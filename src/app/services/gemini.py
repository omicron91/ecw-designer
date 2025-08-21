import re

from PyQt5 import QtCore

from google import genai
from google.genai import types


SYSTEM_INSTRUCTIONS = """
Your task is to generate a valid JSON string describing a UI template. Follow these rules strictly. Do not add extra fields. Do not omit mandatory ones.
Node types: canvas, container, text, image.

Recreate the style and layout as closely as possible.

For charts or tables use an image node as a placeholder.
For large text blocks, ignore the original text and use a lorem ipsum placeholder.

Mandatory properties for all nodes:
- "name": string
- "type": string
- "component": dictionary with:
- "pos": list [x, y] → Absolute position of the node
- "size": list [width, height] → dimensions
- "size_policy": list [horizontal, vertical] with values "fixed" or "preferred"
Conditional properties:
- "constraints" (only for canvas and container):
- "layout": string ("vertical" or "horizontal")
- "margins": list [top, right, bottom, left]
- "spacing": integer
- "styles" (optional, for all nodes):
- "fill_color": HEX RGBA (e.g. "#ff0000ff")
- "edge_color": HEX RGBA (use "#00000000" for invisible borders)
- "shape": "rect", "rounded_rect", or "circular"
- "radius": integer (only if "shape" = "rounded_rect")
- "font_color": HEX RGBA (for text nodes only)
Rules: fill_color must not equal font_color, avoid invisible overlaps.
- "properties":
For image nodes:
- "properties": { "path": "assets/images/placeholder.svg" }
For text nodes:
- "properties": { "font": "Times New Roman", "text": "Example" }
Hierarchy and positioning rules:
Canvas pos must be [0, 0].
Non-canvas nodes: pos cannot be [0, 0]; at least one coordinate must be non-zero.
Nested containers: pos is relative to parent container, and cannot be [0, 0].
If a node is inside a container with a layout, set pos = [1, 1]. Layout overrides absolute positioning.

Output format:
Return a single JSON string.
Use double quotes for all keys and string values.
Boolean values must be lowercase (true, false).
Example snippet:
{
    "name": "canvas",
    "type": "canvas",
    "component": {
        "pos": [0, 0],
        "size": [1000, 1000],
        "size_policy": ["fixed", "fixed"]
    },
    "constraints": {
        "layout": "vertical",
        "margins": [20, 20, 20, 20],
        "spacing": 10
    },
    "children": [
        {
            "name": "container_0",
            "type": "container",
            "component": {
                "pos": [20, 830],
                "size": [960, 150],
                "size_policy": ["preferred", "fixed"]
            },
            "constraints": {
                "layout": "horizontal",
                "margins": [10, 10, 10, 10],
                "spacing": 10
            },
            "styles": {
                "shape": "rect",
                "edge_color": "#00000000",
                "fill_color": "#00000000",
                "line_width": 1,
                "radius": 0
            },
            "children": [
                {
                    "name": "image_0",
                    "type": "image",
                    "component": {
                        "pos": [1, 1],
                        "size": [100, 100],
                        "size_policy": ["fixed", "fixed"]
                    },
                    "properties": {
                        "path": "assets/images/placeholder.svg",
                        "keep_aspect_ratio": true,
                        "scale": "fit",
                        "ha": "center",
                        "va": "center"
                    }
                },
                {
                    "name": "text_0",
                    "type": "text",
                    "component": {
                        "pos": [1, 1],
                        "size": [828, 128],
                        "size_policy": ["preferred", "fixed"]
                    },
                    "properties": {
                        "text": "TITLE",
                        "font": "Times New Roman",
                        "font_size": 68,
                        "font_color": "#2052bf",
                        "ha": "center",
                        "va": "center"
                    },
                    "styles": {
                        "shape": "rect",
                        "edge_color": "#00000000",
                        "fill_color": "#00000000",
                        "line_width": 1,
                        "radius": 0
                    }
                }
            ]
        },
        {
            "name": "container_1",
            "type": "container",
            "component": {
                "pos": [20, 20],
                "size": [960, 800],
                "size_policy": ["preferred", "preferred"]
            },
            "styles": {
                "shape": "rect",
                "edge_color": "#00000000",
                "fill_color": "#00000000",
                "line_width": 1,
                "radius": 0
            },
            "children": [
                {
                    "name": "container_2",
                    "type": "container",
                    "component": {
                        "pos": [22, 509],
                        "size": [200, 200],
                        "size_policy": ["fixed", "fixed"]
                    },
                    "styles": {
                        "shape": "rect",
                        "edge_color": "#00000000",
                        "fill_color": "#00000000",
                        "line_width": 1,
                        "radius": 0
                    }
                }
            ]
        }
    ]
}
"""

