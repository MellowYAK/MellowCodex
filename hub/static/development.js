/* Shared candidate/guidance service. Text is rendered through textContent. */
(()=>{
 let dialog,taskId,strings,guidanceOnly=false;
 const node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(tag==='pre'){e.dir='ltr';e.style.cssText='text-align:left;white-space:pre-wrap;overflow-wrap:anywhere'}else if(['p','h3','h4'].includes(tag))e.dir='auto';return e};
 const request=async(path,body)=>{const r=await fetch('/api/development/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw Error(d.detail||JSON.stringify(d));return d};
 const run=async action=>{try{await action()}catch(e){dialog.append(node('p',e.message))}};
 async function render(){
  const [data,status]=await Promise.all([(guidanceOnly?Promise.resolve({candidates:[]}):request('list',{task_id:taskId})),request('guidance/status',{task_id:taskId})]);
  dialog.replaceChildren(node('h2',strings['development.review_title']),node('p',status.human_request_original));
  if(!guidanceOnly)dialog.append(node('p',strings['development.pending_activation']));
  for(const c of data.candidates){
   const section=node('section');section.append(node('h3',c.id),node('p',strings['development.revision']+' '+c.revision+' · '+c.state));
   const button=node('button',strings['development.show_diff']);
   button.onclick=()=>run(async()=>{const d=await request('diff',{task_id:taskId,candidate_id:c.id});const details=node('div');for(const f of d.files){details.append(node('h4',f.path),node('pre',f.diff));if(f.truncated)details.append(node('p',strings['development.truncated']))}section.append(details);button.disabled=true});
   section.append(button);dialog.append(section);
   if(c.files&&c.files['hub/development/worker.py']){
    const stage=node('button','הכן גרסת רכיב ביצוע');stage.onclick=()=>run(async()=>{
     stage.disabled=true;try{const release=await request('release',{task_id:taskId,candidate_id:c.id,revision:c.revision});
      section.append(node('p','גרסה מוכנה: '+release.id+' · טרם הופעלה'));
      const activate=node('button','הפעל גרסה מוכנה');activate.onclick=()=>run(async()=>{
       activate.disabled=true;const response=await fetch('/api/upgrades/activate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({release_id:release.id,request_id:crypto.randomUUID()})});const result=await response.json();if(!response.ok)throw Error(result.detail||response.status);
       section.append(node('p','בקשת ההפעלה נרשמה: '+result.id+' · בדוק את מצב העדכון. תצפית אורכת לפחות דקה.'));
      });section.append(activate);
     }finally{stage.disabled=false}
    });section.append(stage);
   }
   for(const test of c.test_results||[]){
    const details=node('details');details.append(node('summary',strings['development.revision']+' '+test.revision+' · '+strings[test.verified?'development.test_passed':'development.test_failed']));
    details.append(node('pre',test.output),node('p','Exit: '+test.exit_code+(test.timed_out?' · timeout':'')));section.append(details);
   }
  }
  if(!guidanceOnly&&!data.candidates.length)dialog.append(node('p',strings['development.no_candidates']));
  for(const g of status.guidance){dialog.append(node('p',g.text),node('small',g.consumed_epoch===status.consumer_epoch?strings['development.in_packet']:strings['development.received']))}
  if(status.last_action_evidence)dialog.append(node('small','Action evidence after guidance: '+status.last_action_evidence.action_id+'; execution evidence, not proof of semantic compliance.'));
  const input=node('textarea');input.placeholder=strings['development.guidance_placeholder'];input.maxLength=8000;dialog.append(input);
  const send=node('button',strings['development.send_guidance']);send.onclick=()=>run(async()=>{send.disabled=true;try{await request('guidance',{task_id:taskId,expected_task_revision:status.task_revision,expected_revision:status.guidance_revision,consumer_epoch:status.consumer_epoch,request_id:crypto.randomUUID(),text:input.value});await render()}finally{send.disabled=false}});dialog.append(send);
  const refresh=node('button',strings['development.refresh']);refresh.onclick=()=>run(render);dialog.append(refresh);
  const upgrades=node('button','מצב עדכון רכיב הביצוע');upgrades.onclick=()=>run(async()=>{
   const response=await fetch('/api/upgrades/status');const state=await response.json();if(!response.ok)throw Error(state.detail||response.status);
   const area=node('section');area.append(node('h3','עדכוני רכיב הביצוע'),node('p','גרסה פעילה: '+(state.active.release_id||'גרסת הבסיס')+' · דור '+state.active.epoch));
   for(const job of state.updates){area.append(node('p',job.release_id+' · '+job.state));if(job.error)area.append(node('p',job.error))}
   for(const job of state.requests)area.append(node('p',job.operation+' · '+job.state));
   area.append(node('p','הממשק והשרת אינם מוחלפים במסלול זה.'));dialog.append(area);
  });if(!guidanceOnly)dialog.append(upgrades);
  const close=node('button',strings['development.close']);close.onclick=()=>dialog.close();dialog.append(close);
 }
 window.openDevelopment=async (id,onlyGuidance=false)=>{
  guidanceOnly=onlyGuidance;
  taskId=id;
  if(!dialog){dialog=node('dialog');dialog.dir='rtl';dialog.style.cssText='width:min(850px,90vw);max-height:85vh;overflow:auto';document.body.append(dialog)}
  if(!strings)strings=await(await fetch('/api/context/catalog/he')).json();
  dialog.replaceChildren();dialog.showModal();await run(render);
 };
})();
