"""Native Qt client: independent of Codex, Chromium, and any external browser."""
import html
import json
import sys
import uuid
from pathlib import Path

import httpx
from PySide6.QtCore import QObject,QRunnable,QThreadPool,QTimer,Qt,Signal,QSize
from PySide6.QtGui import QFont,QFontDatabase,QPixmap,QTextCursor
from PySide6.QtNetwork import QLocalServer,QLocalSocket
from PySide6.QtWidgets import QSystemTrayIcon,QMenu,QStyle
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QListWidget,QListWidgetItem,QTextEdit,QLineEdit,QComboBox,QFrame,QFileDialog,QStackedWidget,QGridLayout,QTabWidget
from .config import ROOT,STATE,PORT,ARTIFACTS

LABELS={'queued':'בתור','running':'בעבודה','verifying':'בודק תוצאה','done':'הושלם','failed':'נכשל','paused':'מושהה','cancelled':'בוטל','waiting_user':'נדרשת התערבות','waiting_review':'ממתין לסקירה','waiting_desktop':'ממתין לפתיחת שולחן העבודה'}
STYLE='''
QMainWindow,QWidget#root {background:#111217;color:#e5e7f0}
QWidget {font-family:'Segoe UI';font-size:13px;color:#e5e7f0}
QFrame#sidebar {background:#191a22;border-left:1px solid #2c2e3b}
QLabel#brand {font-size:19px;font-weight:700;color:#c1c2ff}
QLabel#eyebrow {font-size:10px;color:#858ba2}
QLabel#title {font-size:27px;font-weight:600}
QLabel#muted {color:#9399ae;font-size:12px}
QLabel#heroTitle {font-size:25px;font-weight:500}
QLabel#symbol {font-size:44px;color:#c4c6ff}
QPushButton {background:#252733;border:1px solid #3a3d4c;border-radius:8px;padding:10px 15px}
QPushButton:hover {background:#343747}
QPushButton:disabled {color:#73778a}
QPushButton#primary {background:#bfc0ff;color:#202139;border:none;font-weight:600}
QPushButton#danger {background:#301f2a;color:#f3b2bd;border-color:#65404b}
QPushButton#card {text-align:right;background:#1d1f29;padding:18px;border-color:#343746;font-size:14px}
QListWidget {background:transparent;border:none;outline:none}
QListWidget::item {padding:12px 8px;border-radius:7px;margin:3px 0}
QListWidget::item:selected {background:#303247}
QFrame#health,QFrame#composer {background:#1a1c25;border:1px solid #36394b;border-radius:12px}
QLineEdit,QComboBox {background:#13151d;border:1px solid #363a4d;border-radius:6px;padding:9px;color:#d8dbea}
QTextEdit {background:#141620;border:1px solid #303449;border-radius:8px;padding:9px;color:#e0e4f1}
QTextEdit#goal {background:transparent;border:none;font-size:14px}
QLabel#error {color:#ffc2cb;background:#3b2530;padding:8px;border-radius:6px}
QScrollBar:vertical {width:8px;background:#161822} QScrollBar::handle:vertical {background:#42475c;min-height:25px;border-radius:4px}
'''

class Signals(QObject):
    result=Signal(object)
    error=Signal(str)

class Request(QRunnable):
    def __init__(self,method,path,body=None):
        super().__init__()
        self.method,self.path,self.body=method,path,body
        self.signals=Signals()
    def run(self):
        try:
            key=(STATE/'hub.key').read_text(encoding='utf-8').strip()
            with httpx.Client(base_url=f'http://127.0.0.1:{PORT}',headers={'X-Hub-Key':key},timeout=20,trust_env=False) as client:
                response=client.request(self.method,'/api'+self.path,json=self.body)
                result=response.json()
                if not response.is_success:
                    raise RuntimeError(result.get('detail',str(response.status_code)))
            self.signals.result.emit(result)
        except Exception as exc:
            self.signals.error.emit(str(exc))

def label(text,name=None):
    widget=QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(True)
    return widget

