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
from pypdf import PdfReader,PdfWriter
def main(a):
 op=a['operation']
 if op=='text':
  r=PdfReader(absolute(a['source']));pages=a.get('pages',list(range(1,min(len(r.pages),20)+1)))
  if len(pages)>100: raise ValueError('Maximum100pages')
  return {'total_pages':len(r.pages),'pages':[{'page':i,'text':r.pages[i-1].extract_text()[:30000]} for i in pages if 1<=i<=len(r.pages)]}
 dst=output(a['destination']);w=PdfWriter()
 if op=='merge':
  for p in a['sources']: w.append(str(absolute(p)))
 elif op=='split':
  r=PdfReader(absolute(a['source']))
  for i in a['pages']:
   if type(i)!=int or not 1<=i<=len(r.pages): raise ValueError('Page out of range')
   w.add_page(r.pages[i-1])
 else: raise ValueError('operation text|merge|split')
 with dst.open('xb') as f: w.write(f)
 count=len(w.pages);w.close();return {'saved':str(dst),'pages':count}

if __name__=='__main__':
 try: print(json.dumps(main(json.load(sys.stdin)),ensure_ascii=False,default=str))
 except Exception as e: print(json.dumps({'error':str(e)}));sys.exit(1)
