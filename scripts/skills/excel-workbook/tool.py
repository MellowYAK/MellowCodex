import json,sys,pathlib,os
def absolute(value):
 p=pathlib.Path(value)
 if not p.is_absolute(): raise ValueError('Absolute path required')
 return p.resolve()
def output(value):
 p=absolute(value)
 if p.exists(): raise FileExistsError(str(p))
 if not p.parent.is_dir(): raise ValueError('Parent directory must exist')
 return p
from openpyxl import Workbook,load_workbook
def main(a):
 op=a['operation']
 if op=='create':
  dst=output(a['destination']);w=Workbook();s=w.active;s.title=a.get('sheet','Sheet1')
  for row in a.get('rows',[]): s.append(row)
  w.save(dst);w.close();return {'created':str(dst)}
 w=load_workbook(absolute(a['source']),read_only=op=='read',data_only=False)
 try:
  s=w[a['sheet']] if a.get('sheet') else w.active
  if op=='read':
   limit=a.get('limit',100)
   if type(limit)!=int or not 1<=limit<=1000: raise ValueError('limit1..1000')
   return {'sheet':s.title,'rows':list(s.iter_rows(min_row=1,max_row=min(limit,s.max_row),values_only=True)),'sheets':w.sheetnames}
  if op=='edit':
   dst=output(a['destination'])
   for cell,value in a['cells'].items(): s[cell]=value
   w.save(dst);return {'saved':str(dst)}
  raise ValueError('operation create|read|edit')
 finally: w.close()

if __name__=='__main__':
 try: print(json.dumps(main(json.load(sys.stdin)),ensure_ascii=False,default=str))
 except Exception as e: print(json.dumps({'error':str(e)}));sys.exit(1)