def button(text,callback,name=None):
    widget=QPushButton(text)
    if name:
        widget.setObjectName(name)
    widget.clicked.connect(callback)
    return widget

class Window(QMainWindow):
    def __init__(self,live=True):
        super().__init__()
        self.live=live
        self.selected=None
        self.task=None
        self.cursor=0
        self.poll_pending=False
        self.event_pending=False
        self.pool=QThreadPool(self)
        self.pool.setMaxThreadCount(4)
        self.pending_requests=set()
        self.setWindowTitle('Local Agent — סביבת העבודה המקומית')
        self.resize(1220,860)
        self.setMinimumSize(950,720)
        self.setLayoutDirection(Qt.RightToLeft)
        root=QWidget();root.setObjectName('root');self.setCentralWidget(root)
        layout=QHBoxLayout(root);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(238)
        side=QVBoxLayout(sidebar);side.setContentsMargins(20,30,20,24);side.setSpacing(16)
        brand=label('LOCAL AGENT','brand');brand.setLayoutDirection(Qt.LeftToRight);side.addWidget(brand)
        side.addWidget(label('סביבת עבודה מקומית','muted'))
        side.addSpacing(15)
        side.addWidget(button('+ משימה חדשה',self.new_task,'primary'))
        side.addSpacing(14)
        side.addWidget(label('המשימות שלך','muted'))
        self.tasks=QListWidget();self.tasks.setWordWrap(True);self.tasks.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.tasks.itemClicked.connect(self.select_item);side.addWidget(self.tasks,1)
        side.addWidget(label('●  פועל על המחשב שלך','muted'))
        side.addWidget(label('E:\\AI  ·  LOCAL FIRST','eyebrow'))
        layout.addWidget(sidebar)
        main=QWidget();main_layout=QVBoxLayout(main);main_layout.setContentsMargins(34,28,34,20);main_layout.setSpacing(18)
        top=QHBoxLayout();titles=QVBoxLayout();titles.setSpacing(7)
        titles.addWidget(label('WORKSPACE / LOCAL','eyebrow'));titles.addWidget(label('מה נבנה היום?','title'))
        top.addLayout(titles,1);top.addWidget(button('■  עצור הכול',self.stop_all,'danger'),0,Qt.AlignTop);main_layout.addLayout(top)
        health=QFrame();health.setObjectName('health');hl=QHBoxLayout(health);hl.setContentsMargins(18,14,18,14)
        self.health=label('בודק את המנוע המקומי…');hl.addWidget(self.health,1)
        hl.addWidget(label('Windows · עכבר · מקלדת\nCtrl+Alt+F12 לעצירה','muted'))
        hl.addWidget(button('שחרר GPU',lambda:self.request('POST','/model/unload',{},lambda _:self.show_error('המודל שוחרר מזיכרון ה־GPU'))))
        main_layout.addWidget(health)
        self.stack=QStackedWidget()
        welcome=QWidget();wl=QVBoxLayout(welcome);wl.setSpacing(15)
        wl.addStretch(1)
        symbol=label('⌘','symbol');symbol.setAlignment(Qt.AlignCenter);wl.addWidget(symbol)
        heading=label('מרעיון לפעולה, על המחשב שלך.','heroTitle');heading.setAlignment(Qt.AlignCenter);wl.addWidget(heading)
        intro=label('תאר את התוצאה הרצויה. הסוכן יעבוד בתיקיית הפרויקט,\nישמור את ההתקדמות ויציג את הפעולות והראיות.','muted');intro.setAlignment(Qt.AlignCenter);wl.addWidget(intro)
        cards=QHBoxLayout()
        presets=[('להכיר פרויקט\n\nקבצים, מבנה והסבר','בדוק את הקבצים בתיקייה והסבר את מבנה הפרויקט בלי לשנות קבצים.',0),('לבנות ולבדוק קוד\n\nעריכה, פקודות ותוצאות','צור hello.py שמדפיס Hello local agent. הרץ אותו ובדוק את התוצאה.',1),('לראות את המחשב\n\nצילום מסך וניתוח חזותי','הצג את רשימת החלונות וצלם את המסך. תאר מה רואים, בלי ללחוץ או להקליד.',2)]
        for title,prompt,mode in presets:
            cards.addWidget(button(title,lambda checked=False,p=prompt,m=mode:self.preset(p,m),'card'))
        wl.addSpacing(6);wl.addLayout(cards);wl.addStretch(1)
        self.stack.addWidget(welcome)
        detail=QWidget();dl=QVBoxLayout(detail);dl.setContentsMargins(0,0,0,0)
        self.task_title=label('','heroTitle');dl.addWidget(self.task_title)
        self.task_status=label('','muted');dl.addWidget(self.task_status)
        controls=QHBoxLayout()
        self.control_buttons={}
        for command,title in [('pause','השהה'),('resume','המשך'),('cancel','בטל')]:
            b=button(title,lambda checked=False,c=command:self.control(c));self.control_buttons[command]=b;controls.addWidget(b)
        controls.addStretch();dl.addLayout(controls)
        self.events=QTextEdit();self.events.setReadOnly(True);dl.addWidget(self.events,1)
        self.review=QFrame();rl=QHBoxLayout(self.review);rl.setContentsMargins(0,7,0,0)
        self.review_note=QLineEdit();self.review_note.setPlaceholderText('הערה או בקשת תיקון');rl.addWidget(self.review_note,1)
        rl.addWidget(button('אשר תוצאה',lambda:self.review_task('approve'),'primary'));rl.addWidget(button('בקש תיקון',lambda:self.review_task('request_changes')))
        self.review.hide();dl.addWidget(self.review)
        self.stack.addWidget(detail);main_layout.addWidget(self.stack,1)
        composer=QFrame();composer.setObjectName('composer');cl=QVBoxLayout(composer);cl.setContentsMargins(17,12,17,14)
        cl.addWidget(label('המשימה הבאה','muted'))
        self.goal=QTextEdit();self.goal.setObjectName('goal');self.goal.setPlaceholderText('למשל: תקן את הפרויקט, הרץ בדיקות והראה לי מה השתנה…');self.goal.setFixedHeight(83);cl.addWidget(self.goal)
        options=QHBoxLayout();self.mode=QComboBox()
        self.mode.addItem('קריאה בלבד','inspect');self.mode.addItem('קוד ופקודות','code');self.mode.addItem('סוכן מלא: מחשב ודפדפן','desktop');self.mode.addItem('דפדפן','browser');self.mode.setCurrentIndex(2)
        options.addWidget(self.mode)
        self.workspace=QLineEdit(str(ROOT/'repos'/'sandbox'));self.workspace.setLayoutDirection(Qt.LeftToRight);options.addWidget(self.workspace,1)
        options.addWidget(button('תיקייה',self.choose_workspace))
        self.submit=button('הפעל משימה ↑',self.submit_task,'primary');options.addWidget(self.submit);cl.addLayout(options)
        checks=QHBoxLayout();self.check_path=QLineEdit();self.check_path.setPlaceholderText('קובץ צפוי לבדיקה (אופציונלי)');self.check_contains=QLineEdit();self.check_contains.setPlaceholderText('טקסט נדרש בקובץ (אופציונלי)');checks.addWidget(self.check_path);checks.addWidget(self.check_contains);cl.addLayout(checks)
        cl.addWidget(label('מצב קוד מאפשר פקודות מערכת. מצב מחשב מאפשר גם קלט למסך. ללא בדיקת השלמה, התוצאה תמתין לסקירה.','eyebrow'));main_layout.addWidget(composer)
        self.error=label('','error');self.error.hide();main_layout.addWidget(self.error)
        main_layout.addWidget(label('0.2 · LOCAL     |     סוכן עצמאי: דפדפן, קוד ושליטה במחשב','eyebrow'))
        layout.addWidget(main,1)
        self.setStyleSheet(STYLE)
        if live:
            self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(2000)
            self.health_timer=QTimer(self);self.health_timer.timeout.connect(self.refresh_health);self.health_timer.start(15000)
            self.refresh();self.refresh_health()
        else:
            self.health.setText('●  Qwen3.5 4B · מודל מקומי')

    def request(self,method,path,body,callback,error_callback=None):
        if not self.live:
            return
        work=Request(method,path,body)
        work.setAutoDelete(False)
        self.pending_requests.add(work)
        def succeeded(result):
            try:callback(result)
            finally:
                self.pending_requests.discard(work)
                work.signals.deleteLater()
        def failed(message):
            try:(error_callback or self.show_error)(message)
            finally:
                self.pending_requests.discard(work)
                work.signals.deleteLater()
        work.signals.result.connect(succeeded,Qt.QueuedConnection)
        work.signals.error.connect(failed,Qt.QueuedConnection)
        self.pool.start(work)

    def show_error(self,message):
        self.error.setText(str(message));self.error.show()
        self.submit.setEnabled(True)
        QTimer.singleShot(10000,self.error.hide)

    def preset(self,prompt,mode):
        self.goal.setPlainText(prompt);self.mode.setCurrentIndex(mode);self.goal.setFocus()

    def new_task(self):
        self.selected=None;self.task=None;self.cursor=0;self.events.clear();self.stack.setCurrentIndex(0);self.goal.setFocus()

    def choose_workspace(self):
        path=QFileDialog.getExistingDirectory(self,'בחר תיקיית פרויקט',self.workspace.text())
        if path:self.workspace.setText(path)

    def submit_task(self):
        goal=self.goal.toPlainText().strip()
        if not goal:return
        criteria=[]
        if self.check_path.text().strip():
            check={'path':self.check_path.text().strip()}
            if self.check_contains.text():check['contains']=self.check_contains.text()
            criteria.append(check)
        self.submit.setEnabled(False)
        body={'goal':goal,'workspace':self.workspace.text(),'mode':self.mode.currentData(),'idempotency_key':uuid.uuid4().hex,'criteria':criteria}
        def created(task):
            self.submit.setEnabled(True);self.goal.clear();self.select(task['id']);self.refresh()
        self.request('POST','/tasks',body,created)

    def refresh_health(self):
        def loaded(c):
            model=c['model'];self.health.setText(('●  ' if model['available'] else '○  ')+model['name']+(' · מוכן' if model['available'] else ' · לא זמין')+'\n'+str(c['free_gb'])+' GB פנויים בכונן E')
        self.request('GET','/capabilities',None,loaded)

    def refresh(self):
        if self.poll_pending:return
        self.poll_pending=True
        def failed(message):self.poll_pending=False;self.show_error(message)
        def loaded(tasks):
            self.poll_pending=False;self.tasks.clear()
            for task in tasks:
                item=QListWidgetItem(task['goal'][:34]+'\n'+LABELS.get(task['state'],task['state']));item.setData(Qt.UserRole,task['id']);item.setSizeHint(QSize(190,72));self.tasks.addItem(item)
                if task['id']==self.selected:
                    item.setSelected(True);self.update_task(task)
            if self.selected and not self.event_pending:
                self.event_pending=True
                target=self.selected
                def received(events):
                    self.event_pending=False
                    if target!=self.selected:return
                    for event in events:
                        self.cursor=event['seq'];self.append_event(event)
                def event_failed(message):self.event_pending=False;self.show_error(message)
                self.request('GET',f'/tasks/{target}/events?after={self.cursor}',None,received,event_failed)
        self.request('GET','/tasks',None,loaded,failed)

    def select_item(self,item):self.select(item.data(Qt.UserRole))
    def select(self,task_id):
        self.selected=task_id;self.cursor=0;self.events.clear();self.stack.setCurrentIndex(1);self.refresh()

    def update_task(self,task):
        self.task=task;self.task_title.setText(task['goal'][:180]);self.task_status.setText(LABELS.get(task['state'],task['state'])+' · גרסה '+str(task['revision'])+' · '+task['workspace'])
        self.review.setVisible(task['state']=='waiting_review')
        for name,b in self.control_buttons.items():
            b.setEnabled(task['state'] in {'pause':('queued','running','verifying','waiting_desktop'),'resume':('paused','failed','waiting_user'),'cancel':('queued','running','verifying','paused','failed','waiting_user','waiting_review','waiting_desktop')}[name])

    def append_event(self,event):
        kind,data=event['kind'],event['data']
        if kind=='checkpoint' or (kind=='state' and not data.get('result')):return
        title={'model':'חשיבה מקומית','tool_start':'פעולה','tool_result':'תוצאה','verification':'בדיקת השלמה','state':'סיכום'}.get(kind,kind)
        payload=data.get('text',data.get('result',data))
        if not payload:return
        value=payload if isinstance(payload,str) else json.dumps(payload,ensure_ascii=False,indent=2)
        self.events.append('<p style="color:#bfc3ff">'+html.escape(title+' '+data.get('name',''))+'</p><pre style="white-space:pre-wrap">'+html.escape(value[:12000])+'</pre>')
        self.events.moveCursor(QTextCursor.End)
        if kind=='tool_result' and isinstance(payload,dict):
            shot=payload.get('after',payload)
            if isinstance(shot,dict) and shot.get('path') and self.selected:
                path=Path(shot['path']).resolve()
                if path.is_relative_to((ARTIFACTS/self.selected).resolve()) and path.suffix=='.png' and path.is_file():
                    picture=QPixmap(str(path))
                    if not picture.isNull():
                        picture=picture.scaledToWidth(min(650,self.events.width()-40),Qt.SmoothTransformation)
                        self.events.textCursor().insertImage(picture.toImage())

    def control(self,command):
        if self.task:self.request('POST',f'/tasks/{self.selected}/control',{'command':command,'expected_revision':self.task['revision']},lambda _:self.refresh())

    def stop_all(self):
        self.request('POST','/stop',{},lambda _:self.refresh())

    def review_task(self,decision):
        if not self.task:return
        reason=self.review_note.text().strip() or ('התוצאה נבדקה ואושרה על ידי המשתמש' if decision=='approve' else '')
        if not reason:self.show_error('כתוב מה צריך לתקן');return
        self.request('POST',f'/tasks/{self.selected}/review',{'decision':decision,'expected_revision':self.task['revision'],'reason':reason},lambda _:self.refresh())

