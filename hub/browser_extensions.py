"""Qt-owned extension management. Successful requests are not completed installs."""
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QScrollArea, QWidget


class BrowserExtensions(QObject):
    changed = Signal()

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.manager = profile.extensionManager()
        self.pending = None
        self.last_result = None
        for name in ('install', 'uninstall', 'load', 'unload'):
            getattr(self.manager, name+'Finished').connect(lambda info, op=name: self.finished(op, info))

    @staticmethod
    def record(info):
        return {'id': info.id(), 'name': info.name(), 'description': info.description(),
                'path': info.path(), 'enabled': info.isEnabled(), 'installed': info.isInstalled(),
                'loaded': info.isLoaded(), 'error': info.error()}

    def status(self):
        return {'extensions': [self.record(i) for i in self.manager.extensions()],
                'pending': self.pending, 'last_result': self.last_result,
                'enable_available': False,
                'enable_blocker': 'Enabling a valid isolated extension terminated the installed Qt runtime during QA; enabling is blocked until the runtime failure is resolved.',
                'support': 'Manifest V3; compatibility depends on Qt WebEngine APIs. Chrome Web Store installation is not provided.'}

    def finished(self, operation, info):
        self.last_result = {'operation': operation, **self.record(info)}
        self.pending = None
        # Let Chromium finish its lifecycle callback before a consumer starts
        # another operation (especially uninstalling a just-installed extension).
        QTimer.singleShot(0, self.changed.emit)

    def execute(self, action, extension_id=None, path=None):
        if action == 'status': return self.status()
        if self.pending: raise ValueError('An extension operation is still pending; read status before retrying')
        if action == 'install':
            source = Path(path or '').resolve()
            if not path or not (source.is_dir() and (source/'manifest.json').is_file() or source.is_file() and source.suffix.lower()=='.zip'):
                raise ValueError('Select an unpacked extension directory containing manifest.json or a ZIP archive')
            self.pending = {'operation': 'install', 'path': str(source)}
            self.manager.installExtension(str(source))
        elif action in ('enable', 'disable', 'uninstall'):
            if action == 'enable':
                raise RuntimeError('הפעלת תוספים חסומה זמנית: מנוע Qt נסגר בבדיקת הפעלה. התקנה אינה מעידה שהתוסף פעיל.')
            info = next((i for i in self.manager.extensions() if i.id()==extension_id), None)
            if info is None: raise ValueError('Extension no longer exists; refresh the inventory')
            if not info.isInstalled(): raise ValueError('Built-in or temporary extensions are not managed here')
            if action == 'uninstall':
                self.pending = {'operation': action, 'id': extension_id}
                self.manager.uninstallExtension(info)
            else:
                self.manager.setExtensionEnabled(info, action=='enable')
                self.last_result = {'operation': action, 'id': extension_id,
                                    'verified': any(i.id()==extension_id and i.isEnabled()==(action=='enable') for i in self.manager.extensions())}
        else: raise ValueError('Unknown extension action')
        self.changed.emit()
        return self.status()

    def show(self, parent):
        dialog = QDialog(parent); dialog.setWindowTitle('תוספי הדפדפן'); dialog.resize(660, 480)
        layout = QVBoxLayout(dialog)
        note = QLabel('תוספי Manifest V3 מתיקייה או מקובץ ZIP. תוסף חדש מותקן כבוי; הפעל אותו רק לאחר בדיקת המקור וההרשאות. התאימות תלויה ביכולות מנוע הדפדפן.'); note.setWordWrap(True); layout.addWidget(note)
        buttons = QHBoxLayout(); layout.addLayout(buttons)
        status = QLabel(); status.setWordWrap(True); layout.addWidget(status)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); layout.addWidget(scroll)
        def act(action, **kwargs):
            try: self.execute(action, **kwargs)
            except Exception as exc: status.setText(str(exc))
        def select(folder):
            path = QFileDialog.getExistingDirectory(dialog, 'בחר תיקיית תוסף') if folder else QFileDialog.getOpenFileName(dialog, 'בחר תוסף ZIP', '', 'Extension archives (*.zip)')[0]
            if path: act('install', path=path)
        for title, folder in [('התקנה מתיקייה', True), ('התקנה מקובץ ZIP', False)]:
            button=QPushButton(title); button.clicked.connect(lambda checked=False, value=folder:select(value)); buttons.addWidget(button)
        def refresh():
            data=self.status(); content=QWidget(); rows=QVBoxLayout(content)
            if data['pending']: status.setText('הפעולה בביצוע; ממתין לתוצאת מנוע הדפדפן…')
            elif data['last_result']:
                result=data['last_result']; status.setText(result.get('error') or ('ההתקנה הושלמה. התוסף כבוי עד להפעלה.' if result['operation']=='install' else 'התקבלה תוצאת הפעולה; המצב המעודכן מוצג ברשימה.'))
            for item in data['extensions']:
                line=QHBoxLayout(); label=QLabel(item['name']+' · '+('פעיל' if item['enabled'] else 'כבוי')); line.addWidget(label,1)
                if item['installed']:
                    for title, action in [('כבה' if item['enabled'] else 'הפעל', 'disable' if item['enabled'] else 'enable'), ('הסר', 'uninstall')]:
                        button=QPushButton(title); button.clicked.connect(lambda checked=False, a=action, ident=item['id']:act(a, extension_id=ident)); line.addWidget(button)
                        if action=='enable':button.setEnabled(False);button.setToolTip(data['enable_blocker'])
                rows.addLayout(line)
            if not data['extensions']: rows.addWidget(QLabel('אין תוספים מותקנים.'))
            rows.addStretch(); previous=scroll.takeWidget()
            if previous: previous.deleteLater()
            scroll.setWidget(content)
        self.changed.connect(refresh)
        try: refresh(); dialog.exec()
        finally: self.changed.disconnect(refresh); dialog.deleteLater()
