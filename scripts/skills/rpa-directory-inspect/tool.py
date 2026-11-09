import json,sys,pathlib,os
from RPA.FileSystem import FileSystem
def main(a):
 if not isinstance(a,dict) or set(a)-{'path','limit'}: raise ValueError('Expected path and optional limit')
 p=pathlib.Path(a.get('path',''));limit=a.get('limit',50)
 if not p.is_absolute() or not p.is_dir(): raise ValueError('Existing absolute directory required')
 if type(limit) is not int or not 1<=limit<=200: raise ValueError('limit must be 1..200')
 os.chdir(p)
 files=FileSystem().list_files_in_directory(pathlib.Path('.'))
 return {'files':[{'path':str(f.path),'name':f.name,'size':f.size} for f in files[:limit]],'truncated':len(files)>limit}
if __name__=='__main__':
 try: print(json.dumps(main(json.load(sys.stdin)),ensure_ascii=False))
 except Exception as e: print(json.dumps({'error':str(e)}));sys.exit(1)
