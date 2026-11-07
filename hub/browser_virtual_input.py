"""Qt WebEngine widget-local events. Never moves the Windows cursor."""
import math
from PySide6.QtCore import QEvent,QPointF,QTimer,Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication


def drag(view,args,done):
    if view.url().toString()!=args['expected_url']:raise ValueError('Target URL changed')
    values=[float(args[k]) for k in ('x','y','end_x','end_y')]
    if not all(math.isfinite(v) for v in values):raise ValueError('Invalid pointer coordinates')
    x,y,ex,ey=values
    if not all(0<=px<view.width() and 0<=py<view.height() for px,py in [(x,y),(ex,ey)]):raise ValueError('Pointer outside viewport')
    button={'left':Qt.LeftButton,'right':Qt.RightButton,'middle':Qt.MiddleButton}[args['button']]
    receiver=view.focusProxy()
    if receiver is None:raise ValueError('Browser input surface is unavailable')
    events=[(QEvent.MouseMove,x,y,Qt.NoButton,Qt.NoButton),(QEvent.MouseButtonPress,x,y,button,button)]
    events.extend((QEvent.MouseMove,x+(ex-x)*i/12,y+(ey-y)*i/12,Qt.NoButton,button) for i in range(1,13))
    events.append((QEvent.MouseButtonRelease,ex,ey,button,Qt.NoButton))
    completed=False
    def send(event,last=False):
        nonlocal completed
        if completed:return
        try:
            kind,px,py,changed,held=event
            pos=QPointF(px,py)
            QApplication.sendEvent(receiver,QMouseEvent(kind,pos,pos,changed,held,Qt.NoModifier))
            if last:
                completed=True;done({'input_sent':True,'backend':'qt-widget-events','physical_pointer_used':False})
        except Exception as exc:
            completed=True
            try:QApplication.sendEvent(receiver,QMouseEvent(QEvent.MouseButtonRelease,QPointF(ex,ey),QPointF(ex,ey),button,Qt.NoButton,Qt.NoModifier))
            except RuntimeError:pass
            done({'error':type(exc).__name__+': '+str(exc),'outcome':'uncertain'})
    # Schedule release before dispatching press: Chromium may enter a nested
    # native drag loop while a move is delivered. A chained timer would never
    # reach release in that case.
    for index,event in enumerate(events):
        QTimer.singleShot(index*20,lambda event=event,last=index==len(events)-1:send(event,last))
