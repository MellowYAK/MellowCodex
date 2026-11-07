import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from hub.desktop_app import Window,prepare_fonts
app=QApplication([])
prepare_fonts(app)
window=Window(live=True)
window.show()
def select():
    if window.tasks.count():window.select_item(window.tasks.item(0))
def finish():
    window.grab().save('E:/AI/artifacts/native-live-preview.png')
    report={'task_count':window.tasks.count(),'selected':window.selected,'state':window.task['state'] if window.task else None,'events_characters':len(window.events.toPlainText()),'health':window.health.text(),'error':window.error.text()}
    Path('E:/AI/artifacts/native-live-probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))
    window.close();app.quit()
QTimer.singleShot(3000,select)
QTimer.singleShot(7000,finish)
app.exec()
