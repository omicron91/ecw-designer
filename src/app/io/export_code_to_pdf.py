import os

from svglib import svglib

from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.platypus import Paragraph, Table, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


class ReporteClaseBase(canvas.Canvas):
    """
    Clase base para cada slide del reporte
    """

    def __init__(self, filename, pagesize=(1000, 1000)):
        """
        :param pagesize: dimensiones del reporte
        :type pagesize: tuple.
        """
        super(ReporteClaseBase, self).__init__(
            filename=filename,
            pagesize=pagesize
        )

        self.__style = {
            "font": None,
            "font_size": None,
            "color": None,
            "fillcolor": None,
            "linewidth": None
        }

        path_assets = "assets"
        self._path_fonts = os.path.join(path_assets, "fonts")
        self._path_imgs = os.path.join(path_assets, "images/reporte")

        try:
            pdfmetrics.registerFont(TTFont(
                "OpenSans-Regular",
                os.path.join(self._path_fonts, "OpenSans_Condensed-Regular.ttf")
            ))
            self._default_font = "OpenSans-Regular"

            pdfmetrics.registerFont(TTFont(
                "OpenSans-Bold",
                os.path.join(self._path_fonts, "OpenSans_Condensed-Bold.ttf")
            ))
            self._default_font_black = "OpenSans-Bold"
        except TTFError:
            self._default_font = "Times-Roman"
            self._default_font_black = self._default_font
        self._size = pagesize

    def get_size(self):
        """

        :return:
        """
        return self._size

    def get_filename(self):
        """
        Metodo que retorna el nombre del objeto al cual se esta llamando.

        :return: nombre del archivo
        :rtype: str
        """
        return self._filename

    def set_filename(self, filename):
        self._filename = filename

    def set_style(self, **dict_style):
        """
        Método para la configuración de estilos del canvas

        :param font: Fuente.
        :type font: str
        :param font_size: Tamaño texto.
        :type font_size: int
        :param color: Valor hexadecimal para colorear líneas.
        :type color: str
        :param fillcolor: Valor hexadecimal para colorar texto.
        :type fillcolor: str
        :param linewidth: Ancho de la línea a dibujar
        :type linewidth: float

        """
        if "dict_style" in dict_style:
            dict_style = dict_style["dict_style"]

        dict_style_default = {
            "font": None,
            "font_size": None,
            "edge_color": None,
            "fill_color": None,
            "line_width": None
        }

        dict_style_default.update(dict_style)
        dict_style = dict_style_default.copy()

        font = dict_style["font"]
        font_size = dict_style["font_size"]
        edge_color = dict_style["edge_color"]
        fill_color = dict_style["fill_color"]
        line_width = dict_style["line_width"]

        self.__style["font"] = font
        self.__style["font_size"] = font_size
        self.__style["edge_color"] = edge_color
        self.__style["fill_color"] = fill_color
        self.__style["line_width"] = line_width

        if font is not None and font_size is not None:
            self.setFont(font, font_size)

        if font is None and font_size is not None:
            self.setFontSize(font_size)

        if edge_color is not None:
            edge_color = colors.HexColor(edge_color, hasAlpha=True)
            self.setStrokeColor(edge_color)

        if fill_color is not None:
            fill_color = colors.HexColor(fill_color, hasAlpha=True)
            self.setFillColor(fill_color)

        if line_width is not None:
            self.setLineWidth(line_width)

    def get_style(self):
        """
        Metodo que retorna el estilo del objeto al cual se esta llamando.

        :return: estilo
        :rtype: str
        """
        return self.__style

    def stringWidth(self, text, fontName=None, fontSize=None):
        "gets width of a string in the given font and size"
        return pdfmetrics.stringWidth(text, fontName or self._fontname,
                                      (fontSize, self._fontsize)[fontSize is None])

    def insert_svg(self, path, xpos, ypos, w=None, h=None):

        """

        Inserta un SVG dentro del reporte
        :param path: ubicacion del archivo SVG.
        :type path: str
        :param xpos: posicion eje x.
        :type xpos: int
        :param ypos: posicion eje y.
        :type ypos: int

        :return: none.
        :rtype: none
        """
        svg_img = svglib.svg2rlg(path)
        if w is not None:
            scaling_w_factor = w / svg_img.minWidth()
            scaling_h_factor = h / svg_img.height

            svg_img.width = svg_img.minWidth() * scaling_w_factor
            svg_img.height = svg_img.height * scaling_h_factor

            svg_img.scale(scaling_w_factor, scaling_h_factor)

        renderPDF.draw(svg_img, self, xpos, ypos)


