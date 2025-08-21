from PyQt5 import QtCore, QtGui, QtWidgets, sip
from app.utils.constants import MAP_LABEL_ALIGNMENT


FALSE_STATE_COLOR = (233, 233, 233)
TRUE_STATE_COLOR = (68, 68, 68)


class ECWSwitch(QtWidgets.QWidget):
    """
    Implementación de widget tipo 'toggle switch' con animación
    al cambiar de estado

    Señales:
        state_changed(bool)
    """
    state_changed = QtCore.pyqtSignal(bool)

    def __init__(
            self,
            true_state_bgcolor=TRUE_STATE_COLOR, false_state_bgcolor=FALSE_STATE_COLOR,
            *args, **kwargs
    ):
        super(ECWSwitch, self).__init__(*args, **kwargs)
        
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self.__state = False
        self.__disabled = False

        self.__true_state_color = true_state_bgcolor
        self.__false_state_color = false_state_bgcolor

        self.__margin = 6
        self.__button_position = 0 + self.__margin // 2

        self.__animation = QtCore.QPropertyAnimation(self, b"button_position", self)
        self.__animation.setEasingCurve(QtCore.QEasingCurve.OutBounce)
        self.__animation.setDuration(350)

    # *** OVERRIDED EVENTS ***
    def mouseReleaseEvent(self, event):
        """
        Evento encargado de la detección de la pulsación del clic izquierdo
        del mouse sobre el widget. Si lo detecta, procede a procesar la animación
        y la emisión de la señal debido al cambio de estado
        """
        if event.button() == 1 and not self.__disabled:
            self.state = not self.__state
            self.state_changed.emit(self.__state)

    def resizeEvent(self, _):
        """
        Evento encargado de recalcular la posición horizontal de la pelota en el
        eje 'x' al redimensionar la pantalla
        """
        if self.__state:
            self.__button_position = self.width() - self.height() + self.__margin // 2

    def paintEvent(self, _):
        """
        Evento encargado de la lógica de renderizado del widget.
        El widget consiste de un rectángulo estático con bordes redondeados
        y una pelota móvil
        """
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        color = self.__true_state_color if self.__state else self.__false_state_color

        pen = QtGui.QPen()
        pen.setColor(QtGui.QColor(*color))
        pen.setWidth(3)

        # drawing rounded rect...
        painter.setPen(pen)
        rect = QtCore.QRectF(0, 0, self.width(), self.height())

        painter.setBrush(QtGui.QColor(QtGui.QColor.fromRgb(255, 255, 255)))

        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, rect.height()//2, rect.width()//2)
        painter.setClipPath(path)

        painter.fillPath(path, painter.brush())
        painter.strokePath(path, painter.pen())

        # drawing circle...
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(QtGui.QColor.fromRgb(*color)))

        # radius = [rect.height() - self.__margin]*2
        # painter.drawEllipse(self.__button_position, 0 + self.__margin // 2, *radius)
        radius = int(rect.height() - self.__margin)
        painter.drawEllipse(
            int(self.__button_position),
            int(0 + self.__margin // 2),
            radius,
            radius
        )
        painter.end()

    # *** PUBLIC ***
    @QtCore.pyqtProperty(int)
    def button_position(self):
        """
        Método encargado de asignar la propiedad 'button_position' al widget
        relacionándolo con el atributo 'self.__button_position'
        """
        return self.__button_position
    
    @button_position.setter
    def button_position(self, xpos):
        """
        Método encargado de la asignación de la posición de la pelota
        """
        self.__button_position = xpos
        self.update()

    @property
    def state(self):
        """
        Método que retorna el estado del widget
        """
        return self.__state
    
    @state.setter
    def state(self, state):
        """
        Método que permite la asignación del estado del widget
        """
        self.__state = state
        self.__start_animation()
        self.update()

    @property
    def disabled(self):
        """
        Método que retorna el estado del widget
        """
        return self.__state

    @disabled.setter
    def disabled(self, disabled):
        """
        Método que permite la asignación del estado del widget
        """
        self.__disabled = disabled

    # *** PRIVATE ***
    def __start_animation(self):
        """
        Método encargado de realizar la rutina que anima la posición de la pelota
        del widget
        """
        self.__animation.stop()

        xpos = 0 if not self.__state else (self.width() - self.height())

        self.__animation.setStartValue(self.__button_position)
        self.__animation.setEndValue(xpos + self.__margin // 2)
        self.__animation.start()


class CustomLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        super(CustomLabel, self).__init__(*args, **kwargs)
        self.text_alignment = QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        self.setWordWrap(True)
        self.setFont(QtGui.QFont("Times New Roman"))
        self.setStyleSheet("background-color: transparent;")

    def paintEvent(self, _):
        opt = QtWidgets.QStyleOption()
        opt.initFrom(self)
        painter = QtGui.QPainter(self)

        self.style().drawPrimitive(QtWidgets.QStyle.PE_Widget, opt, painter, self)

        self.style().drawItemText(
            painter, self.rect(),
            # self.text_alignment | QtCore.Qt.TextWrapAnywhere,
            self.text_alignment | QtCore.Qt.TextWordWrap,
            self.palette(),
            True, 
            self.text()
        )
        

class CustomWidget(QtWidgets.QFrame):
    def __init__(self, *args, **kwargs):
        super(CustomWidget, self).__init__(*args, **kwargs)

    def get_all_descendants(self):
        children = self.children()
        all_descendants = []
        for child in children:
            all_descendants.append(child)
            if isinstance(child, CustomWidget):
                all_descendants.extend(child.get_all_descendants())
        return all_descendants

    def delete_all_descendants(self):
        deleted_descendants = []
        for child in self.children():
            if isinstance(child, CustomWidget):
                deleted_descendants.extend(child.delete_all_descendants())
                child.setVisible(False)
                child.deleteLater()
                deleted_descendants.append(child)
        return deleted_descendants

    def set_constraints(self, layout=None, margins=None, spacing=None):
        if layout is not None:
            if self.layout() is not None:
                margins = self.layout().contentsMargins() if margins is None else margins
                if isinstance(margins, QtCore.QMargins):
                    margins = [margins.left(), margins.top(), margins.right(), margins.bottom()]
                spacing = self.layout().spacing() if spacing is None else spacing
            layout_wdg = QtWidgets.QVBoxLayout() if layout.lower() == "vertical" else QtWidgets.QHBoxLayout()
            if layout.lower() == "horizontal":
                layout_wdg.setAlignment(QtCore.Qt.AlignLeft)
            else:
                layout_wdg.setAlignment(QtCore.Qt.AlignTop)
            self.clear_constraints()
        else:
            layout_wdg = self.layout()

        if margins is not None:
            layout_wdg.setContentsMargins(*margins)

        if spacing is not None:
            layout_wdg.setSpacing(spacing)

        for child in self.children():
            if isinstance(child, QtWidgets.QWidget):
                child.setParent(None)
                layout_wdg.addWidget(child)

        if self.layout() is None:
            self.setLayout(layout_wdg)

    def clear_constraints(self):
        layout = self.layout()
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget_to_remove = item.widget()
                if widget_to_remove is not None:
                    layout.removeWidget(widget_to_remove)  # Remove from layout
                    widget_to_remove.setParent(self)
            sip.delete(layout)


class CustomTreeWidget(QtWidgets.QTreeWidget):
    item_deleted = QtCore.pyqtSignal(QtWidgets.QTreeWidgetItem)
    def __init__(self, parent=None):
        super(CustomTreeWidget, self).__init__(parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu_requested)

    def delete_component(self, item):
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        self.item_deleted.emit(item)

    def on_context_menu_requested(self, pos):
        item = self.itemAt(pos)
        if item:
            menu = QtWidgets.QMenu()
            delete_action = menu.addAction("Delete")
            action = menu.exec_(self.mapToGlobal(pos))
            if action == delete_action:
                self.delete_component(item)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == QtCore.Qt.Key.Key_Delete and self.currentItem().text(0) != "Canvas":
            self.delete_component(self.currentItem())


class Canvas(CustomWidget):
    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        self.setObjectName("Canvas")
        self.setProperty("component_type", "Canvas")
        
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QBrush(QtGui.QColor(255, 255, 255)))
        pen = QtGui.QPen(QtGui.QColor(200, 200, 200), 1, QtCore.Qt.SolidLine)
        painter.setPen(pen)
        rect = self.rect()

        lines = []
        for x in range(0, rect.width(), 24):
            lines.append(QtCore.QLine(QtCore.QPoint(x, 0), QtCore.QPoint(x, rect.height())))
        for y in range(0, rect.height(), 24):
            lines.append(QtCore.QLine(QtCore.QPoint(0, y), QtCore.QPoint(rect.width(), y)))

        painter.drawLines(lines)


class DragAndDropContainer(CustomWidget):
    geometry_changed = QtCore.pyqtSignal(tuple, tuple)
    selected = QtCore.pyqtSignal(CustomWidget)
    def __init__(self, component_name, *args, **kwargs):
        super(DragAndDropContainer, self).__init__(*args, **kwargs)
        self.color_selection = {
            "selected": QtCore.Qt.blue,
            "no_selected": QtCore.Qt.lightGray
        }
        self.__selected_state = "selected"

        self._style = {
            "shape": "rect",
            "edge_color": (0, 0, 0, 255),
            "fill_color": (0, 0, 0, 0),
            "line_width": 1,
            "radius": 0
        }
        self.setObjectName(component_name)
        self.setStyleSheet("""
            QFrame#{}{{
                background-color: rgba({}, {}, {}, {});
                border: {}px solid rgba({}, {}, {}, {});
            }}""".format(component_name, *self._style["fill_color"], self._style["line_width"], *self._style["edge_color"]))

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        line_width = self._style["line_width"]

        if self._style["shape"] in ("rounded_rect", "circular"):
            if self._style["shape"] == "rounded_rect":
                r = self._style["radius"]
            elif self._style["shape"] == "circular":
                r = min(self.rect().width(), self.rect().height()) // 2

            painter.setPen(QtGui.QPen(QtGui.QColor.fromRgba(line_width)))
            painter.setBrush(QtGui.QBrush(self.color_selection[self.__selected_state], QtCore.Qt.Dense7Pattern))
            painter.drawRoundedRect(QtCore.QRectF(self.rect()), r, r)
        else:
            painter.setPen(QtGui.QPen(QtGui.QColor.fromRgba(QtGui.qRgba(*self._style["fill_color"])), line_width))
            painter.setBrush(QtGui.QBrush(self.color_selection[self.__selected_state], QtCore.Qt.Dense7Pattern))
            painter.drawRect(self.rect())

    def resizeEvent(self, event):
        size = event.size()
        self.geometry_changed.emit((self.pos().x(), self.pos().y()), (size.width(), size.height()))

    def moveEvent(self, event):
        pos = event.pos()
        self.geometry_changed.emit((pos.x(), pos.y()), (self.rect().width(), self.rect().height()))

    def mouseMoveEvent(self, event):
        mime_data = QtCore.QMimeData()
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime_data)
        drag.setHotSpot(event.pos())
        drag.exec(QtCore.Qt.MoveAction)
    
    def mousePressEvent(self, _):
        self.selected.emit(self)
        self.selected_state = "selected"

    @property
    def selected_state(self):
        return self.__selected_state
    
    @selected_state.setter
    def selected_state(self, state):
        self.__selected_state = state
        self.update()

    @property
    def style(self):
        return self._style
    
    @style.setter
    def style(self, dict_style):
        self._style.update(dict_style)

        edge_color = self._style["edge_color"]
        fill_color = self._style["fill_color"]
        line_width = self._style["line_width"]
        radius = self._style["radius"]

        if self._style["shape"] in ("rounded_rect", "circular"):
            if self._style["shape"] == "circular":
                radius = min(self.rect().width(), self.rect().height()) // 2
            self.setStyleSheet("""
                QFrame#{} {{
                    background-color: rgba({}, {}, {}, {});
                    border: {}px solid rgba({}, {}, {}, {});
                    border-radius: {}px;
                }}
                """.format(self.objectName(), *fill_color, line_width, *edge_color, radius)
            )
        else:
            self.setStyleSheet(
                """
                QFrame#{} {{
                    background-color: rgba({}, {}, {}, {});
                    border: {}px solid rgba({}, {}, {}, {});
                }}
                """.format(self.objectName(), *fill_color, line_width, *edge_color)
            )

        self.update()


