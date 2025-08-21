import logging
logger = logging.getLogger(__name__)

import traceback

import os
import json
import time
import re
import ast

import keyring

from PyQt5 import QtCore, QtGui, QtWidgets
import pywinstyles

from .gui.ecw_designer import Ui_MainWindow
from .gui.dialogs import LoadingDialog, ApiKeyDialog

from .widgets.widgets import (
    CustomWidget,
    Canvas,
    CustomTreeWidget,
    DragAndDropButton,
    DragAndDropContainer,
    DragAndDropText,
    DragAndDropImage,
    ECWSwitch
)

from .io.export_data import generate_template

from .utils.constants import MAX_COMPONENTS_PER_TYPE, MAP_SHAPES, IMAP_SHAPES
from .utils.themes import set_light_theme, set_dark_theme
from .utils.colors import ColorArray

from .services.gemini import Gemini


BASE_DIR = os.getcwd()


class ECWDesigner(Ui_MainWindow, QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        """
        Initialize the ECWDesigner main window.

        :param parent: The parent widget, if any.
        :type parent: QWidget or None
        """
        super().__init__(parent)
        self.setupUi(self)
        
        self.setWindowTitle("ECW Designer")
        self.setAcceptDrops(True)

        for splitter in self.splitter, self.splitter_2:
            splitter.setStyleSheet("QSplitter::handle { background-color: rgb(180, 180, 180); }") 

        self.splitter.setSizes([200, 1000])
        self.splitter_2.setSizes([1000, 200])

        self.frm_canvas.setLayout(QtWidgets.QHBoxLayout())
        self.frm_canvas.layout().setContentsMargins(0, 0, 0, 0)

        layout_vert_canvas = QtWidgets.QVBoxLayout()
        layout_vert_canvas.setContentsMargins(0, 0, 0, 0)
        
        self.frm_canvas.layout().addLayout(layout_vert_canvas)

        self.canvas = Canvas()
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.canvas.setFixedSize(1000, 1000)

        layout_vert_canvas.addWidget(self.canvas)

        layout_vert_inspector = QtWidgets.QVBoxLayout()

        # *** TREE OBJECTS ***
        self.tree_objects = CustomTreeWidget()
        self.tree_objects.setColumnCount(2)
        self.tree_objects.setHeaderLabels(["Name", "Type"])
        
        canvas_item = QtWidgets.QTreeWidgetItem(["Canvas", "Canvas"])
        self.tree_objects.addTopLevelItem(canvas_item)
        
        # *** OBJECT PROPERTIES ***
        self.tree_object_properties = QtWidgets.QTreeWidget()
        self.tree_object_properties.setColumnCount(2)
        self.tree_object_properties.setHeaderLabels(["Property", "Value"])
        self.tree_object_properties.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        layout_vert_inspector.addWidget(self.tree_objects)
        layout_vert_inspector.addWidget(self.tree_object_properties)

        self.frm_inspector.setLayout(layout_vert_inspector)

        self.widgets = dict()
        self.widgets["Canvas"] = [self.canvas]
        
        layout_components = QtWidgets.QVBoxLayout()
        self.grp_components.setLayout(layout_components)

        self.drag_and_drop_buttons = []
        for component_type in ("Container", "Text", "Image"):
            wdg = DragAndDropButton(component_type, component_name=component_type)
            wdg.btn.setFixedHeight(40)
            self.drag_and_drop_buttons.append(wdg)
            layout_components.addWidget(wdg)
            self.widgets[component_type] = [None] * MAX_COMPONENTS_PER_TYPE
                
        self.translucent_wdg = QtWidgets.QFrame()
        self.translucent_wdg.setObjectName("translucent_wdg")
        self.translucent_wdg.setVisible(False)
        self.translucent_wdg.setParent(None)
        self.translucent_wdg_mouse_offset = (0, 0)
        self.drag_elapsed_time = 0

        self.ai_assistant = Gemini(api_key=keyring.get_password("ecw_designer", "ecw"))
        self.ai_assistant.query_finished.connect(self.on_query_finished)
        self.ai_assistant.upload_finished.connect(self.on_upload_file_finished)
        self.ai_assistant.process_failed.connect(self.on_process_failed)
        self.attached_file = None
        
        self.update_available_models()

        self.loading_window = LoadingDialog()

        self.last_wdg_selected = None
        
        ecw_switch = ECWSwitch()
        ecw_switch.setFixedSize(64, 32)
        self.replace_widget(self.switch_theme, ecw_switch)
        self.switch_theme = ecw_switch
        self.switch_theme.state = 0

        self.btn_manage_model.setText("")
        self.btn_remove_attached_file.setText("")        
        self.btn_attach_file.setText("")        
        self.btn_generate_template.setText("")

        # *** SIGNALS ***
        # TREE
        self.tree_objects.item_deleted.connect(self.on_objects_item_deleted)
        self.tree_objects.itemSelectionChanged.connect(self.on_objects_item_selection_changed)

        self.btn_new_canvas.clicked.connect(lambda: self.clear_canvas())
        # LOAD TEMPLATE
        self.btn_load_canvas.clicked.connect(self.on_btn_load_canvas_clicked)
        # HANDLE DATA
        self.btn_manage_model.clicked.connect(self.on_btn_manage_model_clicked)
        self.btn_export.clicked.connect(self.on_btn_export_clicked)
        self.btn_attach_file.clicked.connect(self.on_btn_attach_file_clicked)
        self.btn_remove_attached_file.clicked.connect(self.on_btn_remove_attached_file_clicked)
        self.btn_generate_template.clicked.connect(self.on_btn_generate_template_clicked)

        self.switch_theme.state_changed.connect(self.on_switch_theme_state_changed)
        # *** END SIGNALS ***

        app_instance = QtWidgets.QApplication.instance()
        style = "light" if self.switch_theme.state == 0 else "dark"
        
        if style == "light":
            set_light_theme(app_instance)
        else:
            set_dark_theme(app_instance)
            
        self.set_icon_style(style=style)

    def update_available_models(self):
        self.cmb_ai_model.clear()
        try:
            self.cmb_ai_model.addItems(self.ai_assistant.get_available_models())
        except Exception as e:
            pass
    
    def set_icon_style(self, style="light"):
        suffix = "" if style=="light" else "_dt"

        for drag_and_drop_btn in self.drag_and_drop_buttons:
            icon_name = drag_and_drop_btn.objectName().lower()
            drag_and_drop_btn.btn.setIcon(
                QtGui.QIcon(os.path.join(
                    BASE_DIR,
                    "assets", 
                    "icons",
                    "{0}{1}.png".format(icon_name, suffix)
                ))
            )

        for icon_name, btn in zip(("config", "bin", "upload", "magic"),(
            self.btn_manage_model,
            self.btn_remove_attached_file,
            self.btn_attach_file,
            self.btn_generate_template
        )):
            btn.setIcon(
                QtGui.QIcon(os.path.join(
                        BASE_DIR,
                        "assets", 
                        "icons",
                        "{0}{1}.png".format(icon_name, suffix)
                    )
                )
            )
    
    def on_switch_theme_state_changed(self, state):
        """
        Handle the theme switch toggle event.

        :param state: The new state of the theme switch (0 for light, 1 for dark).
        :type state: int
        """
        app = QtWidgets.QApplication.instance()
        if state:
            pywinstyles.apply_style(self, "dark")
            self.set_icon_style(style="dark")
            set_dark_theme(app)
        else:
            pywinstyles.apply_style(self, "light")
            self.set_icon_style(style="light")
            set_light_theme(app)

    @staticmethod
    def replace_widget(old_widget, new_widget):
        """
        Replace a widget in its parent layout with a new widget.

        :param old_widget: The widget to be replaced.
        :type old_widget: QWidget
        :param new_widget: The new widget to insert.
        :type new_widget: QWidget
        """
        parent = old_widget.parentWidget()
        layout = old_widget.parentWidget().layout() if parent else None
        if layout is not None:
            for i in range(layout.count()):
                if layout.itemAt(i).widget() is old_widget:
                    # Remove old widget
                    layout.removeWidget(old_widget)
                    old_widget.setParent(None)
                    # Insert new widget at the same position
                    layout.insertWidget(i, new_widget)
                    break
    
    @QtCore.pyqtSlot()
    def on_btn_manage_model_clicked(self):
        """
        Handle the event when the 'Manage Model' button is clicked.
        Opens the API key dialog and updates the AI assistant API key.
        """
        api_key_dialog = ApiKeyDialog()

        if api_key_dialog.exec():
            try:
                keyring.set_password("ecw_designer", "ecw", api_key_dialog.get_api_key())
                self.ai_assistant.update_api_key(api_key_dialog.get_api_key())
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                self, 
                type(e).__name__, 
                str(e), 
                QtWidgets.QMessageBox.Ok
            )
            self.update_available_models()
                
    def clear_canvas(self):
        """
        Clear all components from the canvas and reset the widget tracking.
        """
        canvas_item = self.find_item("Canvas")

        if canvas_item:
            self.tree_objects.setCurrentItem(None)
            # Remove all child items from canvas
            while canvas_item.childCount() > 0:
                child = canvas_item.child(0)
                canvas_item.removeChild(child)
            
            # Clear all widgets from canvas
            for child in self.canvas.children():
                if isinstance(child, (DragAndDropContainer, DragAndDropText, DragAndDropImage)):
                    self.delete_widget_and_descendants(child)
            
            # Reset widgets tracking
            for widget_type in self.widgets:
                if widget_type != "Canvas":
                    self.widgets[widget_type] = [None] * MAX_COMPONENTS_PER_TYPE

            self.widgets["Canvas"][0].clear_constraints()
            self.widgets["Canvas"][0].setFixedSize(1000, 1000)

            self.tree_objects.setCurrentItem(canvas_item)
    
    def extract_json_from_string(self, s):
        """
        Extract the first valid JSON object from a string.
        Returns the parsed Python dict.
        """
        start = s.find('{')
        end = s.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = s[start:end+1]
            return json.loads(json_str)
        raise ValueError("No valid JSON object found in the string.")
    
    def load_template_from_code(self, code_text):
        """
        Load a template from Python code text, clear the canvas, and show a success message.

        :param code_text: The Python code as a string.
        :type code_text: str
        """
        if self.loading_window.isVisible():
            self.loading_window.accept()

        try:
            canvas_dict = self.extract_json_from_string(code_text)
            try:
                self.clear_canvas()
                
                self.load_template(canvas_dict)

                QtWidgets.QMessageBox.information(
                    self, "File loaded", "The file has been loaded successfully.",
                    QtWidgets.QMessageBox.Ok
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, 
                    type(e).__name__, 
                    str(e), 
                    QtWidgets.QMessageBox.Ok
                )
        except Exception as e:
            QtWidgets.QMessageBox.information(
                self, 
                "Invalid Code",
                "The code generated does not meet the requirements.",
                QtWidgets.QMessageBox.Ok
            )

    @QtCore.pyqtSlot()
    def on_btn_load_canvas_clicked(self):
        """
        Handle the event when the 'Load Canvas' button is clicked.
        Opens a file dialog to select a template file and loads it.
        """
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            "Open File", 
            "", 
            "Templates (*.json)", 
        )
        if filename == "":
            return
        
        with open(filename, "r", encoding="utf-8") as code_file:
            code_text = code_file.read()
            self.load_template_from_code(code_text=code_text)    

    @QtCore.pyqtSlot()
    def on_btn_export_clicked(self):
        """
        Handle the event when the 'Export' button is clicked.
        Opens a file dialog to save the current template to a file.
        """
        try:
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Export File",
                "",
                "JSON Template (*.json);;PDF (*.pdf)"
            )
            if filename == "":
                return
            extension = os.path.splitext(filename)[1].lower()

            generate_template(filename, self.canvas, extension)
            QtWidgets.QMessageBox.information(
                self, "File exported", "The file has been exported successfully.",
                QtWidgets.QMessageBox.Ok
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 
                type(e).__name__, 
                str(e), 
                QtWidgets.QMessageBox.Ok
            )

    def get_selected_widget(self):
        """
        Get the currently selected widget from the object tree.

        :return: The selected widget, or None if no widget is selected.
        :rtype: QWidget or None
        """
        item = self.tree_objects.currentItem()
        if item is None:
            return None
        
        component_name, component_type = item.text(0), item.text(1)
        for wdg in self.widgets[component_type]:
            if wdg is not None and wdg.objectName() == component_name:
                return wdg
        return None

    @QtCore.pyqtSlot()
    def on_spin_geometry_changed(self):
        """
        Handle changes to geometry spinboxes in the property tree and update widget geometry.
        """
        items = self.tree_object_properties.findItems("Geometry", QtCore.Qt.MatchExactly, 0)
        spin_sender = self.sender()
        if items:
            wdg = self.get_selected_widget()
            if wdg is None:
                return
            for i in range(items[0].childCount()):
                child = items[0].child(i)
                spinbox = self.tree_object_properties.itemWidget(child, 1) 
                if spinbox is spin_sender and child.text(0) == "X":
                    wdg.move(spinbox.value(), wdg.pos().y())
                    break
                elif spinbox is spin_sender and child.text(0) == "Y":
                    wdg.move(wdg.pos().x(), spinbox.value())
                    break
                elif spinbox is spin_sender and child.text(0) == "Width":
                    wdg.setFixedSize(spinbox.value(), wdg.size().height())
                    break
                elif spinbox is spin_sender and child.text(0) == "Height":
                    wdg.setFixedSize(wdg.size().width(), spinbox.value())
                    break
    
    @QtCore.pyqtSlot()
    def on_component_size_policy_changed(self):
        """
        Handle changes to the size policy comboboxes and update the widget's size policy.
        """
        items = self.tree_object_properties.findItems("Size Policy", QtCore.Qt.MatchExactly, 0)
        if items:
            wdg = self.get_selected_widget()
            if wdg is None:
                return
            for i in range(items[0].childCount()):
                child = items[0].child(i)
                _cmb_size_policy = self.tree_object_properties.itemWidget(child, 1)
                size_policy_selection = _cmb_size_policy.currentText()
                if self.sender() is _cmb_size_policy and child.text(0) == "Horizontal":
                    size_policy_h = QtWidgets.QSizePolicy.Fixed if size_policy_selection == "Fixed" else QtWidgets.QSizePolicy.Expanding
                    size_policy_v = wdg.sizePolicy().verticalPolicy()
                    if size_policy_h == QtWidgets.QSizePolicy.Fixed:
                        wdg.setFixedWidth(wdg.width())
                    else:
                        wdg.setMinimumWidth(0)
                        wdg.setMaximumWidth(65535)
                    break
                elif self.sender() is _cmb_size_policy and child.text(0) == "Vertical":
                    size_policy_v = QtWidgets.QSizePolicy.Fixed if size_policy_selection == "Fixed" else QtWidgets.QSizePolicy.Expanding
                    size_policy_h = wdg.sizePolicy().horizontalPolicy()
                    if size_policy_v == QtWidgets.QSizePolicy.Fixed:
                        wdg.setFixedHeight(wdg.height())
                    else:
                        wdg.setMinimumHeight(0)
                        wdg.setMaximumHeight(65535)
                    break

            wdg.setSizePolicy(size_policy_h, size_policy_v)
            wdg.adjustSize()

            str_size_policy_h = "Fixed" if size_policy_h == QtWidgets.QSizePolicy.Fixed else "Preferred"
            str_size_policy_v = "Fixed" if size_policy_v == QtWidgets.QSizePolicy.Fixed else "Preferred"
            items[0].setText(1, "({0}, {1})".format(str_size_policy_h, str_size_policy_v))

    def validate_margins(self, line_edit):
        """
        Validate the margins input in a QLineEdit and revert to the previous value if invalid.

        :param line_edit: The QLineEdit containing the margin string.
        :type line_edit: QLineEdit
        """
        # Regular expression for validating margins
        margin_pattern = r"^\d+,\d+,\d+,\d+$"
        current_text = line_edit.text()
        
        if re.match(margin_pattern, current_text):
            line_edit.setProperty(
                "previous_value",
                current_text
            )
        else:
            # Revert to previous valid text
            line_edit.blockSignals(True)
            line_edit.setText(line_edit.property("previous_value"))
            line_edit.blockSignals(False)

    @QtCore.pyqtSlot()
    def on_constraints_changed(self):
        """
        Handle changes to layout constraints in the property tree and update the widget's constraints.
        """
        wdg_sender = self.sender()
        wdg_selected = self.get_selected_widget()
        if wdg_selected is None:
            return
        items = self.tree_object_properties.findItems("Constraints", QtCore.Qt.MatchExactly, 0)
        if items:
            if isinstance(wdg_sender, QtWidgets.QCheckBox):     # Constraint enable changed
                enabled = wdg_sender.isChecked()
                if enabled:
                    layout_data = dict()
                else:
                    layout_data = None
                for i in range(items[0].childCount()):
                    child = items[0].child(i)
                    item_wdg = self.tree_object_properties.itemWidget(child, 1)
                    item_wdg.setEnabled(enabled)
                    if layout_data is not None:
                        key = child.text(0).lower()
                        if isinstance(item_wdg, QtWidgets.QComboBox):
                            data = item_wdg.currentText().lower()
                        elif isinstance(item_wdg, QtWidgets.QLineEdit):
                            data = list(map(int, item_wdg.text().split(",")))
                        elif isinstance(item_wdg, QtWidgets.QSpinBox):
                            data = item_wdg.value()
                        else:
                            data = None
                        layout_data[key] = data

                if enabled:
                    wdg_selected.set_constraints(**layout_data)
                else:
                    wdg_selected.clear_constraints()
            elif isinstance(wdg_sender, QtWidgets.QComboBox):
                wdg_selected.set_constraints(layout=wdg_sender.currentText().lower())
            elif isinstance(wdg_sender, QtWidgets.QSpinBox):
                wdg_selected.set_constraints(spacing=wdg_sender.value())
            elif isinstance(wdg_sender, QtWidgets.QLineEdit):
                for i in range(items[0].childCount()):
                    child = items[0].child(i)
                    item_wdg = self.tree_object_properties.itemWidget(child, 1)
                    if child.text(0) == "Margins" and item_wdg is wdg_sender:
                        self.validate_margins(wdg_sender)
                        margins = list(map(int, wdg_sender.text().split(",")))
                        wdg_selected.set_constraints(margins=margins)
                        break
    
    @QtCore.pyqtSlot()
    def on_text_properties_changed(self):
        """
        Handle changes to label properties in the property tree and update the label widget.
        """
        wdg_sender = self.sender()
        wdg_selected = self.get_selected_widget()

        if wdg_selected is None:
            return
        
        items = self.tree_object_properties.findItems("Text", QtCore.Qt.MatchExactly, 0)
        if items:
            if isinstance(wdg_sender, QtWidgets.QLineEdit):
                wdg_selected.text_properties = {"text": wdg_sender.text()}
            elif isinstance(wdg_sender, QtWidgets.QPushButton):
                for i in range(items[0].childCount()):
                    child = items[0].child(i)
                    item_wdg = self.tree_object_properties.itemWidget(child, 1)
                    if wdg_sender is item_wdg:
                        if "color" in child.text(0):
                            color_list = list(map(int, wdg_sender.text().replace(" ", "")[1:-1].split(",")))
                            color_picker = QtWidgets.QColorDialog(self)
                            new_color = color_picker.getColor(title="Color picker", initial=QtGui.QColor(*color_list))
                            wdg_selected.text_properties = {"font_color": new_color.getRgb()}
                            wdg_sender.setText("({0}, {1}, {2})".format(*new_color.getRgb()))
                        break
            elif isinstance(wdg_sender, QtWidgets.QSpinBox):
                wdg_selected.text_properties = {"font_size": wdg_sender.value()}
            else:   # QCombobox
                for i in range(items[0].childCount()):
                    child = items[0].child(i)
                    item_wdg = self.tree_object_properties.itemWidget(child, 1)
                    if wdg_sender is item_wdg:
                        alignment = "ha" if "Horizontal" in child.text(0) else "va"
                        wdg_selected.text_properties = {alignment: wdg_sender.currentText().lower()}
                        break
    
    @QtCore.pyqtSlot(tuple, tuple)
    def on_component_geometry_changed(self, pos, size):
        """
        Update the property tree and widget when the geometry of a component changes.

        :param pos: The new position as a tuple (x, y).
        :type pos: tuple
        :param size: The new size as a tuple (width, height).
        :type size: tuple
        """
        wdg = self.get_selected_widget()

        # Se ignora cualquier widget redimensionado que no corresponde al widget seleccionado
        if wdg is None or wdg is not self.sender():
            return
        
        items = self.tree_object_properties.findItems("Geometry", QtCore.Qt.MatchExactly, 0)
        if items:
            item_geometry = items[0]
            item_geometry.setText(1, "({0}, {1}), {2} x {3}".format(*pos, *size))
            size_changed = False
            for i in range(item_geometry.childCount()):
                child = item_geometry.child(i)
                spinbox = self.tree_object_properties.itemWidget(child, 1)
                spinbox.blockSignals(True)
                if child.text(0) == "X":
                    spinbox.setValue(pos[0])
                elif child.text(0) == "Y":
                    spinbox.setValue(pos[1])
                elif child.text(0) == "Width":
                    spinbox.setValue(size[0])
                elif child.text(0) == "Height":
                    spinbox.setValue(size[1])
                spinbox.blockSignals(False)

                if child.text(0) in ("Width", "Height"):
                    if not size_changed:
                        size_changed = True

        if size_changed:
            items = self.tree_object_properties.findItems("Styles", QtCore.Qt.MatchExactly, 0)
            if items:
                for idx_item in range(items[0].childCount()):
                    child = items[0].child(idx_item)
                    if child.text(0) == "Radius":
                        spinbox = self.tree_object_properties.itemWidget(child, 1)

                        spinbox.setRange(0, min(size[0] // 2, size[1] // 2))

    @QtCore.pyqtSlot()
    def on_component_image_property_changed(self):
        """
        Handle changes to image properties in the property tree and update the image widget.
        """
        sender = self.sender()
        wdg = self.get_selected_widget()
        if wdg is None:
            return

        items = self.tree_object_properties.findItems("Image", QtCore.Qt.MatchExactly, 0)
        if items:
            if isinstance(sender, QtWidgets.QPushButton):
                if sender.text() in ("+", "-"):
                    if sender.text() == "+":
                        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Abrir imagen", "", "Images (*.png *.jpg *.jpeg *.bmp *.svg)")
                    else:
                        filename = ""
                    wdg.image_properties = {"path": filename}
                    for i in range(items[0].childCount()):
                        child = items[0].child(i)
                        item_wdg = self.tree_object_properties.itemWidget(child, 1)
                        if type(item_wdg) is QtWidgets.QWidget:
                            line_edit = item_wdg.layout().itemAt(0).widget()
                            line_edit.setText(filename)
                            break

            elif isinstance(sender, QtWidgets.QCheckBox):
                wdg.image_properties = {"keep_aspect_ratio": sender.isChecked()}
            else:   # combobox
                for i in range(items[0].childCount()):
                    child = items[0].child(i)
                    item_wdg = self.tree_object_properties.itemWidget(child, 1)
                    if child.text(0) == "Scale" and sender is item_wdg:
                        wdg.image_properties = {"scale": sender.currentText().lower()}
                        break
                    elif "Horizontal" in child.text(0) and sender is item_wdg:
                        wdg.image_properties = {"ha": sender.currentText().lower()}
                        break
                    elif "Vertical" in child.text(0) and sender is item_wdg:   # Vertical alignment
                        wdg.image_properties = {"va": sender.currentText().lower()}
                        break
                    else:
                        pass
    
    @QtCore.pyqtSlot()
    def on_component_style_changed(self):
        """
        Handle changes to style properties in the property tree and update the widget's style.
        """
        sender = self.sender()
        style_data = sender.property("style")
        wdg = self.get_selected_widget()
        if wdg is None:
            return

        if isinstance(sender, QtWidgets.QPushButton):
            color_list = list(map(int, sender.text().replace(" ", "")[1:-1].split(",")))
            color_picker = QtWidgets.QColorDialog(self)
            new_color = color_picker.getColor(title="Color picker", initial=QtGui.QColor(*color_list), options=QtWidgets.QColorDialog.ShowAlphaChannel)
            r = new_color.red()
            g = new_color.green()
            b = new_color.blue()
            a = new_color.alpha()
            sender.setText("({0}, {1}, {2}, {3})".format(r, g, b, a))
            wdg.style = {style_data[0]: (r, g, b, a)}
            wdg.setProperty("style", (style_data[0], (r, g, b, a)))
        elif isinstance(sender, QtWidgets.QSpinBox):
            wdg.style = {style_data[0]: sender.value()}
        else:   # combobox
            new_shape = MAP_SHAPES[sender.currentText()]
            styles = {style_data[0]: new_shape}
            spin_radius_enabled = False if new_shape in ("rect", "circular") else True
            items = self.tree_object_properties.findItems("Styles", QtCore.Qt.MatchExactly, 0)
            if items:
                for idx_item in range(items[0].childCount()):
                    child = items[0].child(idx_item)
                    if child.text(0) == "Radius":
                        spinbox = self.tree_object_properties.itemWidget(child, 1)
                        spinbox.setValue(0)
                        spinbox.setEnabled(spin_radius_enabled)
                        styles = {style_data[0]: new_shape, "radius": 0}
                        
            wdg.style = styles

    def delete_widget_and_descendants(self, widget, delete_from_tracking=True):
        """
        Delete a widget and all its descendants, cleaning up the tracking system.

        :param widget: The widget to delete.
        :type widget: QWidget
        :param delete_from_tracking: Whether to remove the widget from the tracking dictionary.
        :type delete_from_tracking: bool
        """
        if widget is None:
            return
            
        # First delete all descendants
        if hasattr(widget, 'delete_all_descendants'):
            for descendant in widget.delete_all_descendants():
                if delete_from_tracking:
                    descendant_type = descendant.property("component_type")
                    if descendant_type in self.widgets:
                        try:
                            idx = self.widgets[descendant_type].index(descendant)
                            self.widgets[descendant_type][idx] = None
                        except ValueError:
                            pass  # Widget not in tracking list
                descendant.setVisible(False)
                descendant.deleteLater()
        
        # Then delete the widget itself
        if delete_from_tracking:
            widget_type = widget.property("component_type")
            if widget_type in self.widgets:
                try:
                    idx = self.widgets[widget_type].index(widget)
                    self.widgets[widget_type][idx] = None
                except ValueError:
                    pass  # Widget not in tracking list
        
        widget.setVisible(False)
        widget.deleteLater()

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem)
    def on_objects_item_deleted(self, item):
        """
        Handle the event when an item is deleted from the object tree.

        :param item: The QTreeWidgetItem that was deleted.
        :type item: QTreeWidgetItem
        """
        component_name, component_type = item.text(0), item.text(1)
        for wdg in self.widgets[component_type]:
            if wdg is not None and wdg.objectName() == component_name:
                self.delete_widget_and_descendants(wdg)
                break
    
    def find_item(self, object_name, container=None):
        """
        Recursively search for an item in a QTreeWidget by its text value.

        :param object_name: The text to search for in column 1.
        :type object_name: str
        :param container: The parent QTreeWidgetItem to search within, or None to start at the root level.
        :type container: QTreeWidgetItem or None
        :return: The QTreeWidgetItem if found, or None if not found.
        :rtype: QTreeWidgetItem or None
        """
        if container is None:  # Start at the top-level items if no container is specified
            for i in range(self.tree_objects.topLevelItemCount()):
                item = self.tree_objects.topLevelItem(i)
                # Check if the item matches or search recursively
                if item.text(0) == object_name:
                    return item
                elif item.text(1) in ("Canvas", "Container"):
                    result = self.find_item(object_name, container=item)
                    if result is not None:
                        return result
        else:  # Search within the specified container
            for i in range(container.childCount()):
                item = container.child(i)
                # Check if the item matches or search recursively
                if item.text(0) == object_name:
                    return item
                elif item.text(1) in ("Canvas", "Container"):
                    result = self.find_item(object_name, container=item)
                    if result is not None:
                        return result

        return None

    @QtCore.pyqtSlot(CustomWidget)
    def on_component_selected(self, widget):
        """
        Handle the event when a component widget is selected on the canvas.

        :param widget: The selected widget.
        :type widget: QWidget
        """
        # self.tree_objects.findItems(widget.objectName(), QtCore.Qt.MatchExactly, 0)[0].setSelected(True)
        item_component = self.find_item(widget.objectName())
        if item_component is not None:
            current_item = self.tree_objects.currentItem()
            if current_item is not None:
                wdg = self.get_selected_widget()
                wdg.selected_state = "no_selected"

            self.tree_objects.setCurrentItem(item_component)
            self.tree_objects.setFocus()
    
    @QtCore.pyqtSlot()
    def on_objects_item_selection_changed(self):
        """
        Handle the event when the selection changes in the object tree.
        Updates the property tree to reflect the selected widget's properties.
        """
        self.tree_object_properties.clear()

        wdg = self.get_selected_widget()

        if self.last_wdg_selected is not None:
            self.last_wdg_selected.selected_state = "no_selected"
        
        if wdg is None:
            return
        
        self.last_wdg_selected = wdg
        self.last_wdg_selected.selected_state = "selected"

        pos = wdg.pos() if wdg.property("component_type").lower() != "canvas" else QtCore.QPoint(0, 0)

        # *** GEOMETRY ***
        item_geometry = QtWidgets.QTreeWidgetItem(["Geometry", "({0}, {1}), {2} x {3}".format(pos.x(), pos.y(), wdg.width(), wdg.height())])
        self.tree_object_properties.addTopLevelItem(item_geometry)

        item_pos_x = QtWidgets.QTreeWidgetItem(["X", ""])
        item_geometry.addChild(item_pos_x)
        spinbox_x = QtWidgets.QSpinBox()
        spinbox_x.setRange(0, 99999)
        spinbox_x.setValue(pos.x())

        self.tree_object_properties.setItemWidget(item_pos_x, 1, spinbox_x)

        item_pos_y = QtWidgets.QTreeWidgetItem(["Y", ""])
        item_geometry.addChild(item_pos_y)
        spinbox_y = QtWidgets.QSpinBox()
        spinbox_y.setRange(0, 99999)
        spinbox_y.setValue(pos.y())
        self.tree_object_properties.setItemWidget(item_pos_y, 1, spinbox_y)

        if wdg.property("component_type").lower() == "canvas":
            spinbox_x.setEnabled(False)
            spinbox_y.setEnabled(False)
        
        item_pos_width = QtWidgets.QTreeWidgetItem(["Width", ""])
        item_geometry.addChild(item_pos_width)
        spinbox_width = QtWidgets.QSpinBox()
        spinbox_width.setRange(0, 99999)
        spinbox_width.setValue(wdg.width())
        self.tree_object_properties.setItemWidget(item_pos_width, 1, spinbox_width)

        item_pos_height = QtWidgets.QTreeWidgetItem(["Height", ""])
        item_geometry.addChild(item_pos_height)
        spinbox_height = QtWidgets.QSpinBox()
        spinbox_height.setRange(0, 99999)
        spinbox_height.setValue(wdg.height())
        self.tree_object_properties.setItemWidget(item_pos_height, 1, spinbox_height)
        
        # *** SIZE POLICY ***
        if wdg.property("component_type").lower() != "canvas":
            size_policy_h = ("Fixed" if wdg.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Fixed else "Preferred")
            size_policy_v = ("Fixed" if wdg.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Fixed else "Preferred")

            item_size_policy = QtWidgets.QTreeWidgetItem(["Size Policy", "({}, {})".format(size_policy_h, size_policy_v)])
            self.tree_object_properties.addTopLevelItem(item_size_policy)
            
            item_size_policy_h = QtWidgets.QTreeWidgetItem(["Horizontal", ""])
            cmb_size_policy_h = QtWidgets.QComboBox()
            item_size_policy.addChild(item_size_policy_h)
            cmb_size_policy_h.addItems(["Fixed", "Preferred"])
            cmb_size_policy_h.setCurrentText(size_policy_h)
            self.tree_object_properties.setItemWidget(item_size_policy_h, 1, cmb_size_policy_h)
            
            item_size_policy_v = QtWidgets.QTreeWidgetItem(["Vertical", ""])
            cmb_size_policy_v = QtWidgets.QComboBox()
            item_size_policy.addChild(item_size_policy_v)
            cmb_size_policy_v.addItems(["Fixed", "Preferred"])
            cmb_size_policy_v.setCurrentText(size_policy_v)
            self.tree_object_properties.setItemWidget(item_size_policy_v, 1, cmb_size_policy_v)

        # *** CONSTRAINTS ***
        if wdg.property("component_type").lower() in ("canvas", "container"):
            item_constraints = QtWidgets.QTreeWidgetItem(["Constraints", ""])
            self.tree_object_properties.addTopLevelItem(item_constraints)

            chk_constraints = QtWidgets.QCheckBox()
            if wdg.layout() is not None:
                chk_constraints.setChecked(True)

            self.tree_object_properties.setItemWidget(item_constraints, 1, chk_constraints)

            item_layout = QtWidgets.QTreeWidgetItem(["Layout", ""])
            cmb_layout_type = QtWidgets.QComboBox()
            item_constraints.addChild(item_layout)
            cmb_layout_type.addItems(["Horizontal", "Vertical"])
            cmb_layout_type.setCurrentText("Horizontal" if isinstance(wdg.layout(), QtWidgets.QHBoxLayout) or wdg.layout() is None else "Vertical")
            self.tree_object_properties.setItemWidget(item_layout, 1, cmb_layout_type)

            if wdg.layout() is None:
                margins = "0,0,0,0"
            else:
                qmargins = wdg.layout().contentsMargins()
                margins = ",".join([
                    str(qmargins.left()),
                    str(qmargins.top()),
                    str(qmargins.right()),
                    str(qmargins.bottom())
                ])
            
            item_margins = QtWidgets.QTreeWidgetItem(["Margins", ""])
            line_edit_margins = QtWidgets.QLineEdit()
            item_constraints.addChild(item_margins)
            line_edit_margins.setText(margins)
            line_edit_margins.setProperty("previous_value", margins)
            
            self.tree_object_properties.setItemWidget(item_margins, 1, line_edit_margins)

            spacing = 0 if wdg.layout() is None else wdg.layout().spacing()
            item_spacing = QtWidgets.QTreeWidgetItem(["Spacing", ""])
            spinbox_spacing = QtWidgets.QSpinBox()
            item_constraints.addChild(item_spacing)
            spinbox_spacing.setRange(0, 99)
            spinbox_spacing.setValue(spacing)
            self.tree_object_properties.setItemWidget(item_spacing, 1, spinbox_spacing)

            for wdg_constraint in (cmb_layout_type, line_edit_margins, spinbox_spacing):
                wdg_constraint.setEnabled(chk_constraints.isChecked())

            # *** CONSTRAINT SIGNALS ***
            chk_constraints.toggled.connect(self.on_constraints_changed)
            line_edit_margins.editingFinished.connect(self.on_constraints_changed)
            spinbox_spacing.valueChanged.connect(self.on_constraints_changed)
            cmb_layout_type.currentTextChanged.connect(self.on_constraints_changed)

        elif wdg.property("component_type").lower() == "text":
            label_format = wdg.text_properties

            item_label = QtWidgets.QTreeWidgetItem(["Text", ""])
            self.tree_object_properties.addTopLevelItem(item_label)

            item_text = QtWidgets.QTreeWidgetItem(["Text", ""])
            item_font_family = QtWidgets.QTreeWidgetItem(["Font family", ""])
            item_font_size = QtWidgets.QTreeWidgetItem(["Font size", ""])
            # TODO: CONSIDER THE FONT WEIGHT
            item_font_color = QtWidgets.QTreeWidgetItem(["Font color", ""])
            item_text_horizontal_alignment = QtWidgets.QTreeWidgetItem(["Horizontal alignment", ""])
            item_text_vertical_alignment = QtWidgets.QTreeWidgetItem(["Vertical alignment", ""])
            
            for  item_label_prop in (
                item_text, item_font_family, 
                item_font_size,
                item_font_color,
                item_text_horizontal_alignment,
                item_text_vertical_alignment
            ):
                item_label.addChild(item_label_prop)
            

            line_edit_text = QtWidgets.QLineEdit(label_format["text"])
            
            btn_font_family = QtWidgets.QPushButton(label_format["font"])

            spin_font_size = QtWidgets.QSpinBox()
            spin_font_size.setValue(label_format["font_size"])
            spin_font_size.setRange(1, 9999)

            btn_font_color = QtWidgets.QPushButton("({}, {}, {})".format(*label_format["font_color"]))

            cmb_text_horizontal_alignment = QtWidgets.QComboBox()
            cmb_text_horizontal_alignment.addItems(["Left", "Center", "Right"])

            cmb_text_vertical_alignment = QtWidgets.QComboBox()
            cmb_text_vertical_alignment.addItems(["Top", "Center", "Bottom"])
            
            for idx, cmb in enumerate((cmb_text_horizontal_alignment, cmb_text_vertical_alignment)):
                cmb.setCurrentText(label_format["ha"].capitalize() if idx == 0 else label_format["va"].capitalize())

            self.tree_object_properties.setItemWidget(item_text, 1, line_edit_text)
            self.tree_object_properties.setItemWidget(item_font_family, 1, btn_font_family)
            self.tree_object_properties.setItemWidget(item_font_size, 1, spin_font_size)
            self.tree_object_properties.setItemWidget(item_font_color, 1, btn_font_color)
            self.tree_object_properties.setItemWidget(item_text_horizontal_alignment, 1, cmb_text_horizontal_alignment)
            self.tree_object_properties.setItemWidget(item_text_vertical_alignment, 1, cmb_text_vertical_alignment)

            # *** LABEL SIGNALS ***
            line_edit_text.textChanged.connect(self.on_text_properties_changed)
            btn_font_family.clicked.connect(self.on_text_properties_changed)
            spin_font_size.valueChanged.connect(self.on_text_properties_changed)
            btn_font_color.clicked.connect(self.on_text_properties_changed)
            cmb_text_horizontal_alignment.currentTextChanged.connect(self.on_text_properties_changed)
            cmb_text_vertical_alignment.currentTextChanged.connect(self.on_text_properties_changed)

        elif wdg.property("component_type").lower() == "image":
            image_properties = wdg.image_properties
            item_image = QtWidgets.QTreeWidgetItem(["Image", ""])
            self.tree_object_properties.addTopLevelItem(item_image)

            item_image_path = QtWidgets.QTreeWidgetItem(["Path", ""])
            item_image_scale = QtWidgets.QTreeWidgetItem(["Scale type", ""])
            item_image_keep_aspect = QtWidgets.QTreeWidgetItem(["Keep aspect ratio", ""])
            item_image_horizontal_alignment = QtWidgets.QTreeWidgetItem(["Horizontal alignment", ""])
            item_image_vertical_alignment = QtWidgets.QTreeWidgetItem(["Vertical alignment", ""])

            for item in (
                item_image_path, 
                item_image_keep_aspect,
                item_image_scale, 
                item_image_horizontal_alignment, 
                item_image_vertical_alignment
            ):
                item_image.addChild(item)

            browser_image = QtWidgets.QWidget()

            line_edit_image = QtWidgets.QLineEdit("")
            line_edit_image.setText(image_properties["path"])
            line_edit_image.setReadOnly(True)

            btn_add_image = QtWidgets.QPushButton("+")
            btn_add_image.setFixedSize(22, 22)
            btn_remove_image = QtWidgets.QPushButton("-")
            btn_remove_image.setFixedSize(22, 22)

            h_layout_browser_image = QtWidgets.QHBoxLayout()
            h_layout_browser_image.setContentsMargins(0, 0, 0, 0)
            h_layout_browser_image.addWidget(line_edit_image)
            h_layout_browser_image.addWidget(btn_add_image)
            h_layout_browser_image.addWidget(btn_remove_image)
            browser_image.setLayout(h_layout_browser_image)
            
            chk_image_keep_aspect = QtWidgets.QCheckBox()
            chk_image_keep_aspect.setChecked(image_properties["keep_aspect_ratio"])

            cmb_scale_type = QtWidgets.QComboBox()
            cmb_scale_type.addItems(["Fit", "Width", "Height"])
            cmb_scale_type.setCurrentText(image_properties["scale"].title())

            cmb_image_horizontal_alignment = QtWidgets.QComboBox()
            cmb_image_horizontal_alignment.addItems(["Left", "Center", "Right"])

            cmb_image_vertical_alignment = QtWidgets.QComboBox()
            cmb_image_vertical_alignment.addItems(["Top", "Center", "Bottom"])
            
            for cmb in (cmb_image_horizontal_alignment, cmb_image_vertical_alignment):
                cmb.setCurrentText("Center")

            self.tree_object_properties.setItemWidget(item_image_path, 1, browser_image)
            self.tree_object_properties.setItemWidget(item_image_keep_aspect, 1, chk_image_keep_aspect)
            self.tree_object_properties.setItemWidget(item_image_scale, 1, cmb_scale_type)
            self.tree_object_properties.setItemWidget(item_image_horizontal_alignment, 1, cmb_image_horizontal_alignment)
            self.tree_object_properties.setItemWidget(item_image_vertical_alignment, 1, cmb_image_vertical_alignment)
            
            # *** IMAGE SIGNALS ***
            btn_add_image.clicked.connect(self.on_component_image_property_changed)
            btn_remove_image.clicked.connect(self.on_component_image_property_changed)
            chk_image_keep_aspect.toggled.connect(self.on_component_image_property_changed)
            cmb_scale_type.currentTextChanged.connect(self.on_component_image_property_changed)
            cmb_image_horizontal_alignment.currentTextChanged.connect(self.on_component_image_property_changed)
            cmb_image_vertical_alignment.currentTextChanged.connect(self.on_component_image_property_changed)

        if not wdg.property("component_type").lower() in ("canvas", "image"):
            # *** STYLES ***
            item_styles = QtWidgets.QTreeWidgetItem(["Styles", ""])
            self.tree_object_properties.addTopLevelItem(item_styles)

            item_shape = QtWidgets.QTreeWidgetItem(["Shape", ""])
            item_line_width = QtWidgets.QTreeWidgetItem(["Line Width", ""])
            item_background_color = QtWidgets.QTreeWidgetItem(["Fill Color", ""])
            item_edge_color = QtWidgets.QTreeWidgetItem(["Edge Color", ""])
            item_radius = QtWidgets.QTreeWidgetItem(["Radius", ""])

            for  item_style in (item_shape, item_line_width, item_background_color, item_edge_color, item_radius):
                item_styles.addChild(item_style)

            wdg_styles = wdg.style
            cmb_shape = QtWidgets.QComboBox()
            cmb_shape.setProperty("style", ("shape", "rectange"))
            cmb_shape.addItems(["Rectangle", "Rounded Rectangle", "Circular"])
            cmb_shape.setCurrentText(IMAP_SHAPES[wdg_styles["shape"]])

            spin_line_width = QtWidgets.QSpinBox()
            spin_line_width.setProperty("style", ("line_width", wdg_styles["line_width"]))
            spin_line_width.setValue(wdg_styles["line_width"])
            spin_line_width.setRange(1, 99)

            btn_fill_color = QtWidgets.QPushButton("(0, 0, 0, 0)")
            btn_fill_color.setProperty("style", ("fill_color", wdg_styles["fill_color"]))
            btn_edge_color = QtWidgets.QPushButton("(0, 0, 0, 255)")
            btn_edge_color.setProperty("style", ("edge_color", wdg_styles["edge_color"]))

            spin_radius = QtWidgets.QSpinBox()
            spin_radius.setProperty("style", ("radius", wdg_styles["radius"]))
            spin_radius.setRange(0, 99999)
            spin_radius.setValue(wdg_styles["radius"])
            spin_radius.setEnabled(wdg_styles["shape"] == "rounded_rect")

            cmb_shape.currentIndexChanged.connect(self.on_component_style_changed)
            spin_line_width.valueChanged.connect(self.on_component_style_changed)
        
            for btn_color in (btn_fill_color, btn_edge_color):
                btn_color.clicked.connect(self.on_component_style_changed)
            spin_radius.valueChanged.connect(self.on_component_style_changed)

            self.tree_object_properties.setItemWidget(item_shape, 1, cmb_shape)
            self.tree_object_properties.setItemWidget(item_line_width, 1, spin_line_width)
            self.tree_object_properties.setItemWidget(item_background_color, 1, btn_fill_color)
            self.tree_object_properties.setItemWidget(item_edge_color, 1, btn_edge_color)
            self.tree_object_properties.setItemWidget(item_radius, 1, spin_radius)
        
        # *** SIGNALS ***
        for geometry_spinbox in (spinbox_x, spinbox_y, spinbox_width, spinbox_height):
            if geometry_spinbox is not None:
                geometry_spinbox.valueChanged.connect(self.on_spin_geometry_changed)
        
        if wdg.property("component_type").lower() != "canvas":
            for size_policy_combobox in (cmb_size_policy_h, cmb_size_policy_v):
                size_policy_combobox.currentIndexChanged.connect(self.on_component_size_policy_changed)

    def dragEnterEvent(self, event):
        """
        Handle the drag enter event for drag-and-drop operations.

        :param event: The drag enter event.
        :type event: QDragEnterEvent
        """
        if event.source() is None:
            return
        
        self.translucent_wdg.setParent(self.canvas)
        if not isinstance(event.source(), DragAndDropButton):
            self.translucent_wdg.setStyleSheet(event.source().styleSheet())
            style_sheet = event.source().styleSheet().replace(event.source().objectName(), self.translucent_wdg.objectName())

            pattern_bg = r"background-color: rgba\([^)]+\);"
            pattern_border = r"border: [^;]+;"
            updated_stylesheet = re.sub(pattern_bg, "background-color: rgba({},{},{},{});".format(200, 200, 200, 80), style_sheet)
            updated_stylesheet = re.sub(pattern_border, "border: none;", updated_stylesheet)

            self.translucent_wdg.setStyleSheet(updated_stylesheet)
            self.translucent_wdg.setFixedSize(event.source().size())
            if event.source().parent() is self.canvas:
                wdg_pos = event.source().pos()
            else:
                wdg_pos = self.canvas.mapFrom(self, event.pos()) - event.source().mapFrom(self, event.pos())

            self.translucent_wdg.move(wdg_pos)
            self.translucent_wdg_mouse_offset = self.translucent_wdg.mapFrom(self, event.pos())
        else:
            self.translucent_wdg.setFixedSize(200, 200)
            self.translucent_wdg_mouse_offset = QtCore.QPoint(100, 100)
            self.translucent_wdg.setStyleSheet("background-color: rgba(200, 200, 200, 80);")
        self.drag_elapsed_time = time.time()
        event.accept()

    def dragMoveEvent(self, event):
        """
        Handle the drag move event for drag-and-drop operations.

        :param event: The drag move event.
        :type event: QDragMoveEvent
        """
        # TODO: FIX MAP_TO_GLOBAL ON SECONDARY SCREENS
        top_left = self.canvas.mapToGlobal(self.canvas.rect().topLeft())
        bottom_right = self.canvas.mapToGlobal(self.canvas.rect().bottomRight())
        global_canvas_rect = QtCore.QRect(top_left, bottom_right)
        set_translucent_wdg_visible = False
        if global_canvas_rect.contains(self.mapToGlobal(event.pos())):
            if not self.translucent_wdg.isVisible():
                set_translucent_wdg_visible = True
        else:
            self.translucent_wdg.setVisible(False)

        if self.translucent_wdg.isVisible() or set_translucent_wdg_visible:
            if time.time() - self.drag_elapsed_time > 0.01:
                self.translucent_wdg.move(self.canvas.mapFrom(self, event.pos()) - self.translucent_wdg_mouse_offset)
                if set_translucent_wdg_visible:
                    self.translucent_wdg.setVisible(True)
                self.drag_elapsed_time = time.time()
        event.accept()

    def find_deepest_container(self, wdg, pos):
        """
        Find the deepest container widget at a given position.

        :param wdg: The widget being dragged.
        :type wdg: QWidget
        :param pos: The position to check (global coordinates).
        :type pos: QPoint
        :return: The deepest container widget, or None if not found.
        :rtype: QWidget or None
        """
        candidates = []
        for frame in self.widgets["Container"]:
            if frame is None:
                continue
            local_pos = frame.mapFrom(self, pos)
            if frame is not wdg and frame.visibleRegion().contains(local_pos):
                candidates.append(frame)
        
        # Sort by depth (more parents = deeper)
        candidates.sort(key=lambda f: self.get_widget_depth(f), reverse=True)
        if candidates:
            # print("Candidates found:", [c.objectName() for c in candidates])
            for candidate in candidates:
                if candidate is not wdg and not candidate in wdg.get_all_descendants():
                    return candidate
        else:
            return None

    @staticmethod
    def get_widget_depth(widget):
        """
        Calculate the depth of a widget in the parent hierarchy.

        :param widget: The widget to check.
        :type widget: QWidget
        :return: The depth (number of parent levels).
        :rtype: int
        """
        depth = 0
        while widget.parent() is not None:
            depth += 1
            widget = widget.parent()
        return depth
    
    def load_template(self, node, parent_widget=None, parent_tree_item=None):
        """
        Recursively create and render widgets from a JSON/dict node structure on the canvas.
        Handles canvas node by setting size and layout properties if constraints are present.
        Also sets constraints for containers and connects their constraints_changed signal.
        Adds children to the correct parent in self.tree_objects (Canvas > Container > ... > Child).

        :param node: The root node or current node to render (dict).
        :type node: dict
        :param parent_widget: The parent widget to add children to.
        :type parent_widget: QWidget or None
        :param parent_tree_item: The parent tree item in the object tree.
        :type parent_tree_item: QTreeWidgetItem or None
        """
        time.sleep(0.1)
        QtWidgets.QApplication.processEvents()

        widget_map = {
            "container": DragAndDropContainer,
            "text": DragAndDropText,
            "image": DragAndDropImage
        }
        node_type = node.get("type", "").lower()
        # Handle canvas node
        if node_type == "canvas":
            w, h = node.get("component", {}).get("size", [1000, 1000])
            self.canvas.setFixedSize(w, h)
            constraints = node.get("constraints", None)
            if constraints:
                self.canvas.set_constraints(
                    layout=constraints.get("layout"),
                    margins=constraints.get("margins"),
                    spacing=constraints.get("spacing")
                )
            parent_widget = self.canvas
            # Find or create the canvas tree item
            if hasattr(self, "tree_objects"):
                canvas_item = self.find_item("Canvas")
                if not canvas_item:
                    canvas_item = QtWidgets.QTreeWidgetItem(["Canvas", "Canvas"])
                    self.tree_objects.addTopLevelItem(canvas_item)
                parent_tree_item = canvas_item
        elif node_type in widget_map:
            component_name = node.get("name", "")
            if node_type == "container":
                new_wdg = DragAndDropContainer(component_name=component_name)
                constraints = node.get("constraints", None)
                if constraints:
                    new_wdg.set_constraints(
                        layout=constraints.get("layout"),
                        margins=constraints.get("margins"),
                        spacing=constraints.get("spacing")
                    )
                if hasattr(new_wdg, 'constraints_changed'):
                    new_wdg.constraints_changed.connect(self.on_constraints_changed)
            elif node_type == "text":
                text_props = node.get("properties", {})
                new_wdg = DragAndDropText(
                    component_name=component_name,
                    text=text_props.get("text", "Text")
                )
                if text_props:
                    for k, v in text_props.items():
                        if "color" in k and isinstance(v, str):
                            text_props[k] = ColorArray.hex2rgb(v)
                new_wdg.text_properties = text_props
            elif node_type == "image":
                image_props = node.get("properties", {})
                new_wdg = DragAndDropImage(
                    component_name=component_name,
                    path=image_props.get("path", "")
                )
                if image_props:
                    new_wdg.image_properties = image_props
            else:
                return  # Unknown type

            # Apply any styles defined in the node
            styles = node.get("styles", None)
            if styles:
                for k, v in styles.items():
                    if "color" in k and isinstance(v, str):
                        styles[k] = ColorArray.hex2rgba(v)
                new_wdg.style = styles

            new_wdg.setProperty("component_type", node_type.capitalize())
            # Set size policy based on component configuration
            size_policy = node.get("component", {}).get("size_policy", ["fixed", "fixed"])
            size_policy_h = QtWidgets.QSizePolicy.Fixed if size_policy[0].lower() == "fixed" else QtWidgets.QSizePolicy.Expanding
            size_policy_v = QtWidgets.QSizePolicy.Fixed if size_policy[1].lower() == "fixed" else QtWidgets.QSizePolicy.Expanding
            new_wdg.setSizePolicy(size_policy_h, size_policy_v)
            
            # Set size based on policy
            w, h = node.get("component", {}).get("size", [200, 200])
            if size_policy_h == QtWidgets.QSizePolicy.Fixed:
                new_wdg.setFixedWidth(w)
            else:
                new_wdg.setMinimumWidth(0)
                new_wdg.setMaximumWidth(65535)
            
            if size_policy_v == QtWidgets.QSizePolicy.Fixed:
                new_wdg.setFixedHeight(h)
            else:
                new_wdg.setMinimumHeight(0)
                new_wdg.setMaximumHeight(65535)

            if parent_widget.layout() is not None:
                parent_widget.layout().addWidget(new_wdg)
            else:
                new_wdg.setParent(parent_widget)
                x, y = node.get("component", {}).get("pos", [0, 0])
                w, h = node.get("component", {}).get("size", [0, 0])

                new_wdg.move(x, y)
                
            new_wdg.show()

            if node_type.capitalize() in self.widgets:
                for idx, wdg_placeholder in enumerate(self.widgets[node_type.capitalize()]):
                    if wdg_placeholder is None:
                        self.widgets[node_type.capitalize()][idx] = new_wdg
                        break

            # Tree structure: add to parent_tree_item if present
            new_item = QtWidgets.QTreeWidgetItem([new_wdg.objectName(), node_type.capitalize()])
            if parent_tree_item is not None:
                parent_tree_item.addChild(new_item)
            else:
                canvas_item = self.find_item("Canvas")
                if canvas_item:
                    canvas_item.addChild(new_item)
                else:
                    self.tree_objects.addTopLevelItem(new_item)
            self.tree_objects.setCurrentItem(new_item)
            self.tree_objects.setFocus()
            parent_tree_item = new_item

            new_wdg.geometry_changed.connect(self.on_component_geometry_changed)
            new_wdg.selected.connect(self.on_component_selected)

            parent_widget = new_wdg

        # Recursively process children
        for child in node.get("children", []):
            self.load_template(child, parent_widget=parent_widget, parent_tree_item=parent_tree_item)
            
    @staticmethod
    def is_valid_python(code):
        """
        Check if the given code is valid Python syntax.

        :param code: The code to check.
        :type code: str
        :return: True if the code is valid, False otherwise.
        :rtype: bool
        """
        try:
            code = ast.parse(code)
        except SyntaxError:
            return False
        return True
    
    @QtCore.pyqtSlot()
    def on_btn_attach_file_clicked(self):
        """
        Handle the event when the 'Attach File' button is clicked.
        Opens a file dialog and uploads the selected file using the AI assistant.
        """
        path_file, _ = QtWidgets.QFileDialog().getOpenFileName()
        if path_file != "":
            _, filename = os.path.split(path_file)
            self.ai_assistant.upload_file(file=path_file, filename=filename)
            self.loading_window.exec()
    
    @QtCore.pyqtSlot()
    def on_btn_remove_attached_file_clicked(self):
        """
        Handle the event when the 'Remove Attached File' button is clicked.
        Removes the currently attached file and updates the UI.
        """
        if self.attached_file is not None:
            self.attached_file = None
            self.lbl_attached_file_info.setText("No file attached")

    @QtCore.pyqtSlot()
    def on_btn_generate_template_clicked(self):
        """
        Handle the event when the 'Generate Template' button is clicked.
        Sends a prompt (and optionally an attached file) to the AI assistant to generate a template.
        """
        # Generate new template
        if self.attached_file is not None:
            prompt = [self.plain_text_edit_prompt.toPlainText(), self.attached_file]
        else:
            prompt = self.plain_text_edit_prompt.toPlainText()

        self.ai_assistant.query(model=self.cmb_ai_model.currentText(), prompt=prompt)
        self.loading_window.exec()

    @QtCore.pyqtSlot(object)
    def on_query_finished(self, response):
        """
        Handle the event when the AI assistant finishes a query.
        Loads the generated template code into the canvas.

        :param response: The response object from the AI assistant.
        :type response: object
        """
        logger.debug("Query finished with response:\n{}".format(response.text))
        self.load_template_from_code(code_text=response.text)

    @QtCore.pyqtSlot(object, str)
    def on_upload_file_finished(self, file, filename):
        """
        Handle the event when a file upload is finished.
        Updates the attached file and UI label.

        :param file: The uploaded file path or object.
        :type file: object
        :param filename: The name of the uploaded file.
        :type filename: str
        """
        self.attached_file = file
        self.lbl_attached_file_info.setText(filename)
        self.loading_window.accept()

    @QtCore.pyqtSlot(str, str)
    def on_process_failed(self, error_type, content):
        """
        Handle the event when a process (query or upload) fails.
        Shows an error message and closes the loading dialog.

        :param error_type: The type of error.
        :type error_type: str
        :param content: The error message content.
        :type content: str
        """
        if self.loading_window.isVisible():
            self.loading_window.accept()
            
        QtWidgets.QMessageBox.critical(
            self,
            error_type,
            content
        )

    def dropEvent(self, event):
        """
        Handle the drop event for drag-and-drop operations.

        :param event: The drop event.
        :type event: QDropEvent
        """
        wdg = event.source()
        top_left = self.canvas.mapToGlobal(self.canvas.rect().topLeft())
        bottom_right = self.canvas.mapToGlobal(self.canvas.rect().bottomRight())
        global_canvas_rect = QtCore.QRect(top_left, bottom_right)
        if global_canvas_rect.contains(self.mapToGlobal(event.pos())):
            if wdg.parent() != self.canvas and isinstance(wdg, DragAndDropButton):
                component_sequence = 0
                for idx, wdg_placeholder in enumerate(self.widgets[wdg.objectName()]):
                    if wdg_placeholder is None:
                        component_sequence = idx
                        break
                
                component_name = "{}_{}".format(wdg.objectName(), component_sequence)
                if wdg.objectName() == "Container":
                    new_wdg = DragAndDropContainer(component_name=component_name)
                elif wdg.objectName() == "Text":
                    new_wdg = DragAndDropText(component_name=component_name, text="Text...")
                elif wdg.objectName() == "Image":
                    new_wdg = DragAndDropImage(
                        component_name=component_name,
                        path=os.path.join(os.getcwd(), "assets", "images", "chico_migrana.png")
                    )
                else:
                    return

                new_wdg.setProperty("component_type", wdg.objectName())
                new_wdg.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
                new_wdg.setFixedSize(200, 200)

                if self.canvas.layout() is not None:
                    self.canvas.layout().addWidget(new_wdg)
                else:
                    new_wdg.setParent(self.canvas)
                    new_wdg.move(self.canvas.mapFrom(self, event.pos()) - self.translucent_wdg_mouse_offset)

                new_wdg.show()

                self.widgets[wdg.objectName()][component_sequence] = new_wdg

                new_item = QtWidgets.QTreeWidgetItem([new_wdg.objectName(), wdg.objectName()])
                canvas_item = self.find_item("Canvas")
                canvas_item.addChild(new_item)

                prev_wdg_selected = self.get_selected_widget()
                if prev_wdg_selected is not None:
                    prev_wdg_selected.selected_state = "no_selected"

                self.tree_objects.setCurrentItem(new_item) 
                self.tree_objects.setFocus()

                new_wdg.geometry_changed.connect(self.on_component_geometry_changed)
                new_wdg.selected.connect(self.on_component_selected)

            else:
                deepest_container = self.find_deepest_container(wdg, event.pos())
                if deepest_container and not deepest_container in wdg.get_all_descendants():
                        if deepest_container.layout() is not None:
                            deepest_container.layout().addWidget(wdg)
                        else:
                            wdg.setParent(deepest_container)
                        # Change tree parent
                        container_item = self.find_item(deepest_container.objectName())
                        component_item = self.find_item(wdg.objectName())
                        if component_item.parent():
                            component_item.parent().removeChild(component_item)
                        else:
                            self.tree_objects.takeTopLevelItem(self.tree_objects.indexOfTopLevelItem(component_item))
                        container_item.addChild(component_item)
                        pos = deepest_container.mapFrom(self, event.pos() - self.translucent_wdg_mouse_offset)
                else:
                    # print("No suitable container found, moving to canvas")
                    pos = self.canvas.mapFrom(self, event.pos()) - self.translucent_wdg_mouse_offset
                    moved_item = self.find_item(wdg.objectName())
                    if moved_item:
                        if moved_item.parent() is not None:
                            # print("Removing item from parent:", moved_item.parent().text(0))
                            moved_item.parent().removeChild(moved_item)
                            canvas_item = self.find_item("Canvas")
                            canvas_item.addChild(moved_item)

                    if self.canvas.layout() is not None:
                        wdg.setParent(None)
                        self.canvas.layout().addWidget(wdg)
                    else:
                        wdg.setParent(self.canvas)

                wdg.move(pos)
                wdg.show()

                item = self.find_item(wdg.objectName())
                if item:
                    self.tree_objects.setCurrentItem(item)        

        self.translucent_wdg.setVisible(False)
        self.translucent_wdg.setParent(None)
        event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()
