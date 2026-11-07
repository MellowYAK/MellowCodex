"""Verified per-user Windows shortcuts, independent of the planning model."""
import os
from pathlib import Path

def shortcut(action, name, target=None, arguments='', working_directory=''):
    if not name or any(c in name for c in '<>:"/\\|?*') or name.endswith((' ','.')):
        raise ValueError('Invalid shortcut name')
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        shell=win32com.client.Dispatch('WScript.Shell')
        desktop=Path(shell.SpecialFolders('Desktop'))
        path=desktop/(name if name.lower().endswith('.lnk') else name+'.lnk')
        if action=='create':
            if not target or not Path(target).is_file():raise ValueError('Shortcut target must be an existing file')
            if working_directory and not Path(working_directory).is_dir():raise ValueError('Working directory does not exist')
            if path.exists():
                old=shell.CreateShortcut(str(path))
                if os.path.normcase(old.TargetPath)!=os.path.normcase(str(Path(target).resolve())) or old.Arguments!=arguments:
                    raise ValueError('A different shortcut exists; will not overwrite it')
            link=shell.CreateShortcut(str(path))
            link.TargetPath=str(Path(target).resolve())
            link.Arguments=arguments
            link.WorkingDirectory=working_directory or str(Path(target).parent)
            link.Save()
        elif action!='inspect':raise ValueError('Unknown shortcut action')
        if not path.exists():return {'exists':False,'path':str(path),'verified':False}
        link=shell.CreateShortcut(str(path))
        verified=Path(link.TargetPath).is_file()
        if action=='create':verified=verified and os.path.normcase(link.TargetPath)==os.path.normcase(str(Path(target).resolve())) and link.Arguments==arguments
        return {'exists':True,'path':str(path),'target':link.TargetPath,'arguments':link.Arguments,'working_directory':link.WorkingDirectory,'verified':verified}
    finally:pythoncom.CoUninitialize()
