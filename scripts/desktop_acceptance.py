"""Exercise the product input driver only against this disposable native test window."""
import json,sys,threading,time
import httpx
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt,QTimer,Signal,QObject
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLineEdit,QPushButton,QLabel,QScrollArea
from hub.desktop import Desktop
from hub.desktop_app import prepare_fonts

OUT=Path('E:/AI/artifacts/desktop-acceptance');OUT.mkdir(parents=True,exist_ok=True)
AGENT='--agent' in sys.argv
class Canvas(QLabel):
    def __init__(self):
        super().__init__('Drag test area');self.setFixedHeight(120);self.setStyleSheet('background:#cad7fa;color:#152343;padding:20px');self.distance=0;self.start=None
    def mousePressEvent(self,event):self.start=event.position()
    def mouseReleaseEvent(self,event):
        if self.start is not None:self.distance=(event.position()-self.start).manhattanLength()

class Signals(QObject):done=Signal(object)
app=QApplication([]);prepare_fonts(app)
window=QWidget();window.setWindowTitle('Local Agent Desktop Acceptance');window.resize(720,650);window.move(120,100)
layout=QVBoxLayout(window);layout.addWidget(QLabel('Native input verification — disposable test window'))
field=QLineEdit();field.setPlaceholderText('Unicode typing test');layout.addWidget(field)
button=QPushButton('Click test');layout.addWidget(button)
counter={'clicks':0}
button.clicked.connect(lambda:counter.update(clicks=counter['clicks']+1))
canvas=Canvas();layout.addWidget(canvas)
scroll=QScrollArea();content=QLabel('\n'.join(f'Scroll verification line {i}' for i in range(80)));content.setMinimumHeight(1800);scroll.setWidget(content);layout.addWidget(scroll)
signals=Signals();driver=Desktop()

def finish(result):
    result.update(click_verified=counter['clicks']==1,unicode_verified=field.text()=='שלום local 123',drag_verified=canvas.distance>100,scroll_verified=scroll.verticalScrollBar().value()>0)
    if AGENT:
        result['typed_expected']=field.text()=='LOCAL_AGENT_GUI_OK'
        result['passed']=result['typed_expected'] and result['click_verified'] and not result.get('error')
    else:result['passed']=all(result.get(k,False) for k in ('click_verified','unicode_verified','drag_verified','scroll_verified','stop_verified')) and not result.get('error')
    window.grab().save(str(OUT/'fixture-final.png'))
    (OUT/('agent-result.json' if AGENT else 'result.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True));window.close();app.exit(0 if result['passed'] else 1)
signals.done.connect(finish)

def begin():
    def point(widget,dx=0):
        p=widget.mapToGlobal(widget.rect().center());return (p.x()+dx,p.y())
    positions={'field':point(field),'button':point(button),'drag_start':point(canvas,-140),'drag_end':point(canvas,140),'scroll':point(scroll.viewport())}
    handle=int(window.winId())
    def worker():
        result={}
        try:
            if AGENT:
                from hub.config import STATE
                with httpx.Client(base_url='http://127.0.0.1:8876',headers={'X-Hub-Key':(STATE/'hub.key').read_text().strip()},timeout=20,trust_env=False) as client:
                    payload={'goal':'Use ONLY list_windows, focus_window, observe_screen and desktop_action. Find and focus the window titled Local Agent Desktop Acceptance. In that window, type EXACTLY LOCAL_AGENT_GUI_OK into the first text input, then click the button labeled Click test exactly once. Use screenshots to find coordinates. Do not touch any other windows and do not run shell or write files. Report what you observed.','workspace':'E:/AI/repos/sandbox','mode':'desktop','idempotency_key':'gui-acceptance-'+str(time.time_ns())}
                    response=client.post('/api/tasks',json=payload);response.raise_for_status();task=response.json();started=time.monotonic()
                    while time.monotonic()-started<180:
                        task=client.get('/api/tasks/'+task['id']).json()
                        if task['state'] in ('done','waiting_review','waiting_user','failed','cancelled'):break
                        time.sleep(2)
                    result.update(task_id=task['id'],state=task['state'],elapsed_seconds=round(time.monotonic()-started,2))
                    if task['state'] in ('running','queued'):
                        client.post('/api/tasks/'+task['id']+'/control',json={'command':'cancel','expected_revision':task['revision']})
                        result['error']='Model task timed out'
                signals.done.emit(result);return
            driver.focus(handle);time.sleep(.4)
            def action(kind,**args):
                state=driver.capture(OUT);driver.act({'observation_id':state['id'],'action':kind,**args});time.sleep(.15)
            action('click',x=positions['button'][0],y=positions['button'][1])
            action('click',x=positions['field'][0],y=positions['field'][1])
            action('type',text='replace me')
            action('key',key='CTRL+A')
            action('type',text='שלום local 123')
            action('drag',x=positions['drag_start'][0],y=positions['drag_start'][1],end_x=positions['drag_end'][0],end_y=positions['drag_end'][1])
            action('move',x=positions['scroll'][0],y=positions['scroll'][1])
            action('scroll',amount=-5)
            state=driver.capture(OUT);driver.stopped=True
            try:driver.act({'observation_id':state['id'],'action':'click','x':positions['button'][0],'y':positions['button'][1]})
            except RuntimeError:result['stop_verified']=True
            result['screenshot']=state['path']
        except Exception as exc:result['error']=str(exc)
        signals.done.emit(result)
    threading.Thread(target=worker,daemon=True).start()

window.show();window.activateWindow();window.raise_();QTimer.singleShot(1000,begin)
sys.exit(app.exec())