def main():
    from .config import DESKTOP_IPC
    from .browser_view import configure_browser,BrowserView
    configure_browser()
    app=QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    # Windows named pipes alone allow competing servers during simultaneous starts.
    from PySide6.QtCore import QLockFile
    ownership=QLockFile(str(STATE/'desktop-instance.lock'))
    ownership.setStaleLockTime(0)
    owns_desktop=ownership.tryLock(0)
    socket=QLocalSocket();socket.connectToServer(DESKTOP_IPC)
    if socket.waitForConnected(700 if owns_desktop else 8000):
        socket.write(b'background' if '--background' in sys.argv else b'show')
        socket.waitForBytesWritten(700);socket.disconnectFromServer();return
    if not owns_desktop:
        raise RuntimeError('Desktop runtime owns the profile but did not answer within 8 seconds; no duplicate browser started')
    server=QLocalServer()
    if not server.listen(DESKTOP_IPC):
        raise RuntimeError('Another desktop runtime owns the application endpoint')
    prepare_fonts(app)
    class BackgroundWindow(Window):
        def closeEvent(self,event):
            self.hide();browser.current().page().setVisible(True);event.ignore()
    window=BackgroundWindow(live=False)
    from PySide6.QtWidgets import QSplitter
    from PySide6.QtCore import QUrl
    from PySide6.QtWebEngineWidgets import QWebEngineView
    workspace=window.takeCentralWidget();workspace.deleteLater()
    # The retired native task UI had global dark QWidget rules. They must not
    # leak into the web shell or its independently styled browser controls.
    window.setStyleSheet('QMainWindow {background:#f5f5f5} QSplitter::handle {background:#dedede;width:1px}')
    window.timer.stop() if hasattr(window,'timer') else None
    shell=QWebEngineView();shell.setUrl(QUrl(f'http://127.0.0.1:{PORT}/?desktop=1'))
    browser=BrowserView();browser.request=window.request
    window.live=True
    app.aboutToQuit.connect(browser.shutdown)
    split=QSplitter(Qt.Horizontal);split.setLayoutDirection(Qt.LeftToRight)
    split.addWidget(shell);split.addWidget(browser);split.setSizes([900,500])
    window.setCentralWidget(split);window.resize(1480,920)
    def show_window():
        window.showNormal();window.raise_();window.activateWindow()
    def apply_presentation(mode):
        if mode not in ('background','split'):raise ValueError('Unknown presentation mode')
        shell.setVisible(mode=='split')
        if mode=='split':split.setSizes([850,850])
        browser.mode_button.setText('הצג שיחה' if mode=='background' else 'דפדפן בלבד')
        browser.mode_button.setProperty('presentation',mode)
        window.setWindowTitle('ChatGPT — הסוכן פועל ברקע' if mode=='background' else 'Local Agent — התכתבות לצד ChatGPT')
    from .preferences import load_presentation
    apply_presentation(load_presentation(STATE))
    browser.mode_button.clicked.connect(lambda:window.request('POST','/chatgpt/presentation',{'mode':'split' if browser.mode_button.property('presentation')=='background' else 'background'},lambda result:apply_presentation(result['mode']),browser.status.setText))
    def connection():
        client=server.nextPendingConnection()
        def received():
            payload=bytes(client.readAll())
            if payload==b'show':show_window()
            elif payload==b'focus-browser':
                show_window();browser.current().setFocus()
            elif payload==b'quit':app.quit()
            elif payload.startswith(b'{'):
                try:
                    data=json.loads(payload)
                    if 'browser_extensions' in data:
                        result=browser.extensions.execute(**data['browser_extensions'])
                        client.write(json.dumps(result).encode()+b'\n');client.flush();client.disconnectFromServer();return
                    if 'virtual_drag' in data:
                        from .browser_virtual_input import drag
                        args=data['virtual_drag']
                        view=next((browser.tabs.widget(i) for i in range(browser.tabs.count()) if browser.tabs.widget(i).page().devToolsId()==args['target_id']),None)
                        if view is None:raise ValueError('Browser target closed')
                        def finished(result):
                            if client.state()==QLocalSocket.ConnectedState:
                                client.write(json.dumps(result).encode()+b'\n');client.flush();client.disconnectFromServer()
                        drag(view,args,finished);return
                    if 'presentation' in data:
                        show_window();apply_presentation(data['presentation'])
                        client.write(json.dumps({'mode':data['presentation'],'agent_visible':shell.isVisible()}).encode()+b'\n');client.flush();client.disconnectFromServer();return
                    if 'close_targets' in data:
                        result=browser.close_targets(data['close_targets'])
                        client.write(json.dumps(result).encode()+b'\n');client.flush();client.disconnectFromServer();return
                    if 'capture_target' in data:
                        from PySide6.QtCore import QBuffer,QIODevice
                        import base64
                        result={'error':'Browser tab was closed'}
                        for index in range(browser.tabs.count()):
                            view=browser.tabs.widget(index)
                            if view.page().devToolsId()==data['capture_target']:
                                # Capture the application's rendered widget, never the physical desktop.
                                pixmap=view.grab();buffer=QBuffer();buffer.open(QIODevice.WriteOnly)
                                if not pixmap.isNull() and pixmap.save(buffer,'JPEG',80):
                                    result={'image':'data:image/jpeg;base64,'+base64.b64encode(bytes(buffer.data())).decode(),'width':view.width(),'height':view.height()}
                                else:result={'error':'Browser has no rendered surface yet'}
                                break
                        client.write(json.dumps(result).encode()+b'\n');client.flush();client.disconnectFromServer();return
                    if 'select_target' in data:
                        for index in range(browser.tabs.count()):
                            if browser.tabs.widget(index).page().devToolsId()==data['select_target']:
                                browser.tabs.setCurrentIndex(index);show_window();browser.publish_tabs();break
                        client.disconnectFromServer();return
                    if 'reload_target' in data:
                        view=next((browser.tabs.widget(i) for i in range(browser.tabs.count()) if browser.tabs.widget(i).page().devToolsId()==data['reload_target']),None)
                        if view is None or view.url().toString()!=data['expected_url']:
                            result={'error':'Target closed or URL changed; no reload performed'}
                        else:
                            from PySide6.QtWebEngineCore import QWebEnginePage
                            view.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)
                            view.reload()
                            result={'requested':True,'target_id':data['reload_target'],'url':data['expected_url']}
                        client.write(json.dumps(result).encode()+b'\n');client.flush();client.disconnectFromServer();return
                    if 'prepare_target' in data:
                        view=next((browser.tabs.widget(i) for i in range(browser.tabs.count()) if browser.tabs.widget(i).page().devToolsId()==data['prepare_target']),None)
                        if view is None:result={'error':'Target was closed'}
                        else:
                            from PySide6.QtWebEngineCore import QWebEnginePage
                            if view.width()<=0 or view.height()<=0:view.resize(1280,800)
                            view.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)
                            view.page().setVisible(True)
                            result={'prepared':True,'target_id':data['prepare_target'],'width':view.width(),'height':view.height()}
                        client.write(json.dumps(result).encode()+b'\n');client.flush();client.disconnectFromServer();return
                    if 'print_target' in data:
                        from .file_library import FileLibrary
                        view=next((browser.tabs.widget(i) for i in range(browser.tabs.count()) if browser.tabs.widget(i).page().devToolsId()==data['print_target']),None)
                        expected=data['expected_url'];name=data.get('name','page.pdf')
                        def printed(raw):
                            try:
                                if view is None or view.url().toString()!=expected:raise ValueError('Page changed before PDF completed')
                                if not raw:raise ValueError('Qt produced an empty PDF')
                                result=FileLibrary().import_bytes(name,bytes(raw),'application/pdf','Embedded browser PDF: '+expected)
                            except Exception as exc:result={'error':str(exc)}
                            if client.state()==QLocalSocket.ConnectedState:
                                client.write(json.dumps(result).encode()+b'\n');client.flush();client.disconnectFromServer()
                        if view is None or view.url().toString()!=expected:printed(b'');return
                        view.page().printToPdf(printed)
                        return
                    url=QUrl(data['open_url'])
                    if url.scheme() in ('http','https'):
                        browser.new_tab().setUrl(url);show_window()
                except (ValueError,KeyError):pass
            client.disconnectFromServer()
        client.readyRead.connect(received)
        client.disconnected.connect(client.deleteLater)
        if client.bytesAvailable():received()
    server.newConnection.connect(connection)
    tray=QSystemTrayIcon(app.style().standardIcon(QStyle.SP_ComputerIcon),app)
    tray.setToolTip('Local Agent — פועל ברקע')
    menu=QMenu();menu.addAction('פתיחת הסוכן',show_window)
    menu.addAction('יציאה מהדפדפן והממשק',app.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: show_window() if reason==QSystemTrayIcon.DoubleClick else None)
    tray.show()
    window.show()
    if '--background' in sys.argv:
        def background():
            window.hide()
            shell.resize(1100,850);shell.page().setVisible(True)
            browser.current().resize(1280,800)
            browser.current().page().setVisible(True)
        QTimer.singleShot(500,background)
    sys.exit(app.exec())

def prepare_fonts(app):
    for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf'):
        path=Path('C:/Windows/Fonts')/name
        if path.is_file():QFontDatabase.addApplicationFont(str(path))
    app.setFont(QFont('Segoe UI',10))

if __name__=='__main__':main()
