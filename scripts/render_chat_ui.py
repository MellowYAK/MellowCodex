import os,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-gpu'
os.environ.pop('QTWEBENGINE_REMOTE_DEBUGGING',None)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QTimer,QUrl
from hub.desktop_app import prepare_fonts
app=QApplication([]);prepare_fonts(app);view=QWebEngineView();view.resize(1440,900);view.show()
def mobile():
 view.grab().save('E:/AI/artifacts/chat-desktop-review.png');view.resize(390,844);QTimer.singleShot(1500,finish)
def finish():
 view.grab().save('E:/AI/artifacts/chat-mobile-review.png');app.quit()
view.loadFinished.connect(lambda ok:QTimer.singleShot(2500,mobile) if ok else app.exit(1))
view.setUrl(QUrl('http://127.0.0.1:8876/'));QTimer.singleShot(15000,app.quit);sys.exit(app.exec())
