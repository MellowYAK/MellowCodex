"""Application discovery and verified activation for Windows, independent of browser DOM."""
import asyncio,os,time,subprocess
from urllib.parse import urlsplit
from pathlib import Path
import psutil

def normalized(value):return ''.join(c for c in value.casefold() if c.isalnum())

def installed_apps():
    import winreg
    found={}
    for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive,r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths',0,winreg.KEY_READ|view) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        name=winreg.EnumKey(key,i)
                        try:
                            with winreg.OpenKey(key,name) as item:target=winreg.QueryValue(item,None).strip('"')
                            if Path(target).is_file():found[target.casefold()]={'name':Path(name).stem,'path':target,'executable':target}
                        except OSError:pass
            except OSError:pass
    import pythoncom,win32com.client
    pythoncom.CoInitialize()
    try:
        shell=win32com.client.Dispatch('WScript.Shell')
        for base in (os.environ.get('PROGRAMDATA',''),os.environ.get('APPDATA','')):
            menu=Path(base)/'Microsoft/Windows/Start Menu/Programs'
            for link in menu.rglob('*.lnk'):
                try:
                    target=shell.CreateShortcut(str(link)).TargetPath
                    if target and Path(target).suffix.lower()=='.exe' and Path(target).is_file():
                        found[str(link).casefold()]={'name':link.stem,'path':str(link),'executable':target}
                except Exception:pass
    finally:
        shell=None
        pythoncom.CoUninitialize()
    return list(found.values())

def matching(query,apps):
    q=normalized(Path(query).stem)
    exact=[a for a in apps if q in (normalized(a['name']),normalized(Path(a['executable']).stem))]
    return exact or [a for a in apps if q in normalized(a['name']) or q in normalized(Path(a['executable']).stem)]

