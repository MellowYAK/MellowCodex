import pathlib,tempfile,subprocess,sys,json
def run(a):
 p=subprocess.run([sys.executable,'tool.py'],input=json.dumps(a),capture_output=True,text=True)
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);a=p/'a.pdf';w=PdfWriter();w.add_blank_page(width=100,height=100);w.add_blank_page(width=100,height=100)
 font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
 w.pages[0][NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
 stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 10 50 Td (sample PDF text) Tj ET')
 w.pages[0][NameObject('/Contents')]=w._add_object(stream)
 with a.open('wb') as f: w.write(f)
 b=p/'b.pdf';c=p/'c.pdf'
 assert run({'operation':'split','source':str(a),'destination':str(b),'pages':[2]})['pages']==1
 assert run({'operation':'merge','sources':[str(a),str(b)],'destination':str(c)})['pages']==3
 r=run({'operation':'text','source':str(c)});assert r['total_pages']==3 and 'sample PDF text' in r['pages'][0]['text']
print('PDF merge/split and nonempty text extraction passed')
