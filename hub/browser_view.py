"""Application-owned Chromium view, not an external browser installation."""
import json
import os
from pathlib import Path
import uuid
from PySide6.QtCore import QUrl,Qt,QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,QLabel,QTabWidget,QFileDialog,QDialog,QApplication,QToolButton,QMenu,QStyle,QSizePolicy
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from .config import ROOT,STATE,CDP_PORT
from .browser_profile import persistent_profile,save_tabs,load_tabs
from .file_library import FileLibrary

def configure_browser():
    # Called before QApplication. Never expose CDP on a LAN interface.
    if ROOT.resolve()!=Path('E:/AI').resolve() and CDP_PORT==9223:
        raise RuntimeError('An isolated browser requires a separate LOCAL_AGENT_CDP_PORT')
    os.environ['QTWEBENGINE_REMOTE_DEBUGGING']=f'127.0.0.1:{CDP_PORT}'
    flags='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    # A local, reversible software-only renderer fallback for problematic Qt GPU drivers.
    # This affects Qt Chromium only; Ollama model offloading remains unchanged.
    if (STATE/'browser-software-rendering.enabled').is_file():
        flags+=' --disable-gpu'
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS']=flags

class Page(QWebEnginePage):
    def acceptNavigationRequest(self,url,kind,is_main_frame):
        return url.scheme() in ('http','https','about','data')

class View(QWebEngineView):
    def __init__(self,owner):
        super().__init__()
        self.owner=owner
        self.setPage(Page(owner.profile,self))
    def createWindow(self,kind):
        return self.owner.new_tab()

def visually_blank(image):
    """True only for a nearly solid white visible renderer surface."""
    if image.isNull() or image.width()<=0 or image.height()<=0:
        return False
    thumb=image.scaled(24,16,Qt.IgnoreAspectRatio,Qt.FastTransformation)
    total=thumb.width()*thumb.height()
    if not total:return False
    white=sum(1 for y in range(thumb.height()) for x in range(thumb.width())
              if min(thumb.pixelColor(x,y).red(),
                     thumb.pixelColor(x,y).green(),
                     thumb.pixelColor(x,y).blue())>=246)
    return white>=total-1


def should_enable_compatibility(url,visible,already_recovered,blank_cycles):
    # Local dashboards and OAuth callbacks require JavaScript. A blank frame
    # during initial hydration must not replace their page with JS disabled.
    host=url.host().casefold().strip('[]') if url is not None else ''
    if host in ('127.0.0.1','localhost','::1'):
        return False
    return (visible and not already_recovered and blank_cycles>=2
            and url.scheme() in ('http','https'))


def should_restore_javascript(previous_host,url):
    """A JS-disabled readable tab needs full JS on a different website."""
    if url is None or url.scheme() not in ('http','https'):
        return False
    old=str(previous_host or '').casefold().strip('[]')
    new=url.host().casefold().strip('[]')
    return bool(old and new and old!=new)