class Applications:
    def __init__(self,desktop,accessibility):self.desktop=desktop;self.accessibility=accessibility
    @staticmethod
    def observed_address(inspection,url):
        requested=urlsplit(url)
        for element in inspection.get('elements',[]):
            if element.get('type')!='Edit':continue
            value=element.get('value','').strip()
            try:candidate=urlsplit(value if '://' in value else 'https://'+value)
            except ValueError:continue
            if candidate.hostname and candidate.hostname.removeprefix('www.')==requested.hostname.removeprefix('www.') and candidate.path.rstrip('/')==requested.path.rstrip('/') and candidate.query==requested.query:return value
        return None
    async def find(self,query):
        candidates=matching(query,await asyncio.to_thread(installed_apps))
        exes={Path(a['executable']).name.casefold() for a in candidates}
        inventory=self.desktop.windows()
        windows=[w for w in inventory if w.get('process','').casefold() in exes or normalized(Path(w.get('process','')).stem)==normalized(query)]
        labels={normalized(query)}|{normalized(a['name']) for a in candidates}
        unresolved=[w for w in inventory if w not in windows and any(label and label in normalized(w.get('title','')) for label in labels)]
        processes=[]
        for process in psutil.process_iter(['pid','name']):
            if (process.info.get('name') or '').casefold() in exes:processes.append(process.info)
        return {'source':'Windows application inventory','query':query,'windows':windows,'unresolved_windows':unresolved,'absence_verified':not windows and not unresolved,'process_count':len(processes),'processes':processes,'installed':candidates[:30],'note':'Running processes, visible windows, foreground windows and loaded documents are different facts. A restore-pages prompt is not evidence of unsaved document changes or a close confirmation.'}

    async def close(self,query):
        """Request normal window close. Never kill a process or dismiss save dialogs."""
        from ctypes import wintypes
        from .preferences import load_input_mode
        from .config import STATE,ARTIFACTS
        before=await self.find(query)
        executables={c['executable'].casefold() for c in before['installed']}
        if len(executables)!=1:raise ValueError('Choose one specifically identified application')
        def closable(window):
            # Explorer also owns the desktop/taskbar. Closing those can open Windows shutdown.
            if Path(window.get('executable','')).name.casefold()=='explorer.exe':
                return window.get('class_name') in ('CabinetWClass','ExploreWClass')
            return True
        before['windows']=[w for w in before['windows'] if closable(w)]
        user=self.desktop.user
        user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];user.GetAncestor.restype=wintypes.HWND
        roots={int(user.GetAncestor(wintypes.HWND(w['hwnd']),3) or w['hwnd']) for w in before['windows']}
        known={w['hwnd'] for w in before['windows']};roots&=known
        close_errors=[]
        for hwnd in roots:
            if load_input_mode(STATE)=='physical':
                self.desktop.focus(hwnd);observation=self.desktop.capture(ARTIFACTS/'window-close')
                self.desktop.act({'observation_id':observation['id'],'action':'key','key':'ALT+F4'})
            else:
                user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
                import ctypes
                native=ctypes.WinDLL('user32',use_last_error=True)
                native.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
                native.PostMessageW.restype=wintypes.BOOL
                ctypes.set_last_error(0)
                if not native.PostMessageW(hwnd,0x0010,0,0):
                    code=ctypes.get_last_error()
                    close_errors.append({'hwnd':hwnd,'winerror':code,'message':ctypes.FormatError(code),'reason':'Access denied: target may run at a higher integrity level. Requires Windows elevation; no close was delivered.' if code==5 else 'Close request rejected; inspect the remaining window.'})
        for _ in range(20):
            await asyncio.sleep(.2)
            remaining=[w for w in self.desktop.windows() if w.get('executable','').casefold() in executables and closable(w)]
            if not remaining:break
        after=await self.find(query)
        after['windows']=[w for w in after['windows'] if closable(w)]
        return {'source':'Windows normal close request','closed_verified':not after['windows'] and not after.get('unresolved_windows') and not close_errors,'unresolved_windows':after.get('unresolved_windows',[]),'close_errors':close_errors,'windows':after['windows'],'process_count':after['process_count'],'note':'No force kill and no save/discard confirmation was accepted. If a window remains, inspect its actual controls.'}
    async def open(self,query,url=None):
        from .session import session_status
        before=await self.find(query)
        if not session_status().get('interactive'):
            return {**before,'opened_verified':False,'reason':'Interactive desktop unavailable; no application launch or focus attempted.'}
        windows=before['windows']
        if url:
            parsed=urlsplit(url)
            if parsed.scheme not in ('http','https') or not parsed.hostname:raise ValueError('Use an http(s) URL')
            candidates=before['installed'];executables={c['executable'].casefold() for c in candidates}
            if len(executables)!=1 or Path(candidates[0]['executable']).name.casefold() not in ('chrome.exe','msedge.exe','firefox.exe'):
                raise ValueError('URL opening requires one specifically identified installed browser')
            for window in windows:
                try:inspection=await self.accessibility.inspect(window['hwnd'])
                except Exception:continue
                observed=self.observed_address(inspection,url)
                if observed:return {'source':'Existing Windows browser page','opened_verified':True,'reused_existing':True,'requested_url':url,'observed_url':observed,'window':{**window,'title':inspection.get('title',window['title'])},'inspection':inspection,'note':'Already open. Continue interacting with this window; do not launch another tab.'}
            subprocess.Popen([candidates[0]['executable'],url])
            inspection=None;fresh=None;observed_url=None
            for _ in range(30):
                await asyncio.sleep(.5)
                windows=[w for w in self.desktop.windows() if w.get('executable','').casefold() in executables]
                for window in windows:
                    try:inspection=await self.accessibility.inspect(window['hwnd'])
                    except Exception:continue  # A changing UI tree is not a failed launch.
                    observed_url=self.observed_address(inspection,url)
                    if observed_url:fresh={**window,'title':inspection.get('title',window['title'])}
                    if observed_url:break
                if observed_url:break
            return {'source':'Windows browser URL activation','opened_verified':bool(fresh),'requested_url':url,'observed_url':observed_url,'window':fresh,'inspection':inspection,'note':'URL verified from the target browser address control. Inspect page content separately if needed.'}
        if not windows:
            candidates=before['installed']
            executables={c['executable'].casefold() for c in candidates}
            if len(executables)!=1:return {**before,'opened_verified':False,'reason':'Application not found or ambiguous. Use a specific installed name.'}
            os.startfile(candidates[0]['path'])
            for _ in range(30):
                await asyncio.sleep(.5)
                windows=[w for w in self.desktop.windows() if w.get('executable','').casefold() in executables]
                if windows:break
        if not windows:return {**before,'opened_verified':False,'reason':'No application window appeared within 15 seconds. Do not claim it opened.'}
        if len(windows)>1:return {**before,'windows':windows,'opened_verified':False,'reason':'Multiple windows exist; choose the intended HWND, focus it and inspect it.'}
        hwnd=windows[0]['hwnd']
        self.desktop.focus(hwnd)
        fresh=next((w for w in self.desktop.windows() if w['hwnd']==hwnd),None)
        verified=bool(fresh and fresh.get('foreground') and not fresh.get('minimized'))
        return {'source':'Windows application activation','opened_verified':verified,'window':fresh,'inspection':await self.accessibility.inspect(hwnd),'note':'Inspect document/tab content before claiming completion of any further action.'}
