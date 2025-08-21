from .constants import LIGHT_THEME, DARK_THEME


def set_light_theme(app):
    app.setStyleSheet(LIGHT_THEME)

    
def set_dark_theme(app):
    app.setStyleSheet(DARK_THEME)
    