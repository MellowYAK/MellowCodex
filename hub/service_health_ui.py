"""Native rescue panel; no Hub web server dependency."""
import json,time,uuid
from PySide6.QtCore import QObject,QRunnable,QThreadPool,QTimer,Qt,Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QTextEdit,QComboBox,QMessageBox,QWidget
from . import service_health as health
class Events(QObject):
 done=Signal(object);failed=Signal(str)
class Work(QRunnable):
 def __init__(self,fn):super().__init__();self.fn=fn;self.events=Events()
 def run(self):
  try:self.events.done.emit(self.fn())
  except Exception as exc:self.events.failed.emit(str(exc))
class HealthPanel(QDialog):
 summary=Signal(str)
 def __init__(self,parent=None):
  super().__init__(parent);self.setWindowTitle('MellowCodex — בריאות ושירותים');self.resize(1050,700);self.setLayoutDirection(Qt.RightToLeft)
  self.setStyleSheet('QDialog {background:#f5f7fb;color:#172033} QLabel,QTableWidget,QTextEdit,QComboBox {color:#172033;background:white} QPushButton {color:#172033;background:#e6edf8;padding:8px;border:1px solid #b8c8df;border-radius:5px} QPushButton:disabled {color:#8893a5} QHeaderView::section {color:#172033;background:#e6edf8;padding:5px}')
  box=QVBoxLayout(self);self.banner=QLabel('מצב לא ידוע — טרם נבדק');self.banner.setWordWrap(True);box.addWidget(self.banner)
  line=QHBoxLayout();self.target=QComboBox()
  for title,key in [('חיבור MCP','mcp'),('כל שירותי הסוכן','all')]+[(health.LABELS[k][0],k) for k in health.LABELS]:self.target.addItem(title,key)
  line.addWidget(self.target);self.buttons=[]
  for title,action in [('בדיקה','Check'),('תיקון','Repair'),('הפעלה','Start'),('הפעלה מחדש','Restart'),('כיבוי','Stop'),('חיבור MCP מחדש','Reconnect')]:
   b=QPushButton(title);b.clicked.connect(lambda checked=False,a=action:self.act(a));line.addWidget(b);self.buttons.append(b)
  box.addLayout(line)
  global_line=QHBoxLayout()
  for title,action,service in [('בדיקת הכל','Check','all'),('תיקון הכל','Repair','all'),('הפעלה מחדש של תעבורת MCP','Restart','mcp'),('הפעלת הכל','Start','all'),('כיבוי הכל','Stop','all'),('איפוס מצב התאוששות','Reset','all')]:
   b=QPushButton(title);b.clicked.connect(lambda checked=False,a=action,k=service:self.act(a,k));global_line.addWidget(b);self.buttons.append(b)
  box.addLayout(global_line)
  power_line=QHBoxLayout();self.power_buttons=[]
  for title,action in [('כיבוי המחשב בבטחה','shutdown'),('הפעלה מחדש של המחשב בבטחה','restart')]:
   b=QPushButton(title);b.setObjectName('computer-'+action);b.clicked.connect(lambda checked=False,a=action:self.power_action(a));power_line.addWidget(b);self.power_buttons.append(b)
  b=QPushButton('הפעלה עם Windows');b.setObjectName('agent-startup-settings');b.clicked.connect(self.startup_settings);power_line.addWidget(b);self.power_buttons.append(b);box.addLayout(power_line)
  self.target.currentIndexChanged.connect(lambda _:self.enable(not self.busy) if hasattr(self,'busy') else None)
  self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['שירות','תפקיד','מצב','סיבה / פעולה מומלצת','בדיקה אחרונה','הצלחה אחרונה','פעולות']);self.table.horizontalHeader().setStretchLastSection(False);self.table.setWordWrap(True);box.addWidget(self.table)
  self.table.cellClicked.connect(self.select_service)
  explain=QLabel('סגירת חלון משאירה שירותים פעילים. כיבוי MCP משאיר Hub ומשימות פעילות. כיבוי כלל השירותים מחייב בדיקת השפעה ואישור.\nאין שינוי אוטומטי של רשת, OAuth, סודות או הרשאות.');explain.setWordWrap(True);box.addWidget(explain)
  self.toggle=QPushButton('פרטים טכניים / דוח פעולה');box.addWidget(self.toggle)
  self.detail=QTextEdit();self.detail.setReadOnly(True);self.detail.setVisible(False);box.addWidget(self.detail);self.toggle.clicked.connect(lambda:self.detail.setVisible(not self.detail.isVisible()))
  self.busy=False;self.job=None;self.data=None;self.workers=[];self.last_check=0;self.generation=0;self.rendered_at=0;self.row_buttons=[]
  self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(2000)
  self.refresh()
 def dispatch(self,fn,callback):
  task=Work(fn);self.workers.append(task);generation=self.generation
  def done(value):
   self.workers.remove(task)
   if generation==self.generation:callback(value)
  def failed(error):
   self.workers.remove(task)
   if generation!=self.generation:return
   self.busy=False;self.enable(True);self.banner.setText('בדיקה/פעולה נכשלה: '+error);self.summary.emit('⚠ בריאות: נדרשת בדיקה')
  task.events.done.connect(done);task.events.failed.connect(failed);QThreadPool.globalInstance().start(task)
 def enable(self,yes):
  for b in self.buttons+getattr(self,'power_buttons',[]):b.setEnabled(yes)
  self.target.setEnabled(yes)
  for b,service,action in getattr(self,'row_buttons',[]):
   cap=health.diagnostics.capability(service,action);b.setEnabled(yes and cap['enabled']);b.setToolTip(cap['reason'])
  if yes:
   for b,a in zip(self.buttons[:6],('Check','Repair','Start','Restart','Stop','Reconnect')):
    cap=health.diagnostics.capability(self.target.currentData(),a);b.setEnabled(cap['enabled']);b.setToolTip(cap['reason'])
 def refresh(self):
  if self.busy:return
  self.generation+=1;self.busy=True;self.enable(False);self.dispatch(health.snapshot,self.render)
 def render(self,data):
  if data['checked_at']<self.rendered_at:return
  self.rendered_at=data['checked_at'];self.data=data;self.last_check=data['checked_at'];self.busy=False
  self.row_buttons=[]
  self.table.setRowCount(len(data['services']))
  translations={'operational':'תקין','degraded':'מוגבל','unverified':'לא אומת','stale':'ראיות ישנות','intentionally_stopped':'הופסק ביוזמה','starting':'בהפעלה','failed':'נכשל','reauthentication_required':'נדרש חיבור מחדש','available':'זמין מקומית','unknown':'לא ידוע','error':'תקלה','warning':'אזהרה','stopped':'כבוי','idle':'לא טעון'}
  colors={'operational':'#13724b','intentionally_stopped':'#5d6574','failed':'#ba2525','available':'#13724b','unknown':'#876100','error':'#ba2525','warning':'#876100','stopped':'#5d6574','idle':'#5d6574'}
  for i,s in enumerate(data['services']):
   evidence='תהליך: '+str(s.get('process_exists','?'))+' | בעלות: '+str(s.get('owned','?'))+' | פורט: '+str(s.get('port_open','?'))+' | HTTP: '+str(s.get('http_status','?'))
   for j,value in enumerate((s['name'],s['description'],translations.get(s.get('status',s['state']),s['state']),s['reason']+' | '+s.get('recommended_action',''),time.strftime('%H:%M:%S',time.localtime(s['checked_at'])),time.strftime('%H:%M:%S',time.localtime(s['last_success_at'])) if s.get('last_success_at') else 'טרם אומת')):
    item=QTableWidgetItem(str(value));item.setData(Qt.UserRole,s['id']);self.table.setItem(i,j,item)
   self.table.item(i,2).setForeground(QColor(colors.get(s.get('status',s['state']),'#876100')))
   cell=QWidget();actions=QHBoxLayout(cell);actions.setContentsMargins(0,0,0,0)
   for title,action in [('פרטים','Check'),('הפעל','Start'),('עצור','Stop'),('אתחל','Restart'),('תקן','Repair')]:
    b=QPushButton(title);b.clicked.connect(lambda checked=False,k=s['id'],a=action:self.inspect(k) if a=='Check' else self.act(a,k));actions.addWidget(b);self.row_buttons.append((b,s['id'],action))
   self.table.setCellWidget(i,6,cell)
  self.enable(True)
  self.table.setColumnWidth(6,350)
  self.table.setColumnWidth(0,120);self.table.setColumnWidth(1,170);self.table.setColumnWidth(2,100);self.table.setColumnWidth(4,100)
  from PySide6.QtWidgets import QHeaderView
  self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch);self.table.resizeRowsToContents()
  connectors=data.get('connectors',{})
  text='מצב כללי: '+translations.get(data.get('overall_status'),'לא אומת')
  for name,c in connectors.items():
   text+=' | '+name+': '+translations.get(c['status'],c['status'])
  self.banner.setText(text+'\n'+data['network']['reason']);self.summary.emit(text)
  self.detail.setPlainText(json.dumps(data,ensure_ascii=False,indent=2))
 def inspect(self,service):
  row=next((r for r in (self.data or {}).get('services',[]) if r['id']==service),{})
  self.detail.setVisible(True);self.detail.setPlainText(json.dumps(row,ensure_ascii=False,indent=2))
 def select_service(self,row,column):
  item=self.table.item(row,0)
  if item:
   index=self.target.findData(item.data(Qt.UserRole))
   if index>=0:self.target.setCurrentIndex(index)
 def act(self,action,service=None):
  if self.busy:return
  service=service or self.target.currentData()
  if action=='Check' and service not in ('mcp','all','relay'):self.refresh();return
  if action=='Reset':
   scope=health.diagnostics.reset_scope(health)
   if QMessageBox.question(self,'איפוס אבחון בלבד',json.dumps(scope,ensure_ascii=False,indent=2),QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
  if action=='Reconnect':
   from PySide6.QtGui import QDesktopServices
   from PySide6.QtCore import QUrl
   name='Mellow Guard' if service in ('guard','guard_gateway') else 'MellowCodex'
   QMessageBox.information(self,'חיבור מחבר מחדש','פתח הגדרות מחברים ב־ChatGPT וחבר מחדש רק את '+name+'. לאחר האישור יש לבצע קריאת MCP אמיתית. הפעולה אינה משנה הרשאות ואינה מאשרת הסכמה במקומך.')
   QDesktopServices.openUrl(QUrl('https://chatgpt.com/#settings/Connectors'))
   return
  if service not in ('mcp','all',*health.MANAGED):
   QMessageBox.information(self,'Service control','This component uses its existing dedicated control. OwnerBroker: Owner Control (UAC). Model: Models panel. Recovery: registered recovery task. Shell: closing the window keeps services running.');return
  if action in ('Stop','Restart') and service=='all':
   tasks=(self.data or {}).get('active_tasks')
   count=str(len(tasks)) if tasks is not None else 'לא ידוע'
   if QMessageBox.question(self,'השפעה על עבודות','כיבוי כלל השירותים עשוי להפסיק '+str(count)+' משימות. האם להמשיך?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
   confirm=True
  else:confirm=False
  self.generation+=1;self.busy=True;self.enable(False);self.banner.setText('הפעולה נשלחת למבצע מקומי מתמשך…')
  self.dispatch(lambda:health.submit(action,service,uuid.uuid4().hex,confirm),self.accepted)
 def power_action(self,action):
  if self.busy:return
  from . import power
  self.generation+=1;self.busy=True;self.enable(False)
  def confirm(data):
   self.detail.setPlainText(json.dumps(data,ensure_ascii=False,indent=2));self.detail.setVisible(True)
   if data.get('blocker'):
    self.banner.setText(data['blocker']);self.busy=False;self.enable(True);return
   count='לא ידוע' if data['active_tasks'] is None else str(len(data['active_tasks']))
   title='כיבוי המחשב' if action=='shutdown' else 'הפעלה מחדש של המחשב'
   if QMessageBox.question(self,title,'משימות פעילות: '+count+'\nEmber, הסוכן, Ollama, MCP ו־SSH ייעצרו בבטחה לפני Windows. עבודה שלא ניתן לעצור תחסום את הפעולה. יישומים אחרים לא ייסגרו בכוח. להמשיך?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:
    self.busy=False;self.enable(True);return
   self.dispatch(lambda:power.submit(action,uuid.uuid4().hex,True),self.accepted)
  self.dispatch(lambda:power.preview(action),confirm)
 def startup_settings(self):
  if self.busy:return
  from . import power
  self.generation+=1;self.busy=True;self.enable(False)
  def choose(data):
   self.detail.setPlainText(json.dumps(data,ensure_ascii=False,indent=2));self.detail.setVisible(True)
   dialog=QMessageBox(self);dialog.setWindowTitle('הפעלה עם Windows');dialog.setText('הגדרה: '+str(data['start_with_windows'])+' | אומת ב־Windows: '+str(data['effective'])+'\nמפעיל את שירותי הסוכן בכניסה לחשבון. אינו מפעיל מודלי תמונה של Ember ואינו מכבה שירותים פעילים.')
   on=dialog.addButton('הפעל עם Windows',QMessageBox.AcceptRole);off=dialog.addButton('אל תפעיל עם Windows',QMessageBox.DestructiveRole);dialog.addButton(QMessageBox.Cancel);dialog.exec()
   chosen=dialog.clickedButton()
   if chosen not in (on,off):self.busy=False;self.enable(True);return
   def saved(value):
    self.detail.setPlainText(json.dumps(value,ensure_ascii=False,indent=2));self.banner.setText('הגדרת הפעלה נשמרה; מצב Windows: '+str(value['effective']));self.busy=False;self.enable(True)
   self.dispatch(lambda:power.set_startup(chosen==on,data['revision']),saved)
  self.dispatch(power.startup_status,choose)
 def accepted(self,result):
  self.job=result['id'];self.banner.setText('פעולה '+self.job+' — '+result['state']);self.detail.setPlainText(json.dumps(result,ensure_ascii=False,indent=2));self.detail.setVisible(True)
 def tick(self):
  if self.job and not self.workers:self.dispatch(lambda:health.job_status(self.job),self.progress)
  elif not self.busy and time.time()-self.last_check>30:self.refresh()
  if self.last_check and time.time()-self.last_check>60:
   self.summary.emit('⚠ נתוני בריאות ישנים — יש לרענן');self.banner.setToolTip('גיל הראיות: '+str(int(time.time()-self.last_check))+' שניות')
 def progress(self,result):
  self.banner.setText('פעולה '+result['id']+' — '+result['state']+'\n'+result.get('reason',''));self.detail.setPlainText(json.dumps(result,ensure_ascii=False,indent=2))
  if result['state'] not in ('queued','running'):
   self.job=None;self.busy=False;self.enable(True)
   if result.get('result'):
    self.render(result['result'])
    self.banner.setText(result['id']+' / '+result['state']+'\n'+self.banner.text())
    self.detail.setPlainText(json.dumps(result,ensure_ascii=False,indent=2))
 def open(self):
  self.show();self.raise_();self.activateWindow();self.refresh()
def main():
 import sys
 from PySide6.QtWidgets import QApplication
 app=QApplication.instance() or QApplication(sys.argv)
 panel=HealthPanel();panel.show()
 sys.exit(app.exec())

def install(window,toolbar,tray_menu,open_owner):
 panel=HealthPanel(window)
 indicator=toolbar.addAction('בריאות: בודק…');indicator.triggered.connect(panel.open);panel.summary.connect(indicator.setText)
 tools=window.menuBar().addMenu('כלים');tools.addAction('בריאות ושירותים',panel.open)
 status=tray_menu.addAction('בריאות: בודק…');status.setEnabled(False);panel.summary.connect(status.setText)
 tray_menu.addAction('בריאות ושירותים',panel.open)
 for title,action in [('בדיקה מחדש','Check'),('חיבור מחדש ל־MCP','Reconnect'),('תיקון','Repair'),('הפעלת MCP','Start'),('הפעלה מחדש של MCP','Restart'),('כיבוי MCP','Stop')]:
  tray_menu.addAction(title,lambda checked=False,a=action:panel.act(a,'mcp'))
 for menu in (tools,tray_menu):
  menu.addAction('כיבוי המחשב בבטחה',lambda:panel.power_action('shutdown'))
  menu.addAction('הפעלה מחדש של המחשב בבטחה',lambda:panel.power_action('restart'))
  menu.addAction('הפעלה עם Windows',panel.startup_settings)
 tray_menu.addAction('הרשאות בעלים (UAC)',open_owner)
 return panel

if __name__=='__main__':main()
