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
 setInterval(()=>{if(dialog.open)refresh().catch(e=>status.textContent=e.message)},2000);
})();
