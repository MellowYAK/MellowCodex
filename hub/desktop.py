"""Windows input driver. Coordinates refer to native virtual-desktop pixels.

Every mutation requires a recent screenshot and the same foreground HWND.
Unicode text uses SendInput without overwriting the clipboard.
"""
import ctypes
from ctypes import wintypes
import os
import time
import uuid
from .session import session_status
from pathlib import Path
from .errors import ObservationError

class Desktop:
    def __init__(self):
        self.observation = None
        self.stopped = False
        if os.name == 'nt':
            self.user = ctypes.WinDLL('user32', use_last_error=True)
            self.user.GetForegroundWindow.restype = wintypes.HWND
            self.user.SetForegroundWindow.argtypes = [wintypes.HWND]
            self.user.IsWindow.argtypes = [wintypes.HWND]
            self.user.IsWindowVisible.argtypes = [wintypes.HWND]
            self.user.GetWindowTextW.argtypes = [wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
            self.user.ShowWindow.argtypes = [wintypes.HWND,ctypes.c_int]
            try:
                self.user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            except Exception:
                pass

    def windows(self):
        output = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        def collect(hwnd, _):
            if self.user.IsWindowVisible(hwnd):
                title = ctypes.create_unicode_buffer(1024)
                self.user.GetWindowTextW(hwnd,title,1024)
                if title.value:
                    import psutil
                    pid=wintypes.DWORD()
                    self.user.GetWindowThreadProcessId(wintypes.HWND(hwnd),ctypes.byref(pid))
                    name='';exe=''
                    try:name=psutil.Process(pid.value).name()
                    except (psutil.Error,OSError):pass
                    try:exe=psutil.Process(pid.value).exe()
                    except (psutil.Error,OSError):pass
                    window_class=ctypes.create_unicode_buffer(256)
                    self.user.GetClassNameW(hwnd,window_class,256)
                    output.append({'hwnd':hwnd,'title':title.value,'class_name':window_class.value,'pid':pid.value,'process':name,'executable':exe,'foreground':int(self.user.GetForegroundWindow() or 0)==hwnd,'minimized':bool(self.user.IsIconic(wintypes.HWND(hwnd)))})
            return True
        self.user.EnumWindows(callback_type(collect),0)
        return output

    def capture(self, folder: Path):
        import mss
        import mss.tools
        folder.mkdir(parents=True,exist_ok=True)
        token = uuid.uuid4().hex
        path = folder / (token+'.png')
        try:
            with mss.MSS() as screen:
                monitor = dict(screen.monitors[0])
                frame = screen.grab(monitor)
                mss.tools.to_png(frame.rgb,frame.size,output=str(path))
            backend='desktop-gdi'
        except Exception as screen_error:
            try:
                monitor=self._capture_window(path)
                backend='foreground-window-printwindow'
            except Exception as window_error:
                raise RuntimeError('Desktop capture unavailable in this Windows session. Desktop GDI and foreground-window capture both failed. Keep the desktop unlocked and active. '+str(window_error)) from screen_error
        self.observation = {'id':token,'path':str(path),'captured':time.monotonic(),'hwnd':int(self.user.GetForegroundWindow() or 0),**monitor}
        self.observation['backend']=backend
        return {k:v for k,v in self.observation.items() if k != 'captured'}

    def capture_target(self,hwnd,folder):
        """Capture the identified application window, including when not foreground."""
        folder.mkdir(parents=True,exist_ok=True);token=uuid.uuid4().hex;path=folder/(token+'.png')
        foreground_hwnd=int(self.user.GetForegroundWindow() or 0)
        foreground=foreground_hwnd==hwnd or self._owned_by(foreground_hwnd,hwnd)
        interactive = session_status().get('interactive', False)
        screen_error = None
        if foreground and interactive:
            # GPU-rendered browsers can return a white content surface from
            # PrintWindow even though their toolbar is captured correctly.
            import mss,mss.tools,win32gui
            left,top,right,bottom=win32gui.GetWindowRect(hwnd)
            monitor={'left':left,'top':top,'width':right-left,'height':bottom-top}
            try:
                with mss.MSS() as screen:
                    frame=screen.grab(monitor);mss.tools.to_png(frame.rgb,frame.size,output=str(path))
                backend='foreground-window-screen-crop'
            except Exception as exc:
                screen_error = str(exc)
                monitor=self._capture_window(path,hwnd);backend='target-window-printwindow'
        else:
            monitor=self._capture_window(path,hwnd);backend='target-window-printwindow'
        result={'id':token,'path':str(path),'hwnd':hwnd,'foreground_hwnd':foreground_hwnd,**monitor,'backend':backend,'source':'Identified Windows application window','input_ready':False}
        # A background image is evidence only. Physical input requires this exact
        # target still foreground, and a new foreground check in guard().
        if screen_error:result['screen_capture_error']=screen_error
        if foreground and interactive and backend=='foreground-window-screen-crop' and getattr(self,'target_hwnd',None)==hwnd:
            result['input_ready']=True
            self.observation={**result,'captured':time.monotonic()}
        return result

    def _capture_window(self,path,target_hwnd=None):
        import win32gui,win32ui
        from PIL import Image,ImageStat
        hwnd=target_hwnd or int(self.user.GetForegroundWindow() or 0)
        if not hwnd:raise RuntimeError('No foreground window')
        left,top,right,bottom=win32gui.GetWindowRect(hwnd)
        width,height=right-left,bottom-top
        if width<=0 or height<=0 or width*height>40_000_000:raise RuntimeError('Invalid foreground window dimensions')
        handle=win32gui.GetWindowDC(hwnd)
        source=win32ui.CreateDCFromHandle(handle);memory=source.CreateCompatibleDC();bitmap=win32ui.CreateBitmap()
        try:
            bitmap.CreateCompatibleBitmap(source,width,height);memory.SelectObject(bitmap)
            self.user.PrintWindow.argtypes=[wintypes.HWND,wintypes.HDC,wintypes.UINT]
            if not self.user.PrintWindow(hwnd,memory.GetSafeHdc(),2):raise RuntimeError('Window rejected capture')
            picture=Image.frombuffer('RGB',(width,height),bitmap.GetBitmapBits(True),'raw','BGRX',0,1)
            if max(ImageStat.Stat(picture).stddev)<0.5:raise RuntimeError('Window returned an empty capture')
            picture.save(path)
        finally:
            win32gui.DeleteObject(bitmap.GetHandle());memory.DeleteDC();source.DeleteDC();win32gui.ReleaseDC(hwnd,handle)
        return {'left':left,'top':top,'width':width,'height':height}

    def guard(self, observation_id):
        if self.stopped:
            raise RuntimeError('Emergency stop is active')
        obs = self.observation
        if not obs or obs['id'] != observation_id or time.monotonic()-obs['captured'] > 45:
            raise ObservationError('Screenshot expired. Observe the desktop again.')
        if obs.get('foreground_hwnd',obs['hwnd']) != int(self.user.GetForegroundWindow() or 0):
            raise ObservationError('Foreground changed. Observe again before input.')
        target=getattr(self,'target_hwnd',obs['hwnd'])
        if target!=obs['hwnd'] and not self._owned_by(obs['hwnd'],target):
            raise ObservationError('The requested target window is no longer foreground. Focus it before sending input.')
        point = wintypes.POINT()
        self.user.GetCursorPos(ctypes.byref(point))
        if point.x <= obs['left']+2 and point.y <= obs['top']+2:
            raise RuntimeError('Mouse corner fail-safe: move the pointer away from the upper-left corner')
        self.observation = None
        return obs

    def _owned_by(self,hwnd,target):
        if not hwnd or not target:return False
        self.user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];self.user.GetAncestor.restype=wintypes.HWND
        owner=int(self.user.GetAncestor(wintypes.HWND(hwnd),3) or 0)
        if owner!=target:return False
        first=wintypes.DWORD();second=wintypes.DWORD()
        self.user.GetWindowThreadProcessId(wintypes.HWND(hwnd),ctypes.byref(first))
        self.user.GetWindowThreadProcessId(wintypes.HWND(target),ctypes.byref(second))
        return bool(first.value and first.value==second.value)

    def _send(self, kind, *, dx=0,dy=0,data=0,flags=0,vk=0,scan=0):
        ULONG_PTR = ctypes.c_size_t
        class Mouse(ctypes.Structure):
            _fields_=[('dx',wintypes.LONG),('dy',wintypes.LONG),('mouseData',wintypes.DWORD),('dwFlags',wintypes.DWORD),('time',wintypes.DWORD),('dwExtraInfo',ULONG_PTR)]
        class Keyboard(ctypes.Structure):
            _fields_=[('wVk',wintypes.WORD),('wScan',wintypes.WORD),('dwFlags',wintypes.DWORD),('time',wintypes.DWORD),('dwExtraInfo',ULONG_PTR)]
        class Union(ctypes.Union):
            _fields_=[('mi',Mouse),('ki',Keyboard)]
        class Input(ctypes.Structure):
            _fields_=[('type',wintypes.DWORD),('u',Union)]
        event=Input(type=kind)
        if kind == 0:
            event.u.mi=Mouse(dx,dy,data & 0xffffffff,flags,0,0)
        else:
            event.u.ki=Keyboard(vk,scan,flags,0,0)
        if self.user.SendInput(1,ctypes.byref(event),ctypes.sizeof(event)) != 1:
            raise OSError('Windows rejected input (possibly an elevated or secure window)')

    def act(self, args):
        obs = self.guard(args['observation_id'])
        action = args['action']
        if action in ('move','click','drag'):
            x,y=int(args['x']),int(args['y'])
            if not (obs['left'] <= x < obs['left']+obs['width'] and obs['top'] <= y < obs['top']+obs['height']):
                raise ObservationError('Coordinates outside observed desktop; no input sent')
            self._validate_target_point(x,y)
            self.user.SetCursorPos(x,y)
        if action == 'click':
            down,up=(0x0002,0x0004) if args.get('button','left') == 'left' else (0x0008,0x0010)
            for _ in range(min(2,max(1,int(args.get('clicks',1))))):
                self._send(0,flags=down)
                self._send(0,flags=up)
                time.sleep(.07)
        elif action == 'drag':
            end_x,end_y=int(args['end_x']),int(args['end_y'])
            if not (obs['left'] <= end_x < obs['left']+obs['width'] and obs['top'] <= end_y < obs['top']+obs['height']):
                raise ObservationError('Drag target outside desktop; no input sent')
            self._validate_target_point(end_x,end_y)
            self._send(0,flags=2)
            try:
                for i in range(1,21):
                    if self.stopped:
                        break
                    self.user.SetCursorPos(round(x+(end_x-x)*i/20),round(y+(end_y-y)*i/20))
                    time.sleep(.025)
            finally:
                self._send(0,flags=4)
        elif action == 'scroll':
            point=wintypes.POINT();self.user.GetCursorPos(ctypes.byref(point));self._validate_target_point(point.x,point.y)
            self._send(0,data=max(-10,min(10,int(args.get('amount',1))))*120,flags=0x800)
        elif action == 'type':
            raw=args.get('text','')[:4000].replace('\r\n','\n').replace('\r','\n').encode('utf-16-le')
            for i in range(0,len(raw),2):
                if self.stopped:
                    break
                unit=int.from_bytes(raw[i:i+2],'little')
                if unit in (10,9):
                    self._send(1,vk=13 if unit==10 else 9)
                    self._send(1,vk=13 if unit==10 else 9,flags=2)
                else:
                    self._send(1,scan=unit,flags=4)
                    self._send(1,scan=unit,flags=6)
                # Modern text controls consume Unicode packets asynchronously.
                # Do not flood them; keep UTF-16 surrogate pairs together.
                if not 0xD800<=unit<=0xDBFF:time.sleep(.012)
        elif action == 'key':
            keys={'CTRL':17,'ALT':18,'SHIFT':16,'ENTER':13,'ESC':27,'TAB':9,'SPACE':32,'BACKSPACE':8,'DELETE':46,'LEFT':37,'UP':38,'RIGHT':39,'DOWN':40,'HOME':36,'END':35,'PAGEUP':33,'PAGEDOWN':34}
            keys.update({chr(n):n for n in range(48,91)})
            keys.update({f'F{n}':111+n for n in range(1,13)})
            parts=args['key'].upper().split('+')
            codes=[keys[p] for p in parts]
            held=[]
            try:
                for code in codes:
                    self._send(1,vk=code)
                    held.append(code)
                time.sleep(min(2,max(.02,float(args.get('hold',.03)))))
            finally:
                for code in reversed(held):
                    self._send(1,vk=code,flags=2)
        elif action != 'move':
            raise ValueError('Unknown desktop action')
        return {'input_sent':True,'verification_required':True}

    def _validate_target_point(self,x,y):
        if not getattr(self,'target_hwnd',None):return
        self.user.WindowFromPoint.argtypes=[wintypes.POINT];self.user.WindowFromPoint.restype=wintypes.HWND
        self.user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];self.user.GetAncestor.restype=wintypes.HWND
        hit=self.user.WindowFromPoint(wintypes.POINT(x,y))
        root=self.user.GetAncestor(hit,2) if hit else None
        owner=self.user.GetAncestor(hit,3) if hit else None
        target_pid=wintypes.DWORD();hit_pid=wintypes.DWORD()
        self.user.GetWindowThreadProcessId(wintypes.HWND(self.target_hwnd),ctypes.byref(target_pid))
        if hit:self.user.GetWindowThreadProcessId(hit,ctypes.byref(hit_pid))
        owned_popup=int(owner or 0)==self.target_hwnd and target_pid.value==hit_pid.value
        if int(root or 0)!=self.target_hwnd and not owned_popup:
            raise ObservationError('The point is outside the selected window or covered by another window. Observe and focus the target again.')

    def focus(self, hwnd):
        if self.stopped:
            raise RuntimeError('Emergency stop is active')
        if hwnd not in {w['hwnd'] for w in self.windows()}:
            raise ValueError('Window no longer exists')
        self.user.ShowWindow(wintypes.HWND(hwnd),9)
        self.user.ShowWindow(wintypes.HWND(hwnd),5)
        self.user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        current=ctypes.windll.kernel32.GetCurrentThreadId()
        foreground=self.user.GetForegroundWindow()
        target_thread=self.user.GetWindowThreadProcessId(wintypes.HWND(hwnd),None)
        foreground_thread=self.user.GetWindowThreadProcessId(foreground,None) if foreground else 0
        attached=[]
        message=wintypes.MSG();self.user.PeekMessageW(ctypes.byref(message),None,0,0,0)
        try:
            for other in {target_thread,foreground_thread}-{0,current}:
                if self.user.AttachThreadInput(current,other,True):attached.append(other)
            self.user.SetForegroundWindow(wintypes.HWND(hwnd))
            self.user.BringWindowToTop(wintypes.HWND(hwnd))
        finally:
            for other in attached:self.user.AttachThreadInput(current,other,False)
        self.observation=None
        actual=int(self.user.GetForegroundWindow() or 0)
        if actual!=hwnd:
            raise RuntimeError('Windows did not focus the requested window. Click that window once, then resume. No input was sent.')
        self.target_hwnd=hwnd
        return {'foreground':actual}
