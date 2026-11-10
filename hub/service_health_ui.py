"""Native rescue panel; no Hub web server dependency."""
import json,time,uuid
from PySide6.QtCore import QObject,QRunnable,QThreadPool,QTimer,Qt,Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QTextEdit,QComboBox,QMessageBox
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
  self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['שירות','תפקיד','מצב','סיבה','בדיקה אחרונה','ראיות']);self.table.horizontalHeader().setStretchLastSection(False);self.table.setWordWrap(True);box.addWidget(self.table)
  self.table.cellClicked.connect(self.select_service)
  explain=QLabel('סגירת חלון משאירה שירותים פעילים. כיבוי MCP משאיר Hub ומשימות פעילות. כיבוי כלל השירותים מחייב בדיקת השפעה ואישור.\nאין שינוי אוטומטי של רשת, OAuth, סודות או הרשאות.');explain.setWordWrap(True);box.addWidget(explain)
  self.toggle=QPushButton('פרטים טכניים / דוח פעולה');box.addWidget(self.toggle)
  self.detail=QTextEdit();self.detail.setReadOnly(True);self.detail.setVisible(False);box.addWidget(self.detail);self.toggle.clicked.connect(lambda:self.detail.setVisible(not self.detail.isVisible()))
  self.busy=False;self.job=None;self.data=None;self.workers=[];self.last_check=0
  self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(2000)
  self.refresh()
 def dispatch(self,fn,callback):
  task=Work(fn);self.workers.append(task)
  def done(value):
   self.workers.remove(task);callback(value)
  def failed(error):
   self.workers.remove(task);self.busy=False;self.enable(True);self.banner.setText('בדיקה/פעולה נכשלה: '+error);self.summary.emit('⚠ בריאות: נדרשת בדיקה')
  task.events.done.connect(done);task.events.failed.connect(failed);QThreadPool.globalInstance().start(task)
 def enable(self,yes):
  for b in self.buttons:b.setEnabled(yes)
  self.target.setEnabled(yes)
 def refresh(self):
  if self.busy:return
  self.busy=True;self.enable(False);self.dispatch(health.snapshot,self.render)
 def render(self,data):
  self.data=data;self.last_check=time.time();self.busy=False;self.enable(True)
  self.table.setRowCount(len(data['services']))
  translations={'available':'זמין מקומית','unknown':'לא ידוע','error':'תקלה','warning':'אזהרה','stopped':'כבוי','idle':'לא טעון'}
  colors={'available':'#13724b','unknown':'#876100','error':'#ba2525','warning':'#876100','stopped':'#5d6574','idle':'#5d6574'}
  for i,s in enumerate(data['services']):
   evidence='תהליך: '+str(s.get('process_exists','?'))+' | בעלות: '+str(s.get('owned','?'))+' | פורט: '+str(s.get('port_open','?'))+' | HTTP: '+str(s.get('http_status','?'))
   for j,value in enumerate((s['name'],s['description'],translations.get(s['state'],s['state']),s['reason'],time.strftime('%H:%M:%S',time.localtime(s['checked_at'])))):
    item=QTableWidgetItem(str(value));item.setData(Qt.UserRole,s['id']);self.table.setItem(i,j,item)
   self.table.item(i,2).setForeground(QColor(colors.get(s['state'],'#876100')))
  self.table.setColumnWidth(0,160);self.table.setColumnWidth(1,170);self.table.setColumnWidth(2,100);self.table.setColumnWidth(4,100)
  from PySide6.QtWidgets import QHeaderView
  self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch);self.table.resizeRowsToContents()
  issues=sum(s['state'] in ('error','unknown','warning') for s in data['services'])
  text=('⏸ MCP כבוי ביוזמה' if data['manual_stop'] else '⚠ '+str(issues)+' רכיבים דורשים בדיקה' if issues else '● שירותים מקומיים זמינים')
  text+=' | MCP מרחוק: '+{'unknown':'לא אומת','stale':'אימות ישן','verified':'אומת כעת'}.get(data['remote']['state'],'לא ידוע')
  self.banner.setText(text+'\n'+data['network']['reason']);self.summary.emit(text)
  self.detail.setPlainText(json.dumps(data,ensure_ascii=False,indent=2))
 def select_service(self,row,column):
  item=self.table.item(row,0)
  if item:
   index=self.target.findData(item.data(Qt.UserRole))
   if index>=0:self.target.setCurrentIndex(index)
 def act(self,action,service=None):
  if self.busy:return
  service=service or self.target.currentData()
  if action=='Check':self.refresh();return
  if service not in ('mcp','all',*health.MANAGED):
   QMessageBox.information(self,'Service control','This component uses its existing dedicated control. OwnerBroker: Owner Control (UAC). Model: Models panel. Recovery: registered recovery task. Shell: closing the window keeps services running.');return
  if action in ('Stop','Restart') and service=='all':
   tasks=(self.data or {}).get('active_tasks')
   count=str(len(tasks)) if tasks is not None else 'לא ידוע'
   if QMessageBox.question(self,'השפעה על עבודות','כיבוי כלל השירותים עשוי להפסיק '+str(count)+' משימות. האם להמשיך?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
   confirm=True
  else:confirm=False
  self.busy=True;self.enable(False);self.banner.setText('הפעולה נשלחת למבצע מקומי מתמשך…')
  self.dispatch(lambda:health.submit(action,service,uuid.uuid4().hex,confirm),self.accepted)
 def accepted(self,result):
  self.job=result['id'];self.banner.setText('פעולה '+self.job+' — '+result['state']);self.detail.setPlainText(json.dumps(result,ensure_ascii=False,indent=2))
 def tick(self):
  if self.job and not self.workers:self.dispatch(lambda:health.job_status(self.job),self.progress)
  elif not self.busy and time.time()-self.last_check>30:self.refresh()
  if self.last_check and time.time()-self.last_check>60:self.summary.emit('⚠ נתוני בריאות ישנים')
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
 tray_menu.addAction('הרשאות בעלים (UAC)',open_owner)
 return panel

if __name__=='__main__':main()