class DragAndDropText(DragAndDropContainer):
    def __init__(self, text, *args, **kwargs):
        super(DragAndDropText, self).__init__(*args, **kwargs)
        self.__text_properties = {
            "text":  text,
            "font": "Times New Roman",
            "font_size": 12,
            "font_color": (0, 0, 0),
            "ha": "center",
            "va": "center"
        }

        self.__label = CustomLabel(text)
        self.__label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.__label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter | QtCore.Qt.TextWrapAnywhere)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.layout().addWidget(self.__label)

    def paintEvent(self, event):
        super().paintEvent(event)
        self.__label.setStyleSheet("""
            border: none;
            background-color: transparent;
            font-family: {0};
            font-size: {1}px;
            color: rgb({2}, {3}, {4});
        """.format(
            self.__text_properties["font"],
            self.__text_properties["font_size"],
            *self.__text_properties["font_color"])
        )

    @property
    def text_properties(self):
        return self.__text_properties

    @text_properties.setter
    def text_properties(self, dict_text_properties):
        self.__text_properties.update(dict_text_properties)
        self.__label.setText(self.__text_properties["text"])
        ha = self.__text_properties["ha"].lower()
        va = self.__text_properties["va"].lower()
        self.__label.text_alignment = MAP_LABEL_ALIGNMENT["ha"][ha] | MAP_LABEL_ALIGNMENT["va"][va]

        self.update()


