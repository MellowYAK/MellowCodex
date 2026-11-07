"""Read the worker's Windows session; never unlock or switch secure desktops."""
import ctypes as c
from ctypes import wintypes as w
import os

def session_status():
    if os.name!='nt':return {'locked':None,'interactive':False,'reason':'Windows required'}
    class Level1(c.Structure):
        _fields_=[('session_id',w.DWORD),('state',c.c_int),('flags',w.LONG),('station',w.WCHAR*33),('user',w.WCHAR*21),('domain',w.WCHAR*18),('times',c.c_longlong*5),('counters',w.DWORD*6)]
    class Info(c.Structure):
        _fields_=[('level',w.DWORD),('data',Level1)]
    session_id=w.DWORD()
    c.windll.kernel32.ProcessIdToSessionId(os.getpid(),c.byref(session_id))
    api=c.WinDLL('wtsapi32',use_last_error=True)
    api.WTSQuerySessionInformationW.argtypes=[w.HANDLE,w.DWORD,c.c_int,c.POINTER(c.c_void_p),c.POINTER(w.DWORD)]
    api.WTSFreeMemory.argtypes=[c.c_void_p]
    ptr=c.c_void_p();size=w.DWORD()
    if not api.WTSQuerySessionInformationW(None,session_id.value,25,c.byref(ptr),c.byref(size)):
        return {'session_id':session_id.value,'locked':None,'interactive':False,'reason':'Session state unavailable'}
    try:
        if size.value<c.sizeof(Info):raise ValueError('Unexpected WTS session data size')
        info=c.cast(ptr,c.POINTER(Info)).contents
        if info.level!=1:raise ValueError('Unsupported WTS session data level')
        locked={0:True,1:False}.get(info.data.flags)
        return {'session_id':session_id.value,'connection_state':info.data.state,'locked':locked,'interactive':info.data.state==0 and locked is False}
    finally:api.WTSFreeMemory(ptr)
