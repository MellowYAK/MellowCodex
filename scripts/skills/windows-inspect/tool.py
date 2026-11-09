import json,sys
from pywinauto import Desktop
def main(a):
    if not isinstance(a,dict) or set(a)-{'handle','limit'}: raise ValueError('Expected handle and/or limit')
    limit=a.get('limit',30)
    if type(limit) is not int or not 1<=limit<=100: raise ValueError('limit must be 1..100')
    desktop=Desktop(backend='win32')
    if 'handle' in a:
        h=a['handle']
        if type(h) is not int or h<=0: raise ValueError('positive integer handle required')
        items=desktop.window(handle=h).wrapper_object().children()
    else: items=desktop.windows(visible_only=True)
    rows=[]
    for w in items[:limit]:
        try: rows.append({'handle':int(w.handle),'title':w.window_text(),'class':w.class_name(),'pid':w.process_id()})
        except Exception as e: rows.append({'error':type(e).__name__})
    return {'windows':rows,'truncated':len(items)>limit}
if __name__=='__main__':
    try: print(json.dumps(main(json.load(sys.stdin)),ensure_ascii=False))
    except Exception as e:
        print(json.dumps({'error':str(e)}));sys.exit(1)
