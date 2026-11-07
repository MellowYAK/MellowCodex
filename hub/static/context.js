/* Shared authenticated API; every label comes from the locale catalog. */
(async()=>{
  const lang=document.documentElement.lang?.split('-')[0]||'he';
  const strings=await api('/context/catalog/'+(['he','ru','en'].includes(lang)?lang:'en'));
  const t=k=>strings['context.'+k];
  const dialog=el('dialog');dialog.className='context-dialog';
  const title=el('h2',t('title')),output=el('pre'),results=el('div');
  const query=el('input');query.placeholder=t('search');query.setAttribute('aria-label',t('search'));
  let target=null,pendingMap=false;
  const call=(op,body={})=>api('/context/'+op,{project_id:target,...body});
  const details=el('details');details.append(el('summary',t('details')),output);
  const view=el('div');
  const show=data=>{
    output.textContent=JSON.stringify(data,null,2);view.replaceChildren();
    if(data.text!==undefined){view.append(el('h3',data.path),el('pre',data.text));if(data.next_line)view.append(button(t('more_source'),async()=>show(await call('expand',{ref:data.ref,start:data.next_line}))));return}
    if(data.project)view.append(el('h3',data.project.name),el('p',data.project.path));
    if(data.index){
      view.append(el('p',t('revision')+': '+data.index.revision),el('p',new Date(data.index.updated*1000).toLocaleString()));
      const counts=typeof data.index.counts==='string'?JSON.parse(data.index.counts):data.index.counts;
      if(counts){
        const summary=el('dl');summary.className='context-index-summary';
        for(const key of ['indexed','unchanged','changed','deleted','skipped'])if(Number.isInteger(counts[key])){
          summary.append(el('dt',t('count_'+key)),el('dd',String(counts[key])));
        }
        view.append(summary,el('p',t('hash_cache_note')));
      }
    }
    for(const row of data.capsules||[])view.append(button(row.path,async()=>show(await call('expand',{ref:row.ref}))),button(t('related'),async()=>show(await call('related',{ref:row.ref}))));
    if(!data.capsules)for(const path of data.paths||[])view.append(el('div',path));
    if(data.next_offset!=null&&data.project)view.append(button(t('next_page'),async()=>show(await call('overview',{offset:data.next_offset}))));
    for(const row of data.results||[])view.append(el('h3',row.path),el('p',row.excerpt));
    for(const row of data.related||[])view.append(button(row.path+' · '+row.kind,async()=>show(await call('expand',{ref:row.ref}))),el('p',row.confidence));
    for(const row of data.required_constraints||[])view.append(el('p',row.path+': '+row.must_not_break.join(' · ')));
    if(data.saved)view.append(el('p',t('saved')));
  };
  const mode=el('select');mode.setAttribute('aria-label',t('mode'));
  for(const value of ['fast','apc_baseline']){const option=el('option',t('mode_'+value));option.value=value;mode.append(option)}
  const modeLabel=el('label',t('mode'));modeLabel.append(mode);
  mode.onchange=()=>safe(async()=>{await api('/project-index/settings',{project_id:target,enabled:background.checked,mode:mode.value});pendingMap=true;await status();show(await call('overview'))});
  const job=el('p'),background=el('input');background.type='checkbox';
  const backgroundLabel=el('label',t('background'));backgroundLabel.append(background);
  const status=async()=>{const d=await api('/project-index/'+target);job.textContent=(t('state_'+d.state)||d.state)+(d.result?.error?' · '+d.result.error:'');background.checked=!!d.enabled;mode.value=d.mode||'apc_baseline';if(pendingMap&&d.state==='ready'){pendingMap=false;show(await call('overview'))}};
  background.onchange=()=>safe(async()=>{await api('/project-index/settings',{project_id:target,enabled:background.checked});await status()});
  setInterval(()=>{if(dialog.open)safe(status)},2000);
  const field=(name,multiline=false)=>{const label=el('label',t(name)),input=el(multiline?'textarea':'input');label.append(input);return {label,input}};
  const path=field('path'),aliases=field('aliases',true),tags=field('tags',true),notes=field('notes',true),constraints=field('constraints',true);
  const lines=input=>input.value.split('\n').map(x=>x.trim()).filter(Boolean);
  const search=button(t('query'),async()=>{
    const data=await call('search',{query:query.value});show(data);results.replaceChildren();
    for(const row of data.results){const item=el('div');item.append(button(row.path,async()=>{path.input.value=row.path;show(await call('expand',{ref:row.ref,start:row.suggested_start||1}))}),button(t('related'),async()=>show(await call('related',{ref:row.ref}))));results.append(item)}
  });
  query.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();search.click()}});
  dialog.append(title,query,search,button(t('refresh'),async()=>{await call('refresh');pendingMap=true;await status()}),button(t('recovery'),async()=>show(await call('recovery'))),job,backgroundLabel,modeLabel,results,view,details,
    path.label,aliases.label,tags.label,notes.label,constraints.label,
    button(t('save'),async()=>show(await call('annotate',{path:path.input.value,aliases:lines(aliases.input),tags:lines(tags.input),notes:notes.input.value,must_not_break:lines(constraints.input)}))),
    button(t('close'),()=>dialog.close()));
  document.body.append(dialog);
  const open=button(t('title'),async()=>{if(!project)throw Error(t('project'));target=project;show(await call('overview'));await status();dialog.showModal()});
  open.className='context-open';open.textContent=t('open_map');$('project-select').parentElement.append(open);
})().catch(e=>toast(e.message));
