"""Real background UIA acceptance against our disposable window; no physical input."""
import asyncio,json,sys,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLineEdit,QPushButton
from PySide6.QtCore import QObject,Signal,QTimer
from hub.accessibility import Accessibility
from hub.session import session_status
from hub.config import ARTIFACTS
class Signals(QObject): done=Signal(object)
app=QApplication([]);window=QWidget();window.setWindowTitle('Local Agent Background Test')
layout=QVBoxLayout(window);field=QLineEdit();layout.addWidget(field);button=QPushButton('Verify background');layout.addWidget(button)
clicks=[];button.clicked.connect(lambda:clicks.append(True));signals=Signals()
def finish(report):
 report.update(value_verified=field.text()=='BACKGROUND_OK',invoke_verified=len(clicks)==1,session_after=session_status())
 report['passed']=report['value_verified'] and report['invoke_verified'] and not report.get('error')
 (ARTIFACTS/'background-accessibility.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report),flush=True);app.exit(0 if report['passed'] else 1)
signals.done.connect(lambda report:QTimer.singleShot(500,lambda:finish(report)))
def begin():
 handle=int(window.winId())
 def worker():
  report={'session_before':session_status(),'physical_input_used':False}
  async def run():
   a=Accessibility()
   try:
    obs=await a.inspect(handle)
    edit=next(e for e in obs['elements'] if e['type']=='Edit')
    result=await a.act({'observation_id':obs['id'],'ref':edit['ref'],'action':'set_value','text':'BACKGROUND_OK'})
    obs=result['after_accessibility'];b=next(e for e in obs['elements'] if e['type']=='Button')
    await a.act({'observation_id':obs['id'],'ref':b['ref'],'action':'invoke'})
   finally:a.executor.shutdown(wait=False)
  try:asyncio.run(run())
  except Exception as e:report['error']=str(e)
  signals.done.emit(report)
 threading.Thread(target=worker,daemon=True).start()
window.show();QTimer.singleShot(500,begin);QTimer.singleShot(25000,lambda:finish({'error':'UI Automation timed out'}))
sys.exit(app.exec())
