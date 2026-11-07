"""Exercise the shipped UI queue under capture overlap and action failure."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest


def test_controls_wait_for_capture_and_recover_without_replaying_failed_action():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is unavailable')
    source = (Path(__file__).parents[1] / 'hub/static/app.js').read_text(encoding='utf-8')
    queue = source[source.index('let browserInputQueue='):source.index('function remoteInput(data)')]
    script = '''
let frameBusy=true,inputBusy=false;
const events=[];
async function refreshFrame(){
 if(inputBusy||frameBusy)throw Error('capture overlapped control');
 frameBusy=true;events.push('capture');
 await new Promise(r=>setTimeout(r,5));frameBusy=false;
}
''' + queue + '''
(async()=>{
 let attempts=0;
 const first=queueBrowserControl(async()=>{
  if(frameBusy)throw Error('control overlapped capture');
  events.push('first');attempts++;throw Error('expected action failure');
 }).catch(e=>e.message);
 const second=queueBrowserControl(async()=>{
  if(frameBusy||!inputBusy)throw Error('control ownership missing');
  events.push('second');return 'selected';
 });
 await new Promise(r=>setTimeout(r,1));
 const reserved=inputBusy, blocked=events.length===0;
 frameBusy=false;
 const result=await Promise.all([first,second]);
 console.log(JSON.stringify({events,result,reserved,blocked,attempts,inputBusy,frameBusy}));
})().catch(e=>{console.error(e);process.exit(1)});
'''
    result = json.loads(subprocess.run([node, '-e', script], check=True, capture_output=True, text=True, timeout=10).stdout)
    assert result['reserved'] and result['blocked']
    assert result['result'] == ['expected action failure', 'selected']
    assert result['events'] == ['first', 'capture', 'second', 'capture']
    assert result['attempts'] == 1
    assert not result['inputBusy'] and not result['frameBusy']
