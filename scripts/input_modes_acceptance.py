"""Exercise real accessibility and physical input only in an owned test window."""
import asyncio,ctypes,json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path('E:/AI/artifacts/input-modes-acceptance')

def fixture():
    from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLineEdit,QPushButton,QLabel
    from PySide6.QtCore import QTimer
    app=QApplication([]);window=QWidget();window.setWindowTitle('Local Agent input verification')
    layout=QVBoxLayout(window);layout.addWidget(QLabel('Local Agent: quiet controls and real mouse/keyboard test'))
    edit=QLineEdit();edit.setAccessibleName('Evidence input');layout.addWidget(edit)
    button=QPushButton('Commit evidence');layout.addWidget(button)
    label=QLabel('No input committed');layout.addWidget(label)
    def save():
        result={'text':edit.text(),'hwnd':int(window.winId())}
        for name,widget in [('edit',edit),('button',button)]:
            point=widget.mapToGlobal(widget.rect().center());result[name]=[point.x(),point.y()]
        (ROOT/'fixture.json').write_text(json.dumps(result))
    def commit():
        (ROOT/'committed.txt').write_text(edit.text(),encoding='utf-8');label.setText(edit.text());save()
    button.clicked.connect(commit);edit.textChanged.connect(save)
    window.resize(600,220);window.move(350,250);window.show();window.raise_();window.activateWindow()
    timer=QTimer();timer.timeout.connect(save);timer.start(100)
    stop=QTimer();stop.timeout.connect(lambda:app.quit() if (ROOT/'stop').exists() else None);stop.start(200)
    QTimer.singleShot(60000,app.quit);app.exec()

async def verify():
    from hub.desktop import Desktop
    from hub.accessibility import Accessibility
    from ctypes import wintypes
    desktop=Desktop();access=Accessibility()
    def cursor():
        point=wintypes.POINT();desktop.user.GetCursorPos(ctypes.byref(point));return [point.x,point.y]
    async def committed(expected):
        for _ in range(30):
            if (ROOT/'committed.txt').exists() and (ROOT/'committed.txt').read_text(encoding='utf-8')==expected:return
            await asyncio.sleep(.1)
        raise AssertionError('Test window did not receive '+expected)
    state=json.loads((ROOT/'fixture.json').read_text());hwnd=state['hwnd']
    before=cursor();observation=await access.inspect(hwnd)
    field=next(e for e in observation['elements'] if e['type']=='Edit')
    await access.act({'observation_id':observation['id'],'ref':field['ref'],'action':'set_value','text':'quiet-input-ok'})
    observation=await access.inspect(hwnd);button=next(e for e in observation['elements'] if e['type']=='Button' and e['name']=='Commit evidence')
    await access.act({'observation_id':observation['id'],'ref':button['ref'],'action':'invoke'})
    await committed('quiet-input-ok');after=cursor();assert before==after,'Quiet input moved the cursor'
    desktop.focus(hwnd)
    actions=[]
    def act(action,**args):
        observation=desktop.capture(ROOT);desktop.act({'observation_id':observation['id'],'action':action,**args});actions.append(action)
    act('move',x=state['edit'][0],y=state['edit'][1])
    act('click',x=state['edit'][0],y=state['edit'][1])
    act('key',key='CTRL+A');act('type',text='physical-input-ok')
    act('click',x=state['button'][0],y=state['button'][1]);await committed('physical-input-ok')
    evidence=desktop.capture(ROOT)
    result={'quiet':{'verified':True,'cursor_before':before,'cursor_after':after,'received':'quiet-input-ok'},'physical':{'verified':True,'actions':actions,'received':'physical-input-ok'},'screenshot':evidence['path']}
    (ROOT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    access.executor.shutdown(wait=False)

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    for name in ('stop','fixture.json','committed.txt'):(ROOT/name).unlink(missing_ok=True)
    env=dict(os.environ);env.pop('QT_QPA_PLATFORM',None)
    child=subprocess.Popen([sys.executable,__file__,'fixture'],env=env,creationflags=0x08000000)
    try:
        for _ in range(100):
            if (ROOT/'fixture.json').exists():break
            time.sleep(.1)
        asyncio.run(verify())
    finally:
        (ROOT/'stop').write_text('stop');child.wait(timeout=10)

if __name__=='__main__':
    if sys.argv[-1]=='fixture':fixture()
    else:main()
