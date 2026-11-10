/* One durable workflow shared with MCP; no browser-local task state. */
(()=>{
 let labels,dialog,body,profiles=[],catalog;
 const text=k=>labels[k]||k;
 function field(label,type='input'){const wrap=el('label',text(label)),input=el(type);input.setAttribute('aria-label',text(label));wrap.append(input);return {wrap,input}}
 function options(select,items){select.replaceChildren(...items.map(([value,title])=>{const o=el('option',title);o.value=value;return o}))}
 async function render(){
  profiles=(await api('/delegation/profiles')).items;body.replaceChildren();
  const settings=el('details');settings.append(el('summary',text('profiles')));
  const form=el('form',undefined,'delegation-form');
  const fields={};for(const k of ['id','name','provider','transport','model','endpoint','key_env']){fields[k]=field(k,['provider','transport'].includes(k)?'select':'input');form.append(fields[k].wrap)}
  options(fields.provider.input,[['chatgpt','ChatGPT'],['custom','Custom'],...catalog.providers.map(p=>[p.id,p.name])]);
  options(fields.transport.input,['mcp','play','api'].map(v=>[v,v.toUpperCase()]));
  fields.id.input.required=true;fields.name.input.required=true;
  for(const k of ['id','model','endpoint','key_env'])fields[k].input.dir='ltr';
  const save=el('button',text('save'));save.type='submit';form.append(save);
  form.onsubmit=e=>{e.preventDefault();safe(async()=>{await api('/delegation/profiles',Object.fromEntries(Object.entries(fields).map(([k,f])=>[k,f.input.value])));await render();toast(text('saved'))})};
  const toggleApi=()=>{for(const k of ['endpoint','key_env'])fields[k].wrap.hidden=fields.transport.input.value!=='api'};
  fields.transport.input.onchange=toggleApi;toggleApi();settings.append(form);
  const grid=el('div',undefined,'delegation-profiles');
  const marks={chatgpt:'✳',claude:'✺',deepseek:'D',google:'G',gemini:'G',ollama:'◉',custom:'◇'};
  for(const p of profiles){
   const card=el('article',undefined,'ai-connector-card'),head=el('div',undefined,'ai-connector-head');
   const mark=el('span',marks[p.provider]||p.provider.slice(0,2).toUpperCase(),'ai-connector-mark '+(['chatgpt','claude','deepseek'].includes(p.provider)?p.provider:'custom'));mark.setAttribute('aria-hidden','true');
   head.append(mark,el('h3',p.name));card.append(head,el('small',p.provider+' · '+p.transport.toUpperCase()),el('div',p.model||text('external_model'),'delegation-model'),el('span',text('not_verified'),'delegation-connection-state'));
   card.append(button(text('edit'),()=>{for(const [k,f] of Object.entries(fields))f.input.value=p[k]||'';toggleApi();settings.open=true;fields.name.input.focus()}));grid.append(card);
  }
  body.append(grid,settings);
  if(!selected){body.append(el('p',text('empty')));return}
  const start=el('form',undefined,'delegation-form'),objective=field('objective','textarea'),director=field('director','select');
  options(director.input,profiles.map(p=>[p.id,p.name]));objective.input.required=true;
  const submit=el('button',text('start'));submit.type='submit';submit.disabled=!profiles.length;
  start.append(objective.wrap,director.wrap,submit);start.onsubmit=e=>{e.preventDefault();safe(async()=>{await api('/delegation/runs',{chat_id:selected,request_id:crypto.randomUUID(),objective:objective.input.value,director_id:director.input.value});await render()})};body.append(start);
  const runs=(await api('/delegation/runs?chat_id='+encodeURIComponent(selected))).items;
  for(const run of runs){
   const card=el('article',undefined,'delegation-card');card.append(el('h3',run.objective),el('p',text(run.state)+' · '+text('director')+': '+run.director.name));
   for(const w of run.workers){
    const row=el('section',undefined,'delegation-worker');row.append(el('strong',w.profile.name+' · '+text(w.state)),el('p',w.instruction));
    if(w.result){const result=el('pre',w.result);result.className='delegation-result';row.append(result)}
    if(w.state==='waiting_review'){
     const feedback=field('feedback','textarea');row.append(feedback.wrap);
     for(const [decision,label] of [['approved','approve'],['changes_requested','changes']])row.append(button(text(label),async()=>{await api('/delegation/runs/'+run.id,{revision:run.revision,action:'review',payload:{worker_id:w.id,decision,feedback:feedback.input.value}});await render()}));
    }card.append(row);
   }
   if(['waiting_director','working','waiting_review'].includes(run.state)){
    const assign=el('form',undefined,'delegation-form'),worker=field('worker','select'),instruction=field('instruction','textarea');options(worker.input,profiles.map(p=>[p.id,p.name]));instruction.input.required=true;
    const add=el('button',text('assign'));add.type='submit';assign.append(worker.wrap,instruction.wrap,add);assign.onsubmit=e=>{e.preventDefault();safe(async()=>{await api('/delegation/runs/'+run.id,{revision:run.revision,action:'assign',payload:{worker:{id:worker.input.value},instruction:instruction.input.value}});await render()})};card.append(assign);
    const runButton=button(text('workers'),async()=>{runButton.disabled=true;runButton.classList.add('delegation-busy');try{await api('/delegation/runs/'+run.id+'/workers',{});await render()}finally{runButton.disabled=false;runButton.classList.remove('delegation-busy')}});card.append(runButton);
   }
   const details=el('details');details.append(el('summary',text('details')),el('pre',JSON.stringify(run,null,2)));card.append(details);body.append(card);
  }
 }
 const nav=button('Work delegation',async()=>{
  if(!dialog){labels=await api('/delegation/labels');catalog=await api('/delegation/catalog');nav.textContent=text('title');dialog=el('dialog',undefined,'delegation-dialog');dialog.dir='rtl';body=el('div');const head=el('header');head.append(el('h2',text('title')),button(text('refresh'),render),button(text('close'),()=>dialog.close()));dialog.append(head,el('p',text('notice')),body);document.body.append(dialog)}
  dialog.showModal();await render();
 });nav.id='delegation-nav';(document.querySelector('.sidebar-extra')||$('new-chat').parentElement).append(nav);
 safe(async()=>{labels=await api('/delegation/labels');nav.textContent=text('title')});
})();
