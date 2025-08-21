import numpy as np


class ColorArray(object):
    """
    color: iterable with elements between 0 - 255
    """
    def __init__(self, color):
        if isinstance(color, str):
            self.color = ColorArray.hex2rgba(color)
        else:
            if not isinstance(color, np.ndarray):
                self.color = np.array(color)
            else:
                self.color = color

    def normalize(self):
        return ColorArray(self.color / 255)
    
    def rgba(self):
        return self.color

    def rgb(self):
        return self.color[:-1]
    
    def hex(self):
        return self.rgb2hex()
    
    @staticmethod
    def hex2rgb(color):
        hex_color = color.lstrip('#')
    
        red = int(hex_color[0:2], 16)
        green = int(hex_color[2:4], 16)
        blue = int(hex_color[4:6], 16)
        
        return np.array((red, green, blue))
    
    @staticmethod
    def hex2rgba(color):
        hex_color = color.lstrip('#')
    
        red = int(hex_color[0:2], 16)
        green = int(hex_color[2:4], 16)
        blue = int(hex_color[4:6], 16)
        
        alpha = 255 if len(color) < 9 else int(hex_color[6:8], 16)
        
        return np.array((red, green, blue, alpha))
    
    @staticmethod
    def rgb2hex(color):
        return "#{:02x}{:02x}{:02x}".format(*color[:3])

    @staticmethod
    def rgba2hex(color):
        return "#{:02x}{:02x}{:02x}{:02x}".format(*color)
    
    def alpha(self):
        return self.color[-1]

    def set_alpha(self, alpha):
        if self.color.shape[0] == 3:
            self.color = np.append(self.color, np.array([int(alpha)]))
        else:
            self.color[-1] = int(alpha)
