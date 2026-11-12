/* Shared visual route editor; all text rendered as text, never HTML. */
(()=>{
 const dialog=el('dialog');dialog.id='action-routes-dialog';dialog.dir='rtl';
 const status=el('p'),list=el('section'),editor=el('section'),query=el('input'),folderFilter=el('input');
 query.placeholder='חיפוש מסלולים';query.setAttribute('aria-label','חיפוש מסלולים');
 let target=null,current=null,dirty=false,loading=false,next=null;
 const toolbar=el('div',undefined,'route-toolbar'),layout=el('div',undefined,'route-layout');
 const more=button('מסלולים נוספים',()=>refresh(next,true));
 const endpoint=()=>'/chats/'+target+'/action-routes';
 async function call(action,args={}){return api(endpoint(),{action,...args})}
 function field(parent,label,value,onchange,multiline=false){
  const lab=el('label',label),input=el(multiline?'textarea':'input');input.value=value||'';input.setAttribute('aria-label',label);
  input.oninput=()=>{onchange(input.value);dirty=true};lab.append(input);parent.append(lab);return input;
 }
 function discard(){return !dirty||confirm('יש שינויים שלא נשמרו. לעזוב אותם?')}
 async function refresh(offset=0,append=false){
  if(loading)return;loading=true;
  try{
   const result=await call('list',{query:query.value,offset:offset||0});
   if(!append)list.replaceChildren();
   for(const r of result.items){
    const row=el('article',undefined,'route-list-item');
    row.append(button(r.title,async()=>{if(!discard())return;current=await call('get',{route_id:r.id});dirty=false;render()}),
     el('small',(r.folder||'ללא תיקייה')+' · '+r.steps+' שלבים · '+r.scope+' · '+r.verification));
    list.append(row);
   }
   next=result.next_offset;more.hidden=next===null;
  }finally{loading=false}
 }
 function blankStep(){return {title:'שלב חדש',expected:'',instruction:'',success:'',notes:'',before_url:'',after_url:'',images:[],evidence:[]}}
 function newRoute(){if(!discard())return;current={title:'מסלול חדש',folder:'',description:'',start_url:'',scope:'chat',enabled:true,parameters:[],steps:[blankStep()],revision:0,can_edit:true};dirty=true;render()}
 function render(){
  editor.replaceChildren();if(!current)return;
  const r=current;const header=el('section',undefined,'route-header');
  header.append(el('h3',r.title),el('p','גרסה '+r.revision+' · '+(r.verification||'draft')+' · תמונות היסטוריות אינן מצב הדפדפן הנוכחי.'));
  field(header,'שם המסלול',r.title,v=>r.title=v);
  field(header,'תיקייה',r.folder,v=>r.folder=v);
  field(header,'תיאור',r.description,v=>r.description=v,true);
  field(header,'כתובת דף ההתחלה',r.start_url,v=>r.start_url=v);
  const scope=el('select');scope.setAttribute('aria-label','שיתוף המסלול');
  for(const [v,t] of [['chat','השיחה הזו'],['project','כל השיחות בפרויקט'],['global','כל הסוכנים והפרויקטים שלי']]){const o=el('option',t);o.value=v;scope.append(o)}
  scope.value=r.scope;scope.onchange=()=>{r.scope=scope.value;dirty=true};
  const enabled=el('input');enabled.type='checkbox';enabled.checked=r.enabled;enabled.onchange=()=>{r.enabled=enabled.checked;dirty=true};
  const enabledLabel=el('label','מסלול פעיל');enabledLabel.prepend(enabled);header.append(scope,enabledLabel);
  const pars=el('section');pars.append(el('h4','משתנים — כתבו בהנחיות למשל {{channel}}'));
  r.parameters.forEach((p,i)=>{
   const row=el('div',undefined,'route-parameter');
   field(row,'שם משתנה באנגלית',p.name,v=>p.name=v);field(row,'מה לשאול את המשתמש',p.label,v=>p.label=v);
   row.append(button('הסר משתנה',()=>{r.parameters.splice(i,1);dirty=true;render()}));pars.append(row);
  });
  pars.append(button('הוסף משתנה',()=>{r.parameters.push({name:'parameter'+(r.parameters.length+1),label:'',required:true});dirty=true;render()}));
  editor.append(header,pars);
  r.steps.forEach((s,i)=>{
   const card=el('article',undefined,'route-step');card.dataset.stepId=s.id||'new-'+i;
   card.append(el('h3','שלב '+(i+1)));
   field(card,'כותרת השלב',s.title,v=>s.title=v);
   field(card,'כתובת לפני הפעולה',s.before_url,v=>s.before_url=v);
   field(card,'כתובת אחרי הפעולה',s.after_url,v=>s.after_url=v);
   field(card,'המסך המצופה',s.expected,v=>s.expected=v,true);
   field(card,'מה לבצע במסך הזה',s.instruction,v=>s.instruction=v,true);
   field(card,'איך יודעים שהשלב הצליח',s.success,v=>s.success=v,true);
   field(card,'הערות והנחיות נוספות',s.notes,v=>s.notes=v,true);
   const gallery=el('div',undefined,'route-gallery');
   function picture(kind,item,index){
    const fig=el('figure'),img=el('img');img.alt=kind==='evidence'?'צילום היסטורי מהביצוע':'תמונת ייחוס שהמשתמש צירף';img.loading='lazy';img.onclick=()=>window.open(img.src,'_blank','noopener');
    if(r.id&&s.id&&(kind==='evidence'||item.sha256))img.src='/api'+endpoint()+'/'+r.id+'/image/'+s.id+'/'+kind+'/'+index;
    else if(kind==='reference')img.src='/api/files/'+item.file_id+'/content';
    img.onerror=()=>{img.hidden=true;fig.append(el('p','התמונה אינה זמינה — המקור לא נמחק על ידי המסלול.'))};
    fig.append(img,el('figcaption',kind==='evidence'?'ראיה היסטורית · '+item.phase+' · '+(item.title||''):'דוגמה בלבד — לא ראיה חיה'));
    if(kind==='evidence'&&item.url&&/^https?:\/\//.test(item.url)){
     const link=el('a','פתח כתובת מקור היסטורית');link.href=item.url;link.target='_blank';link.rel='noopener noreferrer';fig.append(link);
    }
    if(kind==='reference'){field(fig,'הערה לתמונה',item.caption,v=>item.caption=v);fig.append(button('הסר מהשלב',()=>{s.images.splice(index,1);dirty=true;render()}))}
    gallery.append(fig);
   }
   (s.evidence||[]).forEach((v,n)=>picture('evidence',v,n));(s.images||[]).forEach((v,n)=>picture('reference',v,n));card.append(gallery);
   const upload=el('input');upload.type='file';upload.accept='image/png,image/jpeg,image/webp';upload.setAttribute('aria-label','הוסף צילום מסך לשלב '+(i+1));
   upload.onchange=()=>safe(async()=>{
    const file=upload.files[0];if(!file)return;if(file.size>10000000)throw Error('צילום עד 10 MB');
    const response=await fetch('/api/files/upload?name='+encodeURIComponent(file.name),{method:'POST',headers:{'Content-Type':file.type},body:file});
    const result=await response.json();if(!response.ok)throw Error(result.detail||'העלאה נכשלה');
    s.images.push({file_id:result.id,caption:''});dirty=true;render();
   });
   card.append(upload,button('הוסף שלב אחרי',()=>{r.steps.splice(i+1,0,blankStep());dirty=true;render()}),
    button('למעלה',()=>{if(i){[r.steps[i-1],r.steps[i]]=[r.steps[i],r.steps[i-1]];dirty=true;render()}}),
    button('למטה',()=>{if(i<r.steps.length-1){[r.steps[i+1],r.steps[i]]=[r.steps[i],r.steps[i+1]];dirty=true;render()}}),
    button('מחק שלב',()=>{if(r.steps.length>1){r.steps.splice(i,1);dirty=true;render()}}));
   editor.append(card);
  });
  const controls=el('div',undefined,'route-toolbar');
  const history=el('section',undefined,'route-run-history');
  if(r.id){
   controls.append(button('היסטוריית הרצות ושחזור',()=>safe(async()=>{
    const found=await call('runs',{route_id:r.id});
    history.replaceChildren(el('h4','הרצות קודמות'));
    for(const entry of found.runs){
     const line=el('section',undefined,'route-run-item');
     line.append(el('small',entry.task_id+' · '+entry.state+' · גרסה '+entry.revision));
     line.append(button('בדוק מאיפה להמשיך',()=>safe(async()=>{
      const state=await call('resume',{route_id:r.id,task_id:entry.task_id});
      line.append(el('p','כתובת אחרונה: '+(state.last_observed_url||'לא זמינה')+' · פעולות לבדיקה: '+state.pending_action_ids.length));
      line.append(el('p','יש לבצע תצפית חדשה לפני המשך. ההיסטוריה אינה הרשאה להרצה חוזרת.'));
      for(const action of state.browser_actions)line.append(el('small',action.tool+' · '+action.state+' · '+(action.url||'')));
     })));
     history.append(line);
    }
   })));
  }
  controls.append(button('שמור מסלול',save),button('הוסף שלב',()=>{r.steps.push(blankStep());dirty=true;render()}),
   button('הרץ עם משתנים',run),button('מחק מסלול',async()=>{
    if(!r.id)return;if(!confirm('למחוק את המסלול מהספרייה? השיחות, קבצי התמונות והראיות המקוריות יישמרו.'))return;
    await call('delete',{route_id:r.id,expected_revision:r.revision});current=null;dirty=false;render();await refresh();
   }));
  editor.append(controls,history);
  if(!r.can_edit){editor.querySelectorAll('input,textarea,select,button').forEach(e=>e.disabled=true);editor.append(button('צור עותק לעריכה בשיחה הזו',()=>{current={...structuredClone(r),id:undefined,revision:0,scope:'chat',can_edit:true};current.steps.forEach(s=>s.evidence=[]);dirty=true;render()}),button('הרץ מסלול משותף',run))}
 }
 async function save(){
  if(!current)return;
  let sharing=false;
  if(current.scope!=='chat')sharing=confirm('שיתוף המסלול כולל הנחיות וצילומים היסטוריים. לאשר שיתוף בתחום שנבחר?');
  if(current.scope!=='chat'&&!sharing)return;
  const result=await call(current.id?'save':'create',{route_id:current.id,body:current,expected_revision:current.revision,scope:current.scope,share_confirmed:sharing});
  current=result;dirty=false;status.textContent='נשמרה גרסה '+result.revision;render();await refresh();
 }
 async function run(){
  if(dirty){await save();if(dirty)return}if(!current?.id)return;
  const values={};
  for(const p of current.parameters){const v=prompt(p.label||p.name);if(v===null)return;values[p.name]=v}
  const result=await call('run',{route_id:current.id,values,request_id:uid()});
  if(result.missing_parameters)throw Error('חסרים משתנים: '+result.missing_parameters.map(p=>p.label).join(', '));
  status.textContent='משימה '+result.task_id+' · '+result.state+' — ההרצה אינה הוכחת הצלחה';
 }
 toolbar.append(query,button('חפש',()=>refresh()),button('מסלול חדש',newRoute),button('זכור ביצוע קודם',async()=>{
  if(!discard())return;const id=prompt('מזהה המשימה שהסתיימה בשיחה הזו');if(!id)return;const title=prompt('שם למסלול');if(!title)return;
  current=await call('learn',{source_task_id:id.trim(),title});dirty=false;render();await refresh();
 }),button('סגור',()=>{if(discard())dialog.close()}));
 layout.append(list,editor);dialog.append(el('h2','מסלולי פעולה'),el('p','שלבים, משתנים, צילומי ייחוס והנחיות משותפים. מסלול אינו מחליף הרשאות או אימות בזמן ביצוע.'),toolbar,status,layout,more);
 document.body.append(dialog);
 dialog.addEventListener('cancel',e=>{if(!discard())e.preventDefault()});
 window.openActionRoutes=()=>safe(async()=>{if(!selected)throw Error('בחר שיחה');if(dialog.open)return;target=selected;current=null;dirty=false;editor.replaceChildren();dialog.showModal();await refresh()});
 const launch=button('מסלולי פעולה',window.openActionRoutes);launch.id='action-routes-open';($('settings-dialog')||document.body).prepend(launch);
 const quick=button('מסלולי פעולה',window.openActionRoutes);quick.id='action-routes-quick';document.querySelector('aside')?.append(quick);
})();
