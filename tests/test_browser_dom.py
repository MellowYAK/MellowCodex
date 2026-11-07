"""DOM contract fixtures, without opening or controlling a user browser."""
import json
import shutil
import subprocess
import pytest
from hub.browser import SNAPSHOT_JS, CLICK_JS


def run_js(source):
    node=shutil.which('node')
    if not node:pytest.skip('Node is unavailable')
    return json.loads(subprocess.run([node,'-e',source],check=True,capture_output=True,text=True).stdout)


def test_offscreen_menu_is_not_clickable_but_article_url_remains_available():
    data=run_js('''
global.innerWidth=715;global.innerHeight=783;
global.location={href:'https://example.test/'};
global.getComputedStyle=()=>({visibility:'visible',display:'block'});
function link(x,name,heading=false){return {tagName:'A',innerText:name,href:'https://example.test/'+name,
getBoundingClientRect:()=>({x,y:211,left:x,right:x+47,top:211,bottom:231,width:47,height:20}),
getAttribute:()=>null,setAttribute:()=>{},querySelector:()=>heading?{}:null,closest:()=>null};}
const menu=link(1140,'menu'),article=link(50,'article',true);
global.document={title:'Example',body:{innerText:'body'},querySelector:()=>null,querySelectorAll:()=>[menu,article]};
console.log(JSON.stringify(('''+SNAPSHOT_JS+''')('observation')));
''')
    assert [e['name'] for e in data['elements']]==['article']
    assert data['links']==[{'name':'article','href':'https://example.test/article'}]


@pytest.mark.parametrize('covered',[True,False])
def test_dom_invocation_respects_occlusion_and_does_not_repeat(covered):
    result=run_js('''
let clicks=0;
const element={isConnected:true,disabled:false,getAttribute:()=>null,scrollIntoView:()=>{},
getBoundingClientRect:()=>({x:0,y:0,width:100,height:20}),contains:()=>false,click:()=>{clicks++}};
global.getComputedStyle=()=>({visibility:'visible',display:'block'});
global.document={elementFromPoint:()=>'''+('{}' if covered else 'element')+'''};
const result=('''+CLICK_JS+''')(element); console.log(JSON.stringify({result,clicks}));
''')
    assert result['clicks']==(0 if covered else 1)
    assert result['result']['invoked'] is (not covered)