class DragAndDropImage(DragAndDropContainer):
    def __init__(self, path, *args, **kwargs):
        super(DragAndDropImage, self).__init__(*args, **kwargs)
        self.__image_properties = {
            "path":  path,
            "keep_aspect_ratio": True,
            "scale": "fit",
            "ha": "center",
            "va": "center"
        }
        self.pixmap = QtGui.QPixmap(path)
        self.__label = QtWidgets.QLabel()
        self.__label.setStyleSheet("border: none; background-color: transparent;")
        self.__label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.__label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.layout().addWidget(self.__label)

        self.__label.setPixmap(
            self.pixmap.scaled(
                self.__label.size(), 
                self.__image_properties["keep_aspect_ratio"], 
                QtCore.Qt.SmoothTransformation
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        scaled_pixmap = self.pixmap.scaled(
            self.__label.size(), self.__image_properties["keep_aspect_ratio"], QtCore.Qt.SmoothTransformation
        )
        self.__label.setPixmap(scaled_pixmap)

    @property
    def image_properties(self):
        return self.__image_properties

    @image_properties.setter
    def image_properties(self, dict_image_properties):
        self.__image_properties.update(dict_image_properties)
        self.__label.setAlignment(
            MAP_LABEL_ALIGNMENT["ha"][self.__image_properties["ha"].lower()] | 
            MAP_LABEL_ALIGNMENT["va"][self.__image_properties["va"].lower()]
        )
        if self.__image_properties["path"] == "":
            self.__label.clear()
        else:
            self.pixmap = QtGui.QPixmap(self.__image_properties["path"])
            if self.__image_properties["scale"] == "fit":
                self.__label.setPixmap(
                    self.pixmap.scaled(
                        self.__label.size(), 
                        self.__image_properties["keep_aspect_ratio"], 
                        QtCore.Qt.SmoothTransformation
                    )
                )
            elif self.__image_properties["scale"] == "width":
                self.__label.setPixmap(
                    self.pixmap.scaledToWidth(
                        self.__label.size().width(), 
                        QtCore.Qt.SmoothTransformation
                    )
                )
            else:
                self.__label.setPixmap(
                    self.pixmap.scaledToHeight(
                        self.__label.size().height(), 
                        QtCore.Qt.SmoothTransformation
                    )
                )
        self.update()

class DragAndDropButton(DragAndDropContainer):
    def __init__(self, text, *args, **kwargs):
        super(DragAndDropButton, self).__init__(*args, **kwargs)
        self.__text = text
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.btn = QtWidgets.QPushButton(text)
        self.layout().addWidget(self.btn)
        self.setStyleSheet("""
            QFrame#{} {{
                border: none;
            }}
        """.format(self.objectName()))
    def paintEvent(self, _):
        return

    def resizeEvent(self, _):
        return

    def moveEvent(self, _):
        return

    def text(self):
        return self.__text
    