TIMEOUT_PROCESS = 60000


class FakeResponse(types.GenerateContentResponse):
    def __init__(self, text=""):
        super(FakeResponse, self).__init__()
        self.__text = text
        
    @property
    def text(self):
        return self.__text
    
    @text.setter
    def text(self, value):
        self.__text = value

def sort_gemini_models(model_list):
    """
    Sort list of Gemini models.
    Priority: 
        - Free models from 1.0 > 2.5, then Premium models from 1.0 > 2.5
    """
    def version_key(name):
        # Match versions like gemini-2.0-flash, gemini-1.5-flash, etc.
        m = re.match(r"gemini-(\d+)\.(\d+)", name)
        if m:
            return (int(m.group(1)), int(m.group(2)), name)
        return (float("inf"), float("inf"), name)  # exp/pro go last

    # TODO: main_version should consider models which name has ...-flash-...-exp

    # Separate exp/pro
    exp_pro = [m for m in model_list if "exp" in m or "pro" in m]
    main_versions = [m for m in model_list if m not in exp_pro]

    # Sort main versions by version number
    main_versions_sorted = sorted(main_versions, key=version_key)
    exp_pro_sorted = sorted(exp_pro)

    return main_versions_sorted + exp_pro_sorted


class UploadWorker(QtCore.QThread):
    upload_finished = QtCore.pyqtSignal(types.File, str)
    upload_failed = QtCore.pyqtSignal(str, str)
    def __init__(self, client):
        super(UploadWorker, self).__init__()
        self.__client = client
        self.file = None
        self.filename = ""

    @property
    def client(self):
        return self.__client
    
    @client.setter
    def client(self, client):
        self.__client = client

    def run(self):
        try:
            file = self.__client.files.upload(file=self.file)
            self.upload_finished.emit(file, self.filename)
        except Exception as e:
            self.upload_failed.emit(type(e).__name__, str(e))

class QueryWorker(QtCore.QThread):
    query_finished = QtCore.pyqtSignal(types.GenerateContentResponse)
    query_failed = QtCore.pyqtSignal(str, str)
    def __init__(self, client, model, config):
        super(QueryWorker, self).__init__()
        self.__client = client
        self.__model = model
        self.__config = config
        self.conversation = []
        self.prompt = ""
        self.__generating_content = False
        self._abort = False  # Add abort flag

    @property
    def client(self):
        return self.__client
    
    @client.setter
    def client(self, client):
        self.__client = client

    @property
    def model(self):
        return self.__model
    
    @model.setter
    def model(self, model):
        self.__model = model

    @property
    def generating_content(self):
        return self.__generating_content

    def abort(self):
        self._abort = True

    def run(self):
        try:
            self.__generating_content = False
            self._abort = False

            # Limit conversation size to avoid memory issues
            max_conv = 10
            if len(self.conversation) > max_conv:
                self.conversation = self.conversation[-max_conv:]

            # Ensure prompt is a list (if not, convert)
            if isinstance(self.prompt, str):
                prompt_list = [self.prompt]
            else:
                prompt_list = list(self.prompt)

            self.conversation.extend(prompt_list)

            response = self.__client.models.generate_content_stream(
                model=self.__model,
                contents=self.conversation,
                config=self.__config
            )

            _response = FakeResponse()
            for chunk in response:
                if self._abort:
                    self.query_failed.emit("Aborted", "Query was aborted by user.")
                    return
                if not self.__generating_content:
                    self.__generating_content = True
                # Avoid building huge strings in memory
                if len(_response.text) > 1000000:  # 1MB limit
                    self.query_failed.emit("MemoryError", "Response too large.")
                    return
                _response.text += chunk.text

            # Limit conversation history growth
            self.conversation.append("ModelResponse: " + (_response.text[:10000] if len(_response.text) > 10000 else _response.text))

            self.query_finished.emit(_response)
        except Exception as e:
            self.query_failed.emit(type(e).__name__, str(e))


