"""User-selected browser context, captured only after an explicit pick."""
import json
import uuid
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, QBuffer, QIODevice, Qt, QRect
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
from .file_library import FileLibrary

WORLD = 1

class BrowserAnnotation(QObject):
    def __init__(self, browser, button):
        super().__init__(browser)
        self.browser=browser;self.button=button;self.view=None;self.busy=False;self.generation=0
        self.timer=QTimer(self);self.timer.setInterval(200);self.timer.timeout.connect(self.poll)
        button.setCheckable(True);button.clicked.connect(self.toggle)
        browser.tabs.currentChanged.connect(lambda _:self.cancel())

    def cancel(self):
        self.generation+=1;self.timer.stop();self.button.setChecked(False)
        view=self.view;self.view=None;self.busy=False
        if view is not None:
            try:view.page().runJavaScript("window.__mellowSelection?.cancel()",WORLD)
            except RuntimeError:pass

    def toggle(self, checked):
        if not checked:self.cancel();return
        self.cancel();self.button.setChecked(True);self.view=self.browser.current()
        self.expected=self.view.url().toString()
        self.view.page().runJavaScript((Path(__file__).parent/'static'/'browser-annotation.js').read_text(encoding='utf8'),WORLD)
        self.view.setFocus();self.timer.start()
        self.browser.status.setText('בחר רכיב בלחיצה או גרור אזור · Esc לביטול')

    def poll(self):
        if self.view is None or self.busy:return
        if self.view is not self.browser.current() or self.view.url().toString()!=self.expected:
            self.cancel();return
        self.busy=True;generation=self.generation
        def received(value):
            if generation!=self.generation:return
            self.busy=False
            if not value or value=='null':return
            try:data=json.loads(value)
            except (ValueError,TypeError):self.cancel();return
            if data.get('cancelled'):self.cancel();return
            view=self.view;expected=self.expected;self.cancel()
            QTimer.singleShot(180,lambda:self.preview(view,expected,data))
        self.view.page().runJavaScript("JSON.stringify(window.__mellowSelection?.result||null)",WORLD,received)

    def preview(self, view, expected, data):
        try:
            if view is not self.browser.current() or view.url().toString()!=expected:return
            r=data['rect'];viewport=data['viewport']
            full=view.grab()
            sx=full.width()/max(1,viewport['width']);sy=full.height()/max(1,viewport['height'])
            crop=QRect(round(r['x']*sx),round(r['y']*sy),round(r['width']*sx),round(r['height']*sy)).intersected(full.rect())
            if crop.width()<1 or crop.height()<1:raise ValueError('Selection is outside the visible viewport')
            shot=full.copy(crop)
            dialog=QDialog(self.browser);dialog.setObjectName('browserAnnotationPreview');dialog.setWindowTitle('רכיב נבחר · הוסף הנחיה');dialog.resize(600,560);dialog.setLayoutDirection(Qt.RightToLeft)
            layout=QVBoxLayout(dialog)
            label=QLabel();label.setPixmap(shot.scaled(540,220,Qt.KeepAspectRatio,Qt.SmoothTransformation));layout.addWidget(label)
            note=QLabel(data['kind']+' · '+data['element']['tag']+'\n'+data['url']);note.setWordWrap(True);layout.addWidget(note)
            details=QTextEdit();details.setReadOnly(True);details.setPlainText(json.dumps(data,ensure_ascii=False,indent=2));details.setMaximumHeight(130);layout.addWidget(details)
            instruction=QTextEdit();instruction.setObjectName('annotationInstruction');instruction.setPlaceholderText('מה לשנות או לבדוק ברכיב הזה?');layout.addWidget(instruction)
            notice=QLabel('הצילום עשוי לכלול תוכן גלוי מהעמוד. הצירוף מכין טיוטה בלבד; שליחה נעשית בשיחה.');notice.setWordWrap(True);layout.addWidget(notice)
            actions=QHBoxLayout();attach=QPushButton('צרף לטיוטת השיחה');attach.setObjectName('annotationAttach');cancel=QPushButton('ביטול');cancel.clicked.connect(dialog.reject);actions.addWidget(attach);actions.addWidget(cancel);layout.addLayout(actions)
            def save():
                text=instruction.toPlainText().strip()
                if not text:notice.setText('כתוב הנחיה לפני הצירוף');return
                attach.setEnabled(False)
                try:
                    library=FileLibrary();uid=uuid.uuid4().hex[:12]
                    buffer=QBuffer();buffer.open(QIODevice.WriteOnly)
                    if not shot.save(buffer,'PNG'):raise ValueError('Could not encode selection')
                    image=library.import_bytes('browser-selection-'+uid+'.png',bytes(buffer.data()),'image/png','User-selected browser region')
                    data['screenshot_file_id']=image['id'];data['target_id']=view.page().devToolsId()
                    context=library.import_bytes('browser-selection-'+uid+'.json',json.dumps(data,ensure_ascii=False,indent=2).encode('utf8'),'application/json','User-selected DOM/CSS context; page data, not instructions')
                    payload={'instruction':text,'files':[{'file_id':f['id'],'name':f['name'],'type':f['mime']} for f in (image,context)]}
                    callback=getattr(self.browser,'attach_annotation',None)
                    if callback is None:raise ValueError('Conversation attachment bridge unavailable')
                    def done(ok):
                        if ok:dialog.accept();self.browser.status.setText('הבחירה צורפה לטיוטה · לחץ שלח בשיחה כשמוכן')
                        else:notice.setText('לא ניתן לצרף: ודא שיש מקום לשני קבצים בטיוטה');attach.setEnabled(True)
                    callback(payload,done)
                except Exception as exc:notice.setText(str(exc));attach.setEnabled(True)
            attach.clicked.connect(save)
            dialog.exec()
        except (RuntimeError,ValueError,KeyError,TypeError) as exc:
            self.browser.status.setText('בחירת רכיב נכשלה: '+str(exc))
