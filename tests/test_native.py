import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from hub.desktop_app import Window,prepare_fonts
import hub.desktop_app as native
import time

def test_native_submit_payload_and_review_controls():
    app=QApplication.instance() or QApplication([])
    prepare_fonts(app)
    window=Window(live=False)
    window.show()
    app.processEvents()
    requests=[]
    window.request=lambda method,path,body,callback,error_callback=None:requests.append((method,path,body))
    window.goal.setPlainText('צור קובץ בדיקה')
    window.check_path.setText('proof.txt')
    window.check_contains.setText('שלום')
    QTest.mouseClick(window.submit,Qt.LeftButton)
    method,path,body=requests[-1]
    assert method=='POST' and path=='/tasks'
    assert body['goal']=='צור קובץ בדיקה'
    assert body['mode']=='desktop'
    assert body['criteria']==[{'path':'proof.txt','contains':'שלום'}]
    task={'id':'test','goal':'Test','workspace':'E:/AI/repos/sandbox','revision':3,'state':'waiting_review'}
    window.stack.setCurrentIndex(1)
    window.update_task(task)
    assert window.review.isVisible()
    assert not window.control_buttons['resume'].isEnabled()
    assert window.control_buttons['cancel'].isEnabled()
    window.close()

def test_async_result_reaches_main_window(monkeypatch):
    app=QApplication.instance() or QApplication([])
    window=Window(live=False)
    window.live=True
    monkeypatch.setattr(native.Request,'run',lambda work:work.signals.result.emit({'ok':True}))
    received=[]
    window.request('GET','/probe',None,received.append)
    deadline=time.monotonic()+3
    while not received and time.monotonic()<deadline:
        app.processEvents()
        QTest.qWait(10)
    assert received==[{'ok':True}]
    assert not window.pending_requests
    window.close()
