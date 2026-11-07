"""Prepare native shell scripts without interpolating commands into a parent shell."""
import os,shutil,uuid
from pathlib import Path

def prepare(folder,command,shell='powershell'):
    if shell not in ('powershell','cmd'):raise ValueError('shell must be powershell or cmd')
    script=Path(folder)/('command-'+uuid.uuid4().hex+('.ps1' if shell=='powershell' else '.cmd'))
    if shell=='powershell':
        script.write_text("$ErrorActionPreference = 'Stop'\n[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()\n"+command,encoding='utf-8-sig')
        argv=[shutil.which('pwsh') or 'powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script)]
    else:
        script.write_text('@echo off\nchcp 65001 >nul\n'+command+'\n',encoding='utf-8')
        argv=[os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(script)]
    return script,argv

def preflight(command,shell='powershell'):
    import re
    if shell=='powershell' and re.search(r'(?im)^\s*(?:powershell|pwsh)(?:\.exe)?\s+.*?-(?:command|c)\s',command):
        return {'error':'Nested PowerShell -Command is not executed: outer interpolation can remove $_ and other variables. Submit the PowerShell script directly, without the powershell -Command wrapper. Use native app tools for application inspection/closure.','executed':False,'failure_kind':'shell_preflight'}
    return None


def empty_output_guard(name,args,actions):
    """Prevent a third identical silent shell execution, allowing a changed strategy."""
    if name!='run_shell':return None
    completed=[a for a in actions if a.get('state')=='complete' and (a.get('result') or {}).get('executed') is not False][-2:]
    if len(completed)!=2:return None
    for a in completed:
        r=a.get('result') or {}
        if a.get('tool')!=name or a.get('args')!=args or r.get('exit_code')!=0 or r.get('output','').strip() or r.get('error'):return None
    return {'error':'Two identical shell calls returned no output. This call was NOT executed. Inspect the explicit target with a command that reports existence and errors (for PowerShell use -LiteralPath and -ErrorAction Stop), or choose a different evidence source. Empty output does not prove absence or success.','executed':False,'failure_kind':'shell_no_progress'}
