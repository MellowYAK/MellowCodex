import json,subprocess
from pathlib import Path
import playwright
from hub.browser import SNAPSHOT_JS
from hub.browser_evidence import compact_browser

def test_checkbox_checked_state_changes_even_when_value_stays_on():
 node=Path(playwright.__file__).parent/'driver'/'node.exe'
 if not node.exists():node=node.with_name('node')
 source="""
global.innerWidth=800;global.innerHeight=600;global.location={href:'https://example.test'};
global.getComputedStyle=()=>({visibility:'visible',display:'block'});
const checkbox={tagName:'INPUT',type:'checkbox',value:'on',checked:false,innerText:'I agree',disabled:false,
getBoundingClientRect:()=>({x:1,y:1,left:1,right:101,top:1,bottom:21,width:100,height:20}),
getAttribute:()=>null,setAttribute:()=>{},closest:()=>null,querySelector:()=>null};
global.document={title:'Agreement',body:{innerText:'Agreement'},querySelector:()=>null,
querySelectorAll:s=>s==='a[href]'||s.startsWith('h1')||s.startsWith('[role=alert]')?[]:[checkbox]};
const snap=SNAPSHOT;
const before=snap('before');checkbox.checked=true;const after=snap('after');
console.log(JSON.stringify({before,after}));
""".replace('SNAPSHOT',SNAPSHOT_JS)
 data=json.loads(subprocess.run([str(node),'-e',source],check=True,capture_output=True,text=True).stdout)
 for state,checked in [('before',False),('after',True)]:
  page=dict(data[state],id=state)
  item=compact_browser(page,2500)['elements'][0]
  assert item['value']=='on' and item['checked'] is checked