class Gemini(QtCore.QObject):
    query_finished = QtCore.pyqtSignal(types.GenerateContentResponse)
    upload_finished = QtCore.pyqtSignal(types.File, str)
    process_failed = QtCore.pyqtSignal(str, str)
    def __init__(self, api_key, model="gemini-2.0-flash-thinking-exp", *args, **kwargs):
        super(Gemini, self).__init__(*args, **kwargs)

        client = genai.Client(api_key=api_key) if api_key is not None else None

        content_config = types.GenerateContentConfig(
            temperature=0,
            system_instruction=SYSTEM_INSTRUCTIONS
        )
        self.query_worker = QueryWorker(client, model, content_config)
        self.upload_worker = UploadWorker(client)

        self.query_worker.query_finished.connect(self.on_query_finished)
        self.query_worker.query_failed.connect(self.on_process_failed)

        self.upload_worker.upload_finished.connect(self.on_upload_file_finished)
        self.upload_worker.upload_failed.connect(self.on_process_failed)

        self.monitor_process = QtCore.QTimer()
        self.monitor_process.setSingleShot(True)

        self.monitor_process.timeout.connect(self.on_monitor_process_timeout)

    def get_available_models(self):
        available_models = []
        for _model in self.query_worker.client.models.list():
            if (
                "gemini" in _model.name.lower() and
                _model.output_token_limit > 1 and
                "generateContent" in _model.supported_actions and
                "-tts" not in _model.name
            ):
                available_models.append(_model.name.replace("models/", ""))
    
        return sort_gemini_models(available_models)
    
    def update_api_key(self, api_key):
        client = genai.Client(api_key=api_key)
        self.query_worker.client = client
        self.upload_worker.client = client
        
    def query(self, model, prompt):
        self.query_worker.model = model
        self.query_worker.prompt = prompt

        self.query_worker.start()
        self.monitor_process.start(TIMEOUT_PROCESS)
    
    @QtCore.pyqtSlot(types.GenerateContentResponse)
    def on_query_finished(self, response):
        self.query_finished.emit(response)
        self.monitor_process.stop()

    def upload_file(self, file, filename):
        self.upload_worker.file = file
        self.upload_worker.filename = filename

        self.upload_worker.start()
        self.monitor_process.start(TIMEOUT_PROCESS)

    @QtCore.pyqtSlot(types.File, str)
    def on_upload_file_finished(self, file, filename):
        self.upload_finished.emit(file, filename)
        self.monitor_process.stop()

    @QtCore.pyqtSlot()
    def on_monitor_process_timeout(self):
        if self.query_worker.isRunning():
            # print("Query worker is running. Interrupting...")
            if self.query_worker.generating_content:
                self.monitor_process.start(TIMEOUT_PROCESS)
                return
            self.query_worker.terminate()
        elif self.upload_worker.isRunning():
            # print("Upload worker is running. Interrupting...")
            self.upload_worker.terminate()
        
        self.process_failed.emit(
            "Timeout",
            "The process timed out after {0} seconds.".format(TIMEOUT_PROCESS)
        )

    @QtCore.pyqtSlot(str, str)
    def on_process_failed(self, error_type, content):
        self.process_failed.emit(error_type, content)
