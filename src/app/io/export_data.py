import re
import json
from copy import deepcopy
from PyQt5 import QtWidgets

from ..widgets.widgets import CustomWidget, Canvas

from app.utils.colors import ColorArray

from .export_code_to_pdf import export


def json_to_python_literals(s):
    # Replace only true/false/null that are not inside quotes
    s = re.sub(r"(?<=: )true(?=[,}\n])", "True", s)
    s = re.sub(r"(?<=: )false(?=[,}\n])", "False", s)
    s = re.sub(r"(?<=: )null(?=[,}\n])", "None", s)
    return s


def get_absolute_pos(node):
    pos = node.pos()
    parent = node.parent()
    while parent and hasattr(parent, "pos") and parent.objectName().lower() != "canvas":
        pos += parent.pos()
        parent = parent.parent()
    return [pos.x(), pos.y()]


def get_component_data(node, canvas_height=None):
    component_type = node.objectName().lower()

    size = node.size()
    size_policy = node.sizePolicy()
    size_policy_h = "fixed" if size_policy.horizontalPolicy() == QtWidgets.QSizePolicy.Fixed else "preferred"
    size_policy_v = "fixed" if size_policy.verticalPolicy() == QtWidgets.QSizePolicy.Fixed else "preferred"

    if component_type == "canvas":
        pos = [0, 0]
    else:
        # abs_pos = get_absolute_pos(node)
        abs_pos = [node.pos().x(), node.pos().y()]
        # Invert Y for ReportLab if canvas_height is provided
        # if canvas_height is not None:
        #     pos = [abs_pos[0], canvas_height - abs_pos[1] - size.height()]
        # else:
        #     pos = abs_pos
        pos = abs_pos
    component_data = {
        "pos": pos,
        "size": [size.width(), size.height()],
        "size_policy": [size_policy_h, size_policy_v]
    }

    return component_data


def get_constraints(node):
    if node.layout() is not None:
        margins = node.layout().contentsMargins()
        constraints = {
            "layout": "vertical" if isinstance(node.layout(), QtWidgets.QVBoxLayout) else "horizontal",
            "margins": [margins.left(), margins.top(), margins.right(), margins.bottom()],
            "spacing": node.layout().spacing()
        }
    else:
        constraints = None
    
    return constraints


def get_text_properties(node):
    text_props = deepcopy(node.text_properties)
    text_props["font_color"] = ColorArray.rgb2hex(text_props["font_color"])
    return text_props


def get_image_properties(node):
    return node.image_properties


def get_styles(node):
    if isinstance(node, Canvas):
        return {}
    
    style = {
        "shape": node.style["shape"],
        "edge_color": ColorArray.rgba2hex(node.style["edge_color"]),
        "fill_color": ColorArray.rgba2hex(node.style["fill_color"]),
        "line_width": node.style["line_width"],
        "radius": node.style["radius"] if node.style["shape"] == "rounded_rect" else 0
    }
    return style


def node_to_dict(node, canvas_height=None):
    """
    Recursively convert a Node tree to a JSON-serializable dictionary.
    """
    node_dict = {
        "name": getattr(node, "objectName", lambda: None)() or getattr(node, "name", None),
        "type": getattr(node, "property", lambda x: None)("component_type") or getattr(node, "type", None),
        "component": get_component_data(node, canvas_height)
    }

    constraints = get_constraints(node)
    if constraints:
        node_dict["constraints"] = constraints
    if hasattr(node, "text_properties"):
        node_dict["properties"] = get_text_properties(node)
    if hasattr(node, "image_properties"):
        node_dict["properties"] = get_image_properties(node)
    if hasattr(node, "style"):
        node_dict["styles"] = get_styles(node)
    # Recursively add children
    children = []
    for child in node.children():
        if isinstance(child, CustomWidget):
            children.append(node_to_dict(child, canvas_height))
    if children:
        node_dict["children"] = children
    return node_dict

def generate_template(filename, canvas, extension):
    canvas_dict = node_to_dict(canvas, canvas_height=canvas.height())

    if extension == ".json":
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(canvas_dict, f, indent=4)
    else:
        export(canvas_dict, filename)
