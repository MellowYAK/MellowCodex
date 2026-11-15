"""Safety and render evidence for Qt's per-tab readable fallback."""
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QImage,QColor
from hub.browser_view import visually_blank,should_enable_compatibility


def image(color):
    im=QImage(120,80,QImage.Format_RGB32)
    im.fill(QColor(color))
    return im


def test_full_white_surface_is_blank():
    assert visually_blank(image("#ffffff")) is True
    assert visually_blank(image("#202020")) is False
    assert visually_blank(image("#ededed")) is False
    assert visually_blank(QImage()) is False


def test_actual_content_pixels_prevent_js_fallback():
    im=image("#ffffff")
    for y in range(0,80):
        for x in range(0,120,3):
            im.setPixelColor(x,y,QColor("#202020"))
    assert visually_blank(im) is False


def test_blank_requires_visible_selected_http_tab_and_two_observations():
    u=QUrl("https://www.ynet.co.il/")
    assert not should_enable_compatibility(u,True,False,1)
    assert not should_enable_compatibility(u,False,False,2)
    assert not should_enable_compatibility(u,True,True,2)
    assert should_enable_compatibility(u,True,False,2)
    assert not should_enable_compatibility(QUrl("about:blank"),True,False,2)
    assert not should_enable_compatibility(QUrl("file:///C:/private.html"),True,False,2)
