"""Render only our own Qt widgets offscreen, without browser or desktop input."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from hub.desktop_app import Window,prepare_fonts
app=QApplication([])
prepare_fonts(app)
window=Window(live=False)
window.show()
app.processEvents()
window.grab().save('E:/AI/artifacts/native-app-preview.png')
window.close()
print('E:/AI/artifacts/native-app-preview.png')
