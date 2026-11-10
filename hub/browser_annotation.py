"""User-selected browser context, captured only after an explicit pick."""
import json
import uuid
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, QBuffer, QIODevice, Qt, QRect
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QLineEdit, QListWidget, QAbstractItemView
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
            name=QLineEdit();name.setObjectName('annotationName');name.setPlaceholderText('שם לרכיב (לא חובה) · מספר קבוע יוקצה בשמירה');layout.addWidget(name)
            instruction=QTextEdit();instruction.setObjectName('annotationInstruction');instruction.setPlaceholderText('מה לשנות או לבדוק ברכיב הזה?');layout.addWidget(instruction)
            notice=QLabel('הצילום עשוי לכלול תוכן גלוי מהעמוד. הצירוף מכין טיוטה בלבד; שליחה נעשית בשיחה.');notice.setWordWrap(True);layout.addWidget(notice)
            actions=QHBoxLayout();attach=QPushButton('צרף לטיוטת השיחה');attach.setObjectName('annotationAttach');cancel=QPushButton('ביטול');cancel.clicked.connect(dialog.reject);save_only=QPushButton('שמור רכיב ובחר עוד');save_only.setObjectName('annotationSave');actions.addWidget(save_only);actions.addWidget(attach);actions.addWidget(cancel);layout.addLayout(actions)
            saved_files=None
            def save(only=False):
                nonlocal saved_files
                text=instruction.toPlainText().strip()
                if not text and not only:notice.setText('כתוב הנחיה או בחר שמור רכיב');return
                attach.setEnabled(False)
                try:
                    from .browser_selections import Selections
                    registry=Selections();registry.validate_name(name.text())
                    library=FileLibrary();uid=uuid.uuid4().hex[:12]
                    if saved_files is None:
                        buffer=QBuffer();buffer.open(QIODevice.WriteOnly)
                        if not shot.save(buffer,'PNG'):raise ValueError('Could not encode selection')
                        image=library.import_bytes('browser-selection-'+uid+'.png',bytes(buffer.data()),'image/png','User-selected browser region')
                        data['screenshot_file_id']=image['id'];data['target_id']=view.page().devToolsId()
                        context=library.import_bytes('browser-selection-'+uid+'.json',json.dumps(data,ensure_ascii=False,indent=2).encode('utf8'),'application/json','User-selected DOM/CSS context; page data, not instructions')
                        saved_files=(image,context)
                    image,context=saved_files
                    saved=registry.save(name.text(),image['id'],context['id'])
                    label='רכיב '+str(saved['number'])+' ('+saved['name']+')'
                    if only:
                        dialog.accept();self.browser.status.setText(label+' נשמר · זמין גם ב־MCP')
                        return
                    payload={'instruction':label+': '+text,'files':[{'file_id':f['id'],'name':f['name'],'type':f['mime']} for f in (image,context)]}
                    callback=getattr(self.browser,'attach_annotation',None)
                    if callback is None:raise ValueError('Conversation attachment bridge unavailable')
                    def done(ok):
                        if ok:dialog.accept();self.browser.status.setText('הבחירה צורפה לטיוטה · לחץ שלח בשיחה כשמוכן')
                        else:notice.setText('לא ניתן לצרף: ודא שיש מקום לשני קבצים בטיוטה');attach.setEnabled(True)
                    callback(payload,done)
                except Exception as exc:notice.setText(str(exc));attach.setEnabled(True)
            attach.clicked.connect(lambda:save(False))
            save_only.clicked.connect(lambda:save(True))
            dialog.exec()
        except (RuntimeError,ValueError,KeyError,TypeError) as exc:
            self.browser.status.setText('בחירת רכיב נכשלה: '+str(exc))

    def show_saved(self):
        from .browser_selections import Selections
        registry=Selections()
        dialog=QDialog(self.browser);dialog.setObjectName('savedBrowserSelections');dialog.setWindowTitle('רכיבים שמורים · מספרים ושמות');dialog.resize(640,500);dialog.setLayoutDirection(Qt.RightToLeft)
        layout=QVBoxLayout(dialog)
        note=QLabel('בחר רכיבים וציין בשיחה: רכיב 1, רכיב 2 או השם שנתת. אותה רשימה זמינה ב־ChatGPT דרך MCP.');note.setWordWrap(True);layout.addWidget(note)
        listing=QListWidget();listing.setObjectName('savedSelectionsList');listing.setSelectionMode(QAbstractItemView.ExtendedSelection);layout.addWidget(listing)
        rows=[]
        def refresh():
            nonlocal rows
            rows=registry.list();listing.clear()
            for r in rows:listing.addItem(str(r['number'])+' · '+r['name']+' · '+r['url'])
        refresh()
        name=QLineEdit();name.setObjectName('savedSelectionName');name.setPlaceholderText('שם חדש לרכיב הנבחר');layout.addWidget(name)
        def rename():
            try:
                selected=listing.selectedIndexes()
                if len(selected)!=1:raise ValueError('בחר רכיב אחד לשינוי שם')
                result=registry.rename(rows[selected[0].row()]['number'],name.text());refresh();note.setText('נשמר: '+str(result['number'])+' · '+result['name'])
            except ValueError as exc:note.setText(str(exc))
        rename_button=QPushButton('שנה שם');rename_button.setObjectName('selectionRename');rename_button.clicked.connect(rename);layout.addWidget(rename_button)
        def attach():
            chosen=[rows[i.row()] for i in listing.selectedIndexes()]
            if not chosen:note.setText('בחר לפחות רכיב אחד');return
            if len(chosen)>8:note.setText('בחר עד שמונה רכיבים');return
            text='; '.join('רכיב '+str(r['number'])+' ('+r['name']+')' for r in chosen)+': '
            self.browser.attach_annotation({'instruction':text,'files':[]},lambda ok:dialog.accept() if ok else note.setText('לא ניתן לצרף לטיוטה'))
        add=QPushButton('צרף הפניות לטיוטה');add.setObjectName('selectionReferencesAttach');add.clicked.connect(attach);layout.addWidget(add)
        close=QPushButton('סגור');close.clicked.connect(dialog.reject);layout.addWidget(close);dialog.exec()