class TemplateBased(ReporteClaseBase):
    def __init__(self, template, *args, **kwargs):
        super(TemplateBased, self).__init__(*args, **kwargs)
        self.__template = template

    def draw_container(self, x, y, w, h, style={}):
        shape = style.get("shape", "rect")
        line_width = style.get("line_width", 1)
        fill_color = style.get("fill_color", 0)
        edge_color = style.get("edge_color", "#000000")

        self.set_style(
            fill_color=fill_color,
            edge_color=edge_color,
            line_width=line_width
        )
        stroke = True if line_width > 0 else False
        fill = False if fill_color == 0 else True
        
        if shape == "rect":
            self.rect(
                x=x,
                y=y,
                width=w,
                height=h,
                stroke=stroke,
                fill=fill
            )
        elif shape == "rounded_rect":
            radius = style.get("radius", 3)
            self.roundRect(
                x=x,
                y=y,
                width=w,
                height=h,
                radius=radius,
                stroke=stroke,
                fill=fill
            )
        else:
            radius = min(w, h) // 2
            self.circle(
                x_cen=x+w//2,
                y_cen=y+h//2,
                r=radius,
                stroke=stroke,
                fill=fill
            )

    def draw_slide(self):
        def walk_nodes(node, parent=None):
            node["_parent"] = parent
            yield node
            for child in node.get("children", []):
                yield from walk_nodes(child, node)

        def get_absolute_coords(node):
            x, y = node["component"]["pos"]
            w, h = node["component"]["size"]

            current_node = node
            while current_node.get("_parent") is not None:
                parent = current_node["_parent"]
                px, py = parent["component"]["pos"]
                x += px
                y += py
                current_node = parent

            y = self._size[1] - y - h
            return x, y, w, h
        
        def clip_to_parent(node, x, y, w, h):
            current = node.get("_parent")
            while current is not None and current.get("constraints") is None:
                parent_x, parent_y, parent_w, parent_h = get_absolute_coords(current)
                x1, y1 = x, y
                x2, y2 = x + w, y + h
                px1, py1 = parent_x, parent_y
                px2, py2 = parent_x + parent_w, parent_y + parent_h
                x1 = max(x1, px1)
                y1 = max(y1, py1)
                x2 = min(x2, px2)
                y2 = min(y2, py2)
                w = max(0, x2 - x1)
                h = max(0, y2 - y1)
                x, y = x1, y1
                current = current.get("_parent")
            return x, y, w, h

        for node in walk_nodes(self.__template):
            x, y, w, h = get_absolute_coords(node)
            x, y, w_clip, h_clip = clip_to_parent(node, x, y, w, h)

            bbox_style = node.get("styles", dict())
            node_type = node["type"].lower()
            if node_type == "container":
                self.draw_container(
                    x=x,
                    y=y,
                    w=w_clip,
                    h=h_clip,
                    style=bbox_style
                )
            elif node_type == "text":
                if bbox_style:
                    y_offset = bbox_style.get("y_offset", 0)
                    self.draw_container(
                        x=x,
                        y=y - y_offset,
                        w=w_clip,
                        h=h_clip,
                        style=bbox_style
                    )
                  
                text_properties = node.get("properties", {})
                
                font = text_properties.get("font", "Times-Roman")
                if font == "Times New Roman":
                    font = "Times-Roman"

                font_size = text_properties.get("font_size", 12)
                font_color = text_properties.get("font_color", "#000000")
                ha = text_properties.get("ha", "center")
                va = text_properties.get("va", "center")
                alignment = {
                    "ha": {
                        "left": TA_LEFT,
                        "center": TA_CENTER,
                        "right": TA_RIGHT
                    },
                    "va": {
                        "bottom": "BOTTOM",
                        "center": "MIDDLE",
                        "top": "TOP"
                    }
                }
                styleSheet = ParagraphStyle(
                    name="test",
                    fontName=font,
                    fontSize=font_size,
                    leading=font_size,
                    textColor=font_color,
                    alignment=alignment["ha"][ha]
                )
                text = text_properties.get("text", "").replace("\n", "<br/>")
                paragraph = Paragraph(text, styleSheet)
                font_baseline = font_size * .35

                if va != "bottom":
                    data = [[paragraph]]
                    table = Table(data, colWidths=w, rowHeights=h)
                    table.setStyle([
                        ("VALIGN", (0, 0), (-1, -1), alignment["va"][va]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), font_baseline),
                    ])
                    table.wrapOn(self, w, h)
                else:
                    paragraph.wrap(w, h)
                table.drawOn(canvas=self, x=x, y=y-(h-h_clip))
            elif node_type == "image":
                image_properties = node.get("properties", {})
                path = image_properties.get("path", "")
                if not os.path.exists(path):
                    continue
                alignment = {
                    "ha": {
                        "left": "LEFT",
                        "center": "CENTER",
                        "right": "RIGHT"
                    },
                    "va": {
                        "bottom": "BOTTOM",
                        "center": "MIDDLE",
                        "top": "TOP"
                    }
                }
                ha = image_properties.get("ha", "center")
                va = image_properties.get("va", "center")
                if path.lower().endswith("svg"):
                    img = svglib.svg2rlg(path)
                    original_width = img.minWidth()
                    original_height = img.height
                    w_scale_factor = 1
                    h_scale_factor = 1
                    if image_properties.get("keep_aspect_ratio", False):
                        if image_properties.get("scale", "fit") == "fit":
                            scale_reference = min(w, h)
                            scale_factor = scale_reference / max(original_width, original_height)
                            w_scale_factor = scale_factor
                            h_scale_factor = scale_factor
                        elif image_properties.get("scale") == "width":
                            w_scale_factor = w / original_width
                            h_scale_factor = w / original_width
                        elif image_properties.get("scale") == "height":
                            w_scale_factor = h / original_height
                            h_scale_factor = h / original_height
                    else:
                        w_scale_factor = w / original_width
                        h_scale_factor = h / original_height
                    img.width = original_width * w_scale_factor
                    img.height = original_height * h_scale_factor
                    img.scale(w_scale_factor, h_scale_factor)
                else:
                    kind = "proportional" if image_properties.get("keep_aspect_ratio") else "direct"
                    img = Image(path, kind=kind, width=w, height=h)
                data = [[img]]
                table = Table(data, colWidths=w, rowHeights=h)
                table.setStyle([
                    ("ALIGN", (0, 0), (-1, -1), alignment["ha"][ha]),
                    ("VALIGN", (0, 0), (-1, -1), alignment["va"][va]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ])
                table.wrapOn(self, w, h)
                table.drawOn(canvas=self, x=x, y=y)
        self.save()


def export(template, filename):
    template_based_report = TemplateBased(
        template=template,
        filename=filename,
        pagesize=template["component"]["size"]
    )
    template_based_report.draw_slide()