class BrowserView(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName('agentBrowser')
        # A custom QWidget does not paint a stylesheet background by default.
        # Without this the old dark parent showed through transparent controls.
        self.setAttribute(Qt.WA_StyledBackground,True)
        self.setStyleSheet('''
            QWidget#agentBrowser { background: #f5f5f5; color:#242424; font-family:'Segoe UI'; }
            QWidget#agentBrowser QPushButton, QWidget#agentBrowser QToolButton { background: #f5f5f5; color: #292929;
                border: 1px solid transparent; border-radius: 7px; padding: 5px 8px; font-size:13px; }
            QWidget#agentBrowser QPushButton:hover, QWidget#agentBrowser QToolButton:hover { background: #e5e5e5; border-color:#d7d7d7; }
            QWidget#agentBrowser QToolButton:disabled { color:#999; }
            QWidget#agentBrowser QToolButton::menu-indicator { image:none; width:0; }
            QWidget#agentBrowser QMenu { background:#fff; color:#242424; border:1px solid #ddd; padding:6px; }
            QWidget#agentBrowser QMenu::item { padding:9px 18px; }
            QWidget#agentBrowser QMenu::item:selected { background:#e8e8e8; color:#171717; }
            QWidget#agentBrowser QLineEdit { background: white; color: #242424;
                selection-background-color:#d9e5ff; selection-color:#171717;
                border: 1px solid #dedede; border-radius: 10px; padding: 7px 10px; font-size:13px; }
            QWidget#agentBrowser QLineEdit:focus { border-color:#9caed1; }
            QWidget#agentBrowser QTabWidget::pane { background:white; border: 1px solid #dedede; }
            QWidget#agentBrowser QTabBar::tab { background: #ededed; color: #555;
                padding: 8px 12px; min-width: 65px; max-width: 180px; }
            QWidget#agentBrowser QTabBar::tab:selected { background: white; color: #171717; }
            QWidget#agentBrowser QTabBar::tab:hover { background:#e4e4e4; }
            QWidget#agentBrowser QLabel { color: #606060; font-size: 12px; }
        ''')
        self.setLayoutDirection(Qt.LeftToRight)
        self.profile=persistent_profile(self,STATE,ROOT/'cache'/'browser')
        from .browser_extensions import BrowserExtensions
        self.extensions=BrowserExtensions(self.profile,self)
        self.files=FileLibrary();self.downloads={};self.shutting_down=False
        self.profile.downloadRequested.connect(self.download)
        layout=QVBoxLayout(self);layout.setContentsMargins(8,8,8,8);layout.setSpacing(6)
        bar=QHBoxLayout();bar.setSpacing(4)
        for title,icon,action in [('חזרה',QStyle.SP_ArrowBack,lambda:self.current().back()),('קדימה',QStyle.SP_ArrowForward,lambda:self.current().forward()),('רענון',QStyle.SP_BrowserReload,lambda:self.current().reload())]:
            b=QToolButton();b.setIcon(self.style().standardIcon(icon));b.setToolTip(title);b.setAccessibleName(title);b.setFixedSize(32,34);b.clicked.connect(action);bar.addWidget(b)
        self.address=QLineEdit();self.address.setObjectName('browserAddress');self.address.setAccessibleName('כתובת האתר');self.address.setLayoutDirection(Qt.LeftToRight);self.address.setMinimumWidth(120);self.address.setPlaceholderText('כתובת אתר או קישור');self.address.returnPressed.connect(self.navigate);bar.addWidget(self.address,1)
        go=QToolButton();go.setText('פתח');go.setAccessibleName('פתח כתובת');go.setFixedHeight(34);go.clicked.connect(self.navigate);bar.addWidget(go)
        add=QToolButton();add.setText('+');add.setToolTip('לשונית חדשה');add.setAccessibleName('לשונית חדשה');add.setFixedSize(32,34);add.clicked.connect(lambda:self.new_tab());bar.addWidget(add)
        more=QToolButton();more.setObjectName('browserMenu');more.setText('⋯');more.setToolTip('כלי הדפדפן');more.setAccessibleName('כלי הדפדפן');more.setFixedSize(34,34)
        menu=QMenu(more);menu.setLayoutDirection(Qt.RightToLeft)
        menu.addAction('העברת כניסה מ־Chrome',self.pair)
        menu.addAction('ניהול תוספים',lambda:self.extensions.show(self))
        menu.addAction('רכיבים שמורים',lambda:self.annotation.show_saved())
        more.setMenu(menu);more.setPopupMode(QToolButton.InstantPopup);bar.addWidget(more)
        self.hide_button=QToolButton();self.hide_button.setText('הסתר דפדפן ×');self.hide_button.setAccessibleName('הסתר דפדפן');self.hide_button.setToolTip('הסתר את התצוגה; הלשוניות והחיבור ממשיכים ברקע');bar.addWidget(self.hide_button)
        self.annotate_button=QToolButton();self.annotate_button.setText('בחר רכיב');self.annotate_button.setObjectName('browserAnnotate');self.annotate_button.setAccessibleName('בחר רכיב או אזור');bar.addWidget(self.annotate_button)
        layout.addLayout(bar)
        self.tabs=QTabWidget();self.tabs.setTabsClosable(True);self.tabs.tabCloseRequested.connect(self.close_tab);self.tabs.currentChanged.connect(self.changed);layout.addWidget(self.tabs,1)
        self.tabs.tabBar().setExpanding(False);self.tabs.tabBar().setElideMode(Qt.ElideRight);self.tabs.tabBar().setUsesScrollButtons(True)
        self.status=QLabel('דפדפן עצמאי · הכניסות לחשבונות והקבצים נשמרים במחשב')
        self.status.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);self.status.setWordWrap(True);self.status.setMaximumHeight(36);self.status.setLayoutDirection(Qt.RightToLeft)
        footer=QHBoxLayout();footer.addWidget(self.status,1)
        self.full_site_button=QPushButton('הפעל JavaScript מחדש');self.full_site_button.setToolTip('נסה מחדש את העמוד עם JavaScript מלא');self.full_site_button.clicked.connect(self.retry_full_site);self.full_site_button.setVisible(False);footer.addWidget(self.full_site_button)
        self.mode_button=QPushButton('ChatGPT בלבד');footer.addWidget(self.mode_button);layout.addLayout(footer)
        urls,selected=load_tabs(STATE/'browser-session.json')
        for url in urls or ['about:blank']:
            view=self.new_tab()
            if url!='about:blank':view.setUrl(QUrl(url))
        self.tabs.setCurrentIndex(selected)
        self.metadata_timer=QTimer(self);self.metadata_timer.timeout.connect(self.publish_tabs);self.metadata_timer.start(1500)
        # Poll only the current VISIBLE tab: hidden Qt widgets are blank by design.
        self.render_timer=QTimer(self);self.render_timer.timeout.connect(self.check_render);self.render_timer.start(4500)
        endpoint={'url':f'http://127.0.0.1:{CDP_PORT}','pid':os.getpid(),'profile':str(STATE/'browser-profile'),'instance':uuid.uuid4().hex}
        (STATE/'browser-endpoint.json').write_text(json.dumps(endpoint),encoding='utf-8')

        from .browser_annotation import BrowserAnnotation
        self.annotation=BrowserAnnotation(self,self.annotate_button)
        self.selections_button=QToolButton();self.selections_button.setText('רכיבים');self.selections_button.setObjectName('browserSelections');self.selections_button.clicked.connect(self.annotation.show_saved);bar.addWidget(self.selections_button)

    def tab_loaded(self,view,ok):
        if view is not self.current():return
        if view.compatibility_mode:
            self.status.setText('מצב תאימות: JavaScript כבוי בלשונית זו בלבד; פעולות דינמיות עלולות להיות מוגבלות')
        else:
            self.status.setText('הדף נטען' if ok else 'טעינת הדף נכשלה')
        if not ok and not view.compatibility_mode:
            QTimer.singleShot(700,lambda v=view:self.check_render(v,failed=True))

    def check_render(self,view=None,failed=False):
        import shiboken6
        view=view or self.current()
        if self.shutting_down or view is None or not shiboken6.isValid(view):
            return
        if (view is not self.current() or not self.isVisible() or
                not self.window().isVisible() or not view.isVisible() or
                view.width()<120 or view.height()<120):
            return
        if view.compatibility_mode or view.url().scheme() not in ('http','https'):
            return
        image=view.grab().toImage()
        view.blank_cycles=view.blank_cycles+1 if visually_blank(image) else 0
        if failed and view.blank_cycles:view.blank_cycles=2
        if should_enable_compatibility(view.url(),True,view.compatibility_mode,view.blank_cycles):
            self.enable_readable_mode(view)

    def replace_page(self,view,*,javascript):
        old=view.page()
        fresh=Page(self.profile,view)
        fresh.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled,javascript)
        view.setPage(fresh)
        fresh.windowCloseRequested.connect(lambda v=view:self.remove_closed_tab(v))
        old.deleteLater()

    def enable_readable_mode(self,view):
        # Never replay inputs; create a fresh GET page using the same persistent
        # profile/cookies only when the selected visible surface is actually blank.
        if view is not self.current() or view.compatibility_mode:return
        url=view.url()
        if url.scheme() not in ('http','https'):return
        view.compatibility_mode=True
        view.compatibility_host=url.host().casefold().strip('[]')
        view.blank_cycles=0
        self.replace_page(view,javascript=False)
        view.setUrl(url)
        self.full_site_button.setVisible(True)
        self.status.setText('מסך לבן זוהה: טעינה במצב קריאה ללא JavaScript, עבור לשונית זו בלבד')
        self.publish_tabs()

    def retry_full_site(self):
        view=self.current()
        if not view or not view.compatibility_mode:return
        url=view.url()
        view.compatibility_mode=False
        view.compatibility_host=None
        view.blank_cycles=0
        self.replace_page(view,javascript=True)
        view.setUrl(url)
        self.full_site_button.setVisible(False)
        self.status.setText('מנסה טעינה מלאה עם JavaScript; אם יתקע שוב, מצב הקריאה יחזור')
        self.publish_tabs()

    def publish_tabs(self):
        if self.shutting_down:return
        tabs=[{'target_id':self.tabs.widget(i).page().devToolsId(),'url':self.tabs.widget(i).url().toString(),'selected':i==self.tabs.currentIndex()} for i in range(self.tabs.count())]
        path=STATE/'browser-tabs.json';temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'tabs':tabs}),encoding='utf-8');temporary.replace(path)
        save_tabs(STATE/'browser-session.json',[t['url'] for t in tabs],self.tabs.currentIndex())

    def shutdown(self):
        if self.shutting_down:return
        self.publish_tabs();self.shutting_down=True;self.metadata_timer.stop();self.render_timer.stop()
        # Qt requires all pages to be destroyed before the profile flushes storage.
        import shiboken6
        for item,record in list(self.downloads.values()):
            if not item.isFinished():
                item.cancel();self.files.fail(record['id'],'Browser closed before download completed')
        for index in range(self.tabs.count()):shiboken6.delete(self.tabs.widget(index).page())
        shiboken6.delete(self.profile)

    def pair(self):
        bridge=Path(__file__).resolve().parent.parent/'chrome-session-bridge'
        if not (bridge/'manifest.json').is_file():
            self.status.setText('תוסף ההעברה חסר בהתקנה: '+str(bridge));return
        def show(result):
            dialog=QDialog(self);dialog.setWindowTitle('העברת סשן מ־Chrome');dialog.resize(620,260)
            layout=QVBoxLayout(dialog)
            note=QLabel(f'זהו חיבור לאתר יחיד, ולא ייבוא מלא של פרופיל Chrome.\nטען פעם אחת את התוסף שבתיקייה:\n{bridge}\nדרך chrome://extensions > Developer mode > Load unpacked.\nפתח את האתר שבו אתה מחובר, לחץ על התוסף והדבק את הקוד.\nרק נתוני האתר הנבחר יועברו, ישירות למחשב הזה. הקוד תקף ל־3 דקות.\nאתרים מסוימים עשויים לדרוש כניסה מחדש.');note.setWordWrap(True);layout.addWidget(note)
            code=QLineEdit(result['code']);code.setReadOnly(True);layout.addWidget(code)
            copy=QPushButton('העתק קוד');copy.clicked.connect(lambda:QApplication.clipboard().setText(result['code']));layout.addWidget(copy)
            dialog.exec()
        if hasattr(self,'request'):
            self.status.setText('יוצר קוד להעברת כניסה…')
            self.request('POST','/browser/pair',{},show,lambda message:self.status.setText('יצירת קוד נכשלה: '+str(message)))
        else:self.status.setText('אין חיבור לשירות הסוכן; לא נוצר קוד העברה')

    def current(self):return self.tabs.currentWidget()
    def new_tab(self):
        view=View(self)
        view.compatibility_mode=False
        view.compatibility_host=None
        view.blank_cycles=0
        index=self.tabs.addTab(view,'דף חדש');self.tabs.setCurrentIndex(index)
        view.page().windowCloseRequested.connect(lambda v=view:self.remove_closed_tab(v))
        view.titleChanged.connect(lambda title,v=view:self.tab_title(v,title))
        view.urlChanged.connect(lambda url,v=view:self.url_changed(v,url))
        view.loadFinished.connect(lambda ok,v=view:self.tab_loaded(v,ok))
        view.setHtml('''<!doctype html><html lang="he" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>דפדפן MellowCodex</title><style>html{color-scheme:light dark}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#fafafa;color:#252525;font:15px/1.7 "Segoe UI",sans-serif}main{max-width:420px;padding:32px;text-align:center}.mark{font-size:32px;color:#777}h1{font-size:27px;font-weight:550;letter-spacing:-.5px;margin:16px 0 8px}p{margin:0;color:#737373}small{display:block;margin-top:28px;font-size:12px;color:#888}@media(prefers-color-scheme:dark){body{background:#202020;color:#ededed}p,small{color:#aaa}}</style><main><div class="mark" aria-hidden="true">◎</div><h1>לאן ניגשים?</h1><p>הזן כתובת בשורת הכתובת, או בקש מהסוכן לפתוח אתר ולעבוד בו.</p><small>הדפדפן של MellowCodex · הכניסות נשמרות בפרופיל המקומי</small></main></html>''',QUrl('about:blank'))
        return view
    def tab_title(self,view,title):
        index=self.tabs.indexOf(view)
        if index<0:return
        self.tabs.setTabText(index,title or 'דף חדש');self.tabs.setTabToolTip(index,title)
    def close_tab(self,index):
        self.tabs.widget(index).page().triggerAction(QWebEnginePage.WebAction.RequestClose)
    def remove_closed_tab(self,view):
        index=self.tabs.indexOf(view)
        if index<0:return
        self.tabs.removeTab(index);view.deleteLater()
        if not self.tabs.count():self.new_tab()
        self.publish_tabs()
    def close_targets(self,targets):
        views={self.tabs.widget(i).page().devToolsId():self.tabs.widget(i) for i in range(self.tabs.count())}
        if not targets or any(t not in views for t in targets):
            return {'error':'Tab inventory changed; list tabs again before closing'}
        for target in targets:
            views[target].page().triggerAction(QWebEnginePage.WebAction.RequestClose)
        return {'requested':targets,'note':'Unsaved-work dialogs are not automatically accepted; verify the remaining tabs.'}
    def changed(self,index):
        if self.current():self.address.setText(self.current().url().toString())
        self.full_site_button.setVisible(bool(self.current() and self.current().compatibility_mode))
    def url_changed(self,view,url):
        view.blank_cycles=0
        if view.compatibility_mode and should_restore_javascript(getattr(view,'compatibility_host',None),url):
            # Restore scripts for a DIFFERENT host without reloading the page
            # or replaying a navigation/submission that may have side effects.
            view.compatibility_mode=False
            view.compatibility_host=None
            view.page().settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled,True)
            if view is self.current():
                self.full_site_button.setVisible(False)
                self.status.setText('JavaScript הופעל מחדש עבור האתר החדש')
        if view is self.current():self.address.setText(url.toString())
    def navigate(self):
        url=QUrl.fromUserInput(self.address.text().strip())
        if url.scheme() not in ('http','https'):
            self.status.setText('יש להזין כתובת http או https');return
        self.current().setUrl(url)
    def download(self,item):
        # Store exactly the downloaded bytes. Downloading never executes an installer.
        record=self.files.reserve(item.suggestedFileName(),'browser download',item.mimeType())
        path=Path(record['path']);self.downloads[item.id()]=(item,record)
        item.setDownloadDirectory(str(path.parent));item.setDownloadFileName(path.name)
        def changed():
            if not item.isFinished():return
            from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
            if item.state()==QWebEngineDownloadRequest.DownloadCompleted:
                self.files.finish(record['id']);self.status.setText('הקובץ נשמר: '+str(path))
            else:self.files.fail(record['id'],item.interruptReasonString() or 'Download cancelled')
            self.downloads.pop(item.id(),None)
        item.stateChanged.connect(changed);item.isFinishedChanged.connect(changed)
        item.accept();self.status.setText('מוריד: '+record['name'])
