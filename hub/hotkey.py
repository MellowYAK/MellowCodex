"""Independent Ctrl+Alt+F12 emergency stop. Does not depend on model responsiveness."""
import ctypes
from ctypes import wintypes
import os
import threading

class EmergencyHotkey:
    def __init__(self,callback):
        self.callback=callback
        self.thread_id=None
        self.registered=False
        self.ready=threading.Event()

    def start(self):
        if os.name!='nt':
            return
        self.thread=threading.Thread(target=self._listen,daemon=True,name='emergency-hotkey')
        self.thread.start()
        self.ready.wait(2)

    def _listen(self):
        user=ctypes.windll.user32
        self.thread_id=ctypes.windll.kernel32.GetCurrentThreadId()
        self.registered=bool(user.RegisterHotKey(None,1,0x4000|0x0002|0x0001,0x7B))
        self.ready.set()
        if not self.registered:
            return
        message=wintypes.MSG()
        try:
            while user.GetMessageW(ctypes.byref(message),None,0,0)>0:
                if message.message==0x0312:
                    self.callback()
        finally:
            user.UnregisterHotKey(None,1)
            self.registered=False

    def close(self):
        if self.thread_id and self.registered:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id,0x0012,0,0)
