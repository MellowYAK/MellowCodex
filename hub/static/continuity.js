/* Exact durable history and explicit notes share the HTTP/MCP service. */
(()=>{
 const dialog=el('dialog');dialog.id='continuity-dialog';dialog.dir='rtl';
 const title=el('h2','זיכרון השיחה'),status=el('p'),notes=el('textarea');notes.maxLength=6000;notes.setAttribute('aria-label','החלטות והנחיות לשיחה');
 const history=el('div',undefined,'history-list');let target=null,revision=0,cursor=-1;
 const more=button('טען פניות נוספות',()=>load());
 const anchors=el('section');let anchorCursor=null;
 const anchorsMore=button('החלטות שמורות נוספות',()=>loadAnchors());
 async function loadAnchors(){const data=await api('/chats/'+target+'/anchors'+(anchorCursor===null?'':'?after='+anchorCursor));for(const a of data.items){const row=el('article');row.append(el('h4',a.label),el('blockquote',a.quote),el('small',a.source_changed?'המקור השתנה — נדרשת בדיקה':a.superseded?'קיימת החלטה מאוחרת המחליפה זו':'ציטוט מהבקשה המקורית'),button('קרא מקור',()=>detail(a.source_task_id,'goal',row)));row.append(button('Pin in this chat',()=>changePin(a.id,'chat',true)),button('Share with project',()=>changePin(a.id,'project',true)),button('Unpin',()=>changePin(a.id,'chat',false)));anchors.append(row)}anchorCursor=data.next_after;anchorsMore.hidden=anchorCursor===null;}

 const reviews=el('section');let reviewCursor=null;
 const reviewsMore=button('משובים קודמים',()=>loadReviews());
 async function loadReviews(){const data=await api('/chats/'+target+'/memory-reviews'+(reviewCursor===null?'':'?after='+reviewCursor));const states={pending:'ממתין למשוב',stale:'המקור השתנה — האימות אינו עדכני',confirmed:'אושר במשוב',contradicted:'נמצאה סתירה — יש לבדוק את המקור',unavailable:'אין הקשר מספיק לאימות'};for(const r of data.items){const row=el('article');row.append(el('h4',states[r.status==='reviewed'?r.response.verdict:r.status]||r.status),el('p',r.request.claim),el('blockquote',r.request.evidence_quote),el('p',r.response?.evidence||'טרם התקבלה תשובה. הסוכן יכול להמשיך עם המקורות המקומיים.'),button('קרא מקור המשוב',()=>detail(r.request.source_task_id,r.request.field,row)));reviews.append(row)}reviewCursor=data.next_after;reviewsMore.hidden=reviewCursor===null;}
 const feedback=el('section'),enabled=el('input'),transport=el('select'),feedbackStatus=el('p');enabled.type='checkbox';
 const feedbackLabel=el('label','אימות זיכרון בעזרת ChatGPT');feedbackLabel.prepend(enabled);
 for(const [value,label] of [['auto','החיבור הפעיל'],['browser','צ׳אט בדפדפן'],['mcp','MCP']]){const option=el('option',label);option.value=value;transport.append(option)}
 transport.setAttribute('aria-label','חיבור למשוב זיכרון');
 feedback.append(el('h3','משוב על זיכרון השיחה'),feedbackLabel,transport,el('p','נשלח רק קטע רלוונטי קצר לאימות. אם אין גישה לשיחה המקורית, הסוכן ממשיך לפי הראיות המקומיות. המשוב נשמר בנפרד ואינו משנה את ההיסטוריה.'),button('שמור משוב זיכרון',async()=>{const saved=await api('/chats/'+target+'/memory-review/settings',{enabled:enabled.checked,transport:transport.value});enabled.checked=saved.enabled;transport.value=saved.transport;feedbackStatus.textContent=(saved.enabled?'מופעל':'כבוי')+' · יחול על בקשת האימות הבאה';}),feedbackStatus);
 async function load(){const d=await api('/chats/'+target+'/history?after='+cursor+'&limit=10');status.textContent=d.total_turns+' פניות שמורות במחשב · ההיסטוריה אינה נמחקת לפי גיל';for(const t of d.turns){const row=el('article');row.append(el('small',new Date(t.created).toLocaleString()+' · '+(labels[t.state]||t.state)),el('h3',t.goal),el('p',t.result));row.append(button('הצג את הבקשה המלאה',()=>detail(t.id,'goal',row)),button('הצג את התשובה המלאה',()=>detail(t.id,'result',row)));history.append(row)}cursor=d.next_after;more.hidden=cursor===null;}
 async function detail(id,field,row){let offset=0,text='';do{const d=await api('/chats/'+target+'/history?'+new URLSearchParams({task_id:id,field,offset,chars:6000}));text+=d.text;offset=d.next_offset;}while(offset!==null);let output=row.querySelector('pre');if(!output){output=el('pre');row.append(output)}output.textContent=text;}
 dialog.append(title,status,el('label','החלטות והנחיות לשימור'),notes,button('שמור החלטות',async()=>{const d=await api('/chats/'+target+'/continuity',{text:notes.value,expected_revision:revision,source:'user'});revision=d.revision;toast('נשמרה גרסה '+revision+' · תיכלל בהקשר המשימה הבאה')}),el('h3','היסטוריה כרונולוגית'),history,more,button('סגור',()=>dialog.close()));document.body.append(dialog);
 dialog.insertBefore(feedback,history.previousSibling);dialog.insertBefore(anchors,feedback);anchors.after(anchorsMore);feedback.after(reviews,reviewsMore);

 const contextSection=el('section'),contextStatus=el('pre'),contextSources=el('div'),policy=el('select'),targetBudget=el('input');
 contextSection.id='context-memory-controls';policy.setAttribute('aria-label','Context policy');targetBudget.type='number';targetBudget.min=2048;targetBudget.max=262144;targetBudget.setAttribute('aria-label','Working input token target');
 for(const mode of ['legacy','shadow','bounded']){const o=el('option',mode);o.value=mode;policy.append(o)}
 async function changePin(anchorId,scope,pinned){
  let offset=0,revision=0;
  do {const page=await api('/chats/'+target+'/context-pins?offset='+offset);const found=page.pin_records.find(p=>p.anchor_id===anchorId);if(found){revision=found.revision;break}if(page.pin_records.length<100)break;offset+=100;}while(true);
  await api('/chats/'+target+'/context-pins',{anchor_id:anchorId,scope,pinned,expected_revision:revision});await loadContext();
 }
 async function loadPins(offset=0){
  const pins=await api('/chats/'+target+'/context-pins?offset='+offset);
  for(const pin of pins.items)contextSources.append(el('p',pin.scope+' | '+pin.label+' | '+pin.quote));
  if(pins.next_offset!==null){const more=button('More memories',async()=>{more.remove();await loadPins(pins.next_offset)});contextSources.append(more)}
 }
 async function loadContext(){
  const data=await api('/chats/'+target+'/context-memory');policy.value=data.settings.context_management;targetBudget.value=data.settings.working_input_tokens;
  const c=data.packet?.context||{};
  contextStatus.textContent=JSON.stringify({policy:data.settings.context_management,configured_context:data.settings.context_tokens,effective_context:c.context_limit??'not yet measured',estimated_input:c.estimated_input??null,last_actual_input:data.last_actual_input??null,reserved_output:data.settings.response_tokens,components:c.components??null,checkpoint:data.checkpoint,degraded:c.degraded||c.shadow_error||null,history:'Stored history is not automatically loaded'},null,2);
  contextSources.replaceChildren(el('h4','Explicit memory: chat / project'));
  await loadPins();

  for(const ref of [...(c.included_refs||[]),...(c.omitted_refs||[])].slice(0,20)){
   const row=el('div');let offset=0;
   const sourceButton=button('Read source '+ref.message_index,async()=>{const page=await api('/chats/'+target+'/context-evidence?'+new URLSearchParams({...ref,offset:offset||0,chars:3000}));const pre=el('pre',page.text);row.append(pre);offset=page.next_offset;sourceButton.disabled=offset===null;sourceButton.textContent=offset===null?'Source fully read':'Read next source page'});row.append(sourceButton);contextSources.append(row);
  }
 }
 async function setContext(field,value,action='set'){const d=await api('/settings/model/control',{action,field,value});if(d.accepted===false)throw Error(d.error);await loadContext()}
 contextSection.append(el('h3','Context & Memory'),el('p','Estimated input and actual usage are different measurements. Settings apply globally to the next inference.'),policy,targetBudget,button('Save policy',()=>setContext('context_management',policy.value)),button('Save input target',()=>setContext('working_input_tokens',Number(targetBudget.value))),button('Restore default policy',()=>setContext('context_management',null,'reset')),button('Use legacy / rollback',()=>setContext('context_management','legacy')),button('Refresh context',()=>loadContext()),contextStatus,contextSources);
 dialog.insertBefore(contextSection,history.previousSibling);
 window.openContinuity=()=>safe(async()=>{if(!selected)throw Error('בחר שיחה כדי לפתוח את הזיכרון שלה');target=selected;cursor=-1;history.replaceChildren();const n=await api('/chats/'+target+'/continuity');notes.value=n.text;revision=n.revision;const settings=await api('/chats/'+target+'/memory-review/settings');enabled.checked=settings.enabled;transport.value=settings.transport;feedbackStatus.textContent='';anchors.replaceChildren(el('h3','החלטות עם מקור'));anchorCursor=null;reviews.replaceChildren(el('h3','משוב שהתקבל'));reviewCursor=null;dialog.showModal();await loadContext();await loadAnchors();await loadReviews();await load()});
})();
