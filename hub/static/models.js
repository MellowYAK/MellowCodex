/* Installation uses the same persistent jobs as local tools and MCP. */
(()=>{
 const dialog=document.getElementById('quick-model-dialog');
 const box=document.createElement('section');
 const title=document.createElement('h3');title.textContent='התקנת מודלים';box.append(title);
 const label=document.createElement('label');label.textContent='שם מודל ב־Ollama ';
 const input=document.createElement('input');input.placeholder='qwen2.5-coder:7b';input.dir='ltr';input.maxLength=160;label.append(input);box.append(label);
 const note=document.createElement('p');note.textContent='הורדה בלבד. המודל לא ייבחר ולא ייטען לכרטיס המסך.';box.append(note);
 const status=document.createElement('p');status.setAttribute('role','status');box.append(status);
 const list=document.createElement('div');box.append(list);
 async function call(path,body){const r=await fetch('/api/models/'+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const value=await r.json();if(!r.ok)throw Error(value.detail||r.status);return value;}
 function button(text,action){const b=document.createElement('button');b.textContent=text;b.onclick=async()=>{b.disabled=true;try{await action()}catch(e){status.textContent=e.message}finally{b.disabled=false}};return b;}
 async function refresh(){
  const data=await call('catalog');list.replaceChildren();
  const labels={queued:'בתור',downloading:'מוריד',verifying:'מאמת התקנה',ready:'מותקן ומאומת',interrupted:'הורדה הופסקה',failed:'ההורדה נכשלה'};
  for(const job of data.jobs){
   const row=document.createElement('div');const p=job.progress;
   row.textContent=job.model+' · '+(labels[job.state]||job.state)+(p.total?' · '+Math.floor((p.completed||0)*100/p.total)+'%':'')+(p.error?' · '+p.error:'');
   if(['queued','downloading','verifying'].includes(job.state))row.append(button('עצור הורדה',async()=>{await call('cancel',{id:job.id});await refresh()}));
   if(['interrupted','failed'].includes(job.state))row.append(button('נסה להמשיך',async()=>{const p=job.provenance;await call(p?'install-hf':'install',p?{repo:p.repository,filename:p.file.name,request_id:crypto.randomUUID()}:{model:job.model,request_id:crypto.randomUUID()});await refresh()}));
   list.append(row);
  }
 }
 box.insertBefore(button('הורד מודל',async()=>{await call('install',{model:input.value.trim(),request_id:crypto.randomUUID()});status.textContent='הבקשה נרשמה. ההתקדמות מוצגת כאן.';await refresh()}),status);
 box.insertBefore(button('רענן הורדות',refresh),status);dialog.insertBefore(box,document.getElementById('quick-model-close'));
 const searchLabel=document.createElement('label');searchLabel.textContent='חיפוש ב־Hugging Face ';
 const query=document.createElement('input');query.placeholder='Qwen GGUF';query.maxLength=160;searchLabel.append(query);box.append(searchLabel);
 const results=document.createElement('div');box.append(button('חפש מודלים',async()=>{
  const data=await call('search?'+new URLSearchParams({query:query.value.trim()}));results.replaceChildren();
  for(const model of data.results){const row=document.createElement('div');row.append(button(model.id,async()=>{
   const data=await call('details?'+new URLSearchParams({repo:model.id}));const detail=document.createElement('div');
   const info=document.createElement('p');info.textContent='רישיון: '+(data.license||'לא צוין')+' · גרסה: '+(data.revision||'לא זמינה')+' · תאימות הרצה טרם נבדקה';detail.append(info);
   for(const file of data.files){const line=document.createElement('p');line.textContent=file.name+' · '+(file.bytes?(file.bytes/1024**3).toFixed(2)+' GiB':'גודל לא ידוע');
    if(file.install_supported&&!data.gated&&!data.private)line.append(button('התקן קובץ זה',async()=>{await call('install-hf',{repo:model.id,filename:file.name,request_id:crypto.randomUUID()});await refresh()}));
    else line.append(document.createTextNode(' · אינו נתמך במתקין זה'));
    detail.append(line);
   }row.replaceChildren(row.firstChild,detail);
  }));results.append(row)}
 }));box.append(results);

 // One shared profile API serves this UI and the authenticated MCP tools.
 const profileSection=document.createElement('section');profileSection.className='model-profile-editor';box.append(profileSection);
 const heading=document.createElement('h3');heading.textContent='ניהול מודלים: הגדרות גלובליות ואישיות';profileSection.append(heading);
 const policyStatus=document.createElement('p');policyStatus.setAttribute('role','status');profileSection.append(policyStatus);
 function field(label,kind,choices){
  const wrapper=document.createElement('label');wrapper.textContent=label+' ';
  const element=document.createElement(kind==='select'?'select':'input');
  if(kind==='select')for(const [value,title] of choices){const option=document.createElement('option');option.value=value;option.textContent=title;element.append(option)}
  else{element.type=kind;element.min='0'}
  wrapper.append(element);profileSection.append(wrapper);return element;
 }
 const globalPreset=field('פרופיל גלובלי פעיל','select',[]);
 const globalMode=field('ברירת מחדל GPU/CPU','select',[['auto','חלוקה אוטומטית'],['gpu','GPU בלבד'],['cpu','CPU בלבד'],['percent','אחוז GPU'],['layers','מספר שכבות']]);
 const globalPercent=field('אחוז משקלי המודל ב־GPU','number');globalPercent.max='100';
 const globalContext=field('טוקני הקשר גלובליים','select',[['maximum','מקסימום מעשי'],['manual','ערך ידני']]);
 const globalContextValue=field('טוקנים ידניים להקשר','number');
 const globalOutput=field('טוקני פלט גלובליים','select',[['maximum','מקסימום מעשי'],['manual','ערך ידני']]);
 const globalOutputValue=field('טוקנים ידניים לפלט','number');
 const customPreset=field('שם פרופיל גלובלי חדש (רשות)','text');
 const modelSelect=field('מודל מותקן','select',[]);
 const modelMode=field('דריסה אישית של חלוקת GPU/CPU','select',[['','לרשת מהפרופיל הגלובלי'],['auto','אוטומטי'],['gpu','GPU בלבד'],['cpu','CPU בלבד'],['percent','אחוז משקלים'],['layers','מספר שכבות']]);
 const gpuPercent=field('אחוז משקלים אישי ב־GPU','number');gpuPercent.max='100';
 const gpuLayers=field('מספר שכבות GPU ידני','number');
 const modelContext=field('חלון הקשר אישי','select',[['','ירושה גלובלית'],['maximum','מקסימום מעשי'],['manual','ערך ידני']]);
 const modelContextValue=field('טוקנים אישיים להקשר','number');
 const modelOutput=field('פלט אישי','select',[['','ירושה גלובלית'],['maximum','מקסימום מעשי'],['manual','ערך ידני']]);
 const modelOutputValue=field('טוקנים אישיים לפלט','number');
 let policyCache=null;
 const inputNum=(el,fallback)=>Number.isFinite(Number(el.value))&&el.value!==''?Number(el.value):fallback;
 async function policyRefresh(){
  const model=modelSelect.value;
  const [catalog,policy]=await Promise.all([call('catalog'),call('profiles'+(model?'?'+new URLSearchParams({model}):''))]);
  policyCache=policy;
  const modelNames=(catalog.installed||[]).map(item=>item.name);
  modelSelect.replaceChildren();
  for(const name of modelNames){const option=document.createElement('option');option.value=name;option.textContent=name;modelSelect.append(option)}
  if(modelNames.includes(model))modelSelect.value=model;
  const gl=policy.global,choices={...policy.builtin_presets,...gl.presets};
  globalPreset.replaceChildren();
  for(const name of Object.keys(choices)){const option=document.createElement('option');option.value=name;option.textContent=name;globalPreset.append(option)}
  globalPreset.value=gl.active_preset;
  globalMode.value=gl.defaults.mode;
  globalPercent.value=gl.defaults.gpu_percent;
  globalContext.value=gl.defaults.context_mode;globalContextValue.value=gl.defaults.context_tokens??'';
  globalOutput.value=gl.defaults.output_mode;globalOutputValue.value=gl.defaults.output_tokens??'';
  const override=policy.model_overrides[modelSelect.value]||{};
  modelMode.value=override.mode??'';
  gpuPercent.value=override.gpu_percent??'';
  gpuLayers.value=override.gpu_layers??'';
  modelContext.value=override.context_mode??'';
  modelContextValue.value=override.context_tokens??'';
  modelOutput.value=override.output_mode??'';
  modelOutputValue.value=override.output_tokens??'';
  policyStatus.textContent='פרופיל גלובלי: '+gl.active_preset+' · מגבלת בקשות: '+(gl.request_limit===null?'ללא תקרה שרירותית':gl.request_limit)
    +' · הגדרות אישיות נשמרות רק למודל שנבחר. חלוקה באחוזים היא יעד משקלים, לא שימוש VRAM מדויק.';
  return policy;
 }
 modelSelect.onchange=()=>policyRefresh().catch(e=>policyStatus.textContent=e.message);
 profileSection.append(button('שמור הגדרות גלובליות',async()=>{
  const old=policyCache.global;
  const defaults={...old.defaults,mode:globalMode.value,gpu_percent:inputNum(globalPercent,70),context_mode:globalContext.value,output_mode:globalOutput.value,
   context_tokens:globalContext.value==='manual'?inputNum(globalContextValue,null):null,
   output_tokens:globalOutput.value==='manual'?inputNum(globalOutputValue,null):null};
  const settings={active_preset:globalPreset.value,defaults};
  const result=await call('profiles/global',{settings});if(!result.accepted)throw Error(result.error||'לא נשמר');
  policyStatus.textContent='ההגדרות הגלובליות נשמרו';await policyRefresh();
 }));
 profileSection.append(button('שמור פרופיל אישי למודל',async()=>{
  if(!modelSelect.value)throw Error('בחר מודל מותקן');
  const settings={};
  if(modelMode.value){settings.mode=modelMode.value;
   if(modelMode.value==='percent')settings.gpu_percent=inputNum(gpuPercent,null);
   if(modelMode.value==='layers')settings.gpu_layers=inputNum(gpuLayers,null);
  }
  if(modelContext.value){settings.context_mode=modelContext.value;
   if(modelContext.value==='manual')settings.context_tokens=inputNum(modelContextValue,null)}
  if(modelOutput.value){settings.output_mode=modelOutput.value;
   if(modelOutput.value==='manual')settings.output_tokens=inputNum(modelOutputValue,null)}
  const result=await call('profiles/model',{model:modelSelect.value,settings});if(!result.accepted)throw Error(result.error||'לא נשמר');
  policyStatus.textContent='נשמר פרופיל אישי: '+modelSelect.value;await policyRefresh();
 }));
 profileSection.append(button('בטל דריסות אישיות',async()=>{
  const result=await call('profiles/model',{model:modelSelect.value,reset:true});
  if(!result.accepted)throw Error(result.error||'שגיאת איפוס');await policyRefresh();
 }));
 profileSection.append(button('שמור פרופיל גלובלי בשם',async()=>{
  const name=customPreset.value.trim();if(!/^[a-zA-Z0-9_-]{2,64}$/.test(name))throw Error('שם פרופיל: 2–64 תווים באנגלית, מספרים או _-');
  const old=policyCache.global;
  const defaults={mode:globalMode.value,gpu_percent:inputNum(globalPercent,70),
   context_mode:globalContext.value,output_mode:globalOutput.value};
  if(globalContext.value==='manual')defaults.context_tokens=inputNum(globalContextValue,null);
  if(globalOutput.value==='manual')defaults.output_tokens=inputNum(globalOutputValue,null);
  const presets={...old.presets,[name]:defaults};
  const res=await call('profiles/global',{settings:{presets,active_preset:name}});
  if(!res.accepted)throw Error(res.error||'שגיאת שמירה');await policyRefresh();
 }));
 profileSection.append(button('טען מודל עם הפרופיל השמור',async()=>{
  if(!modelSelect.value)throw Error('בחר מודל');
  const response=await fetch('/api/model/memory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'switch',model:modelSelect.value})});
  const result=await response.json();if(!response.ok||!result.verified)throw Error(result.detail||result.error||'הטעינה לא אומתה');
  policyStatus.textContent='המודל נטען. '+JSON.stringify({placement:result.placement,models:result.memory?.models});
 }));
 profileSection.append(button('בדוק חלוקת זיכרון בפועל',async()=>{
  const response=await fetch('/api/model/memory');const result=await response.json();
  if(!response.ok)throw Error(result.detail||'לא ניתן לקרוא זיכרון');
  policyStatus.textContent=(result.models||[]).map(m=>m.name+' · GPU '+(m.size_vram/1024**3).toFixed(2)+' GiB · CPU/RAM '+((m.size-m.size_vram)/1024**3).toFixed(2)+' GiB').join(' | ')||'אין מודל טעון';
 }));
 profileSection.append(button('רענן הגדרות ופרופילים',policyRefresh));
 policyRefresh().catch(e=>policyStatus.textContent=e.message);

 setInterval(()=>{if(dialog.open)refresh().catch(e=>status.textContent=e.message)},2000);
})();
