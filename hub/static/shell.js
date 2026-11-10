/* Hub-native product shell; existing controls retain their handlers and IDs. */
(()=>{
 bridgePhases.opening_conversation='פותח שיחת ChatGPT חדשה וממתין לטעינת הדפדפן';bridgePhases.connection_attention='הקמת החיבור דורשת בדיקה';
 document.querySelector('.brand b').textContent='MellowCodex';
 document.querySelector('.brand').firstChild.textContent='';
 $('new-chat').textContent='＋ שיחה חדשה';$('chatgpt-bridge').textContent='חיבור ל־ChatGPT';$('schedules').textContent='משימות מתוזמנות';
 const sectionLabels=document.querySelectorAll('#sidebar > .section');if(sectionLabels[0])sectionLabels[0].firstChild.textContent='פרויקטים';if(sectionLabels[1])sectionLabels[1].firstChild.textContent='שיחות';
 const actions=document.querySelector('.header-actions');
 const overflow=el('details',undefined,'toolbar-menu'),toggle=el('summary','•••');toggle.setAttribute('aria-label','אפשרויות שיחה וכלים');overflow.append(toggle);const menu=el('div',undefined,'menu-popover');
 for(const id of ['rename','pin','archive','files-toggle','library-toggle','git-toggle','terminal-toggle']){const b=$(id);const titles={rename:'שינוי שם השיחה',pin:'נעיצה',archive:'העבר לארכיון','files-toggle':'קבצי הפרויקט','library-toggle':'הורדות וקבצים','git-toggle':'שינויים בקוד','terminal-toggle':'טרמינל'};b.textContent=titles[id];b.addEventListener('click',()=>overflow.open=false);menu.append(b)}
 menu.append(button('זיכרון והיסטוריית שיחה',()=>{overflow.open=false;window.openContinuity()}));overflow.append(menu);actions.prepend(overflow);
 $('browser-toggle').textContent='דפדפן';$('stop').textContent='עצור';$('stop').classList.add('stop-button');
 document.addEventListener('click',e=>{if(!overflow.contains(e.target))overflow.open=false});
 // One settings surface with focused categories instead of a long form.
 const settings=$('settings-dialog'),children=[...settings.children];
 const close=$('settings-close');close.textContent='סגור';close.className='settings-dismiss';
 const head=el('div',undefined,'settings-heading');head.append(el('h2','הגדרות'),close);
 const layout=el('div',undefined,'settings-layout'),nav=el('nav',undefined,'settings-nav'),content=el('div',undefined,'settings-pages');nav.setAttribute('aria-label','קטגוריות הגדרות');
 const pages=new Map();let first=true;
 function page(key,title){const panel=el('section',undefined,'settings-page');panel.hidden=!first;panel.dataset.page=key;panel.append(el('h2',title));const b=button(title,()=>{for(const p of pages.values())p.panel.hidden=true;for(const p of pages.values())p.button.classList.remove('active');panel.hidden=false;b.classList.add('active')});if(first)b.classList.add('active');first=false;nav.append(b);content.append(panel);pages.set(key,{panel,button:b});return panel}
 const general=page('general','כללי'),models=page('models','מודלים ומשאבים'),visual=page('visual','צילום וניתוח מסך'),connection=page('connections','חיבורים'),projectPage=page('project','פרויקט והקשר');
 safe(async()=>{const labels=await api('/lifecycle/labels');const shutdown=button(labels.shutdown,async()=>{shutdown.disabled=true;try{const impact=await api('/service-health');const count=impact.active_tasks===null?'unknown':impact.active_tasks.length;if(!confirm('Stop all agent services and active tasks ('+count+')? MCP will disconnect. Rescue window and OwnerBroker remain available.')){shutdown.disabled=false;return}await api('/lifecycle/shutdown',{confirm_tasks:true,request_id:crypto.randomUUID()});shutdown.textContent=labels.stopping;const timer=setInterval(async()=>{try{const state=await api('/lifecycle/status');if(state.state==='failed'){clearInterval(timer);shutdown.disabled=false;shutdown.textContent=labels.shutdown;toast(state.errors.map(e=>e.stage+': '+e.error).join('\n'))}}catch(e){clearInterval(timer)}},1000)}catch(e){shutdown.disabled=false;throw e}});shutdown.classList.add('stop-button');general.append(shutdown)});
 for(const node of children){if(node===close||node.tagName==='H2')continue;if(node.tagName==='SECTION'){const h=node.querySelector('h3')?.textContent||'';(node.classList.contains('model-settings')?models:h.includes('דחיסת')?visual:connection).append(node)}else if(node.contains($('project-notes'))||['save-notes','worktree'].includes(node.id))projectPage.append(node);else general.append(node)}
 projectPage.append(button('פתח את זיכרון השיחה',()=>{settings.close();window.openContinuity()}));
 const ext=page('extensions','Skill Shops · סקילים והרחבות');
 const description=el('p','קטלוג סקילים מותקנים. רישום או hash תקין אינם הוכחת פעולה מלאה.');ext.append(description);
 const filterBar=el('div');filterBar.style.cssText='display:flex;flex-wrap:wrap;gap:8px;margin:12px 0';
 const search=el('input');search.type='search';search.placeholder='חיפוש סקיל או יכולת';search.setAttribute('aria-label','חיפוש סקילים');
 const category=el('select');category.setAttribute('aria-label','סינון קטגוריה');
 const status=el('select');status.setAttribute('aria-label','סינון אימות');
 for(const [key,title] of [['all','כל הסטטוסים'],['live','בוצעה בדיקה חיה'],['limited','חלקי או לא מאומת']]){const o=el('option',title);o.value=key;status.append(o)}
 const reload=button('רענון',()=>safe(loadShop));filterBar.append(search,category,status,reload);ext.append(filterBar);
 const metrics=el('p','טוען קטלוג...'),results=el('div');results.style.cssText='display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:12px';
 const notice=el('p','התקנה והסרה דורשות אישור OwnerBroker מוגן.');const availablePanel=el('div');ext.append(metrics,results,notice,availablePanel);
 let catalog=null;
 const isLive=v=>v.startsWith('live_')||v.startsWith('real_');
 const skillIconPaths={"form":"M5 3h14v18H5z M8 7h8 M8 11h2 M13 11h3 M8 15h2 M13 15h3","cloud":"M6 18a4 4 0 0 1-1-8 7 7 0 0 1 13-2 5 5 0 0 1 0 10H6 M9 13l3-3 3 3 M12 10v10","sheet":"M4 3h16v18H4z M4 8h16 M4 13h16 M4 17h16 M10 8v13","search":"M4 3h10l4 4v5 M4 3v18h7 M14 4v4h4 M14 14a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M17 21l4 2","folder":"M3 7V4h7l2 3h9v13H3z M8 13h8 M13 10l3 3-3 3","workspace":"M3 4h18v13H3z M3 8h18 M9 17v4 M15 17v4 M7 21h10","image":"M3 3h18v18H3z M3 17l6-6 4 4 3-3 5 5 M15 6h2v2h-2z","network":"M9 3h6v5H9z M3 16h6v5H3z M15 16h6v5h-6z M12 8v4 M6 16v-4h12v4","pdf":"M5 3h9l5 5v13H5z M14 3v5h5 M8 12h8 M8 16h6","folder-search":"M3 7V4h7l2 3h9v6 M3 7v13h8 M15 13a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M18 20l3 3","browser":"M3 3h18v18H3z M3 8h18 M7 5h1 M10 5h1 M9 12l-3 3 3 3 M15 12l3 3-3 3","file-lock":"M4 3h10l4 4v4 M4 3v18h6 M14 3v5h4 M13 16h8v6h-8z M15 16v-3h4v3","download":"M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5","cloud-lock":"M6 17a4 4 0 0 1-1-8 7 7 0 0 1 13-2 5 5 0 0 1 2 8 M10 16h8v6h-8z M12 16v-3h4v3","shield":"M12 2l8 4v6c0 5-8 10-8 10S4 17 4 12V6z M8 12l3 3 5-6","package":"M3 7l9-5 9 5v10l-9 5-9-5z M3 7l9 5 9-5 M12 12v10 M7 5l9 5","audit":"M6 4h12v18H6z M9 2h6v4H9z M9 10l1 1 2-2 M14 10h2 M9 16l1 1 2-2 M14 16h2","monitor":"M3 3h18v14H3z M8 21h8 M12 17v4 M6 12l3-4 3 5 3-6 3 3","chart":"M4 3v18h17 M8 17v-5 M13 17V7 M18 17V4","app":"M3 3h18v18H3z M3 8h18 M10 11l6 4-6 4z","inspect":"M3 3h18v10 M3 3v17h7 M3 8h18 M15 13a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M18 20l3 3","settings":"M4 5h16 M4 12h16 M4 19h16 M8 2v6 M16 9v6 M10 16v6","archive":"M4 3h16v18H4z M10 3v3h4v3h-4v3h4v3h-4v3h4v3"};
 const skillIconColors={form:'#2563eb',cloud:'#0284c7',sheet:'#15803d',search:'#7c3aed',folder:'#b45309',workspace:'#0891b2',image:'#db2777',network:'#0f766e',pdf:'#dc2626','folder-search':'#c2410c',browser:'#2563eb','file-lock':'#7c3aed',download:'#059669','cloud-lock':'#4f46e5',shield:'#0f766e',package:'#b45309',audit:'#9333ea',monitor:'#0284c7',chart:'#16a34a',app:'#6366f1',inspect:'#c026d3',settings:'#475569',archive:'#ca8a04'};
 function skillIcon(key,image){
   if(image&&/^data:image\/(png|svg\+xml);base64,/.test(image)){
     const img=el('img');img.className='skill-icon';img.width=44;img.height=44;img.alt='';img.style.cssText='flex:0 0 44px;object-fit:contain;border-radius:10px';
     img.onerror=()=>img.replaceWith(skillIcon(key));img.src=image;return img;
   }
   const color=skillIconColors[key]||skillIconColors.package;
   const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
   for(const [name,value] of Object.entries({viewBox:'-4 -4 32 32',width:'44',height:'44',fill:'none',stroke:color,'stroke-width':'1.6','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true',focusable:'false'}))svg.setAttribute(name,value);
   svg.style.cssText='flex:0 0 44px';svg.classList.add('skill-icon');
   const tile=document.createElementNS('http://www.w3.org/2000/svg','rect');
   for(const [k,v] of Object.entries({x:'-4',y:'-4',width:'32',height:'32',rx:'8',fill:color+'18',stroke:'none'}))tile.setAttribute(k,v);
   const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',skillIconPaths[key]||skillIconPaths.package);
   const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');dot.setAttribute('cx','22');dot.setAttribute('cy','1');dot.setAttribute('r','2');dot.setAttribute('fill','#fbbf24');dot.setAttribute('stroke','none');
   svg.append(tile,path,dot);return svg;
 }
 function iconControls(s,heading){
   const controls=el('div');controls.style.cssText='display:flex;gap:8px;flex-wrap:wrap;margin-top:10px';
   const file=el('input');file.type='file';file.accept='.png,.jpg,.jpeg,.webp,.gif,.ico,.svg';file.hidden=true;
   const choose=button('שינוי אייקון',()=>{file.value='';file.click()});choose.classList.add('skill-icon-choose');
   const reset=button('אייקון מקורי',()=>safe(()=>saveIcon(null,true)));reset.disabled=!s.icon_image;reset.classList.add('skill-icon-reset');
   async function saveIcon(data_uri,restore=false){
     choose.disabled=true;reset.disabled=true;
     try{
       const saved=await api('/settings/skill-icons',{name:s.name,data_uri,reset:restore});
       s.icon_image=saved.icon_image;heading.querySelector('.skill-icon').replaceWith(skillIcon(s.icon,s.icon_image));toast('האייקון נשמר');
     }finally{choose.disabled=false;reset.disabled=!s.icon_image}
   }
   file.addEventListener('change',()=>safe(async()=>{
     const chosen=file.files[0];if(!chosen)return;
     if(chosen.size>512*1024)throw Error('בחר תמונה עד 512 KB');
     let uri=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(Error('לא ניתן לקרוא את התמונה'));r.readAsDataURL(chosen)});
     const ext=chosen.name.split('.').pop().toLowerCase(),mime={png:'png',jpg:'jpeg',jpeg:'jpeg',webp:'webp',gif:'gif',ico:'x-icon',svg:'svg+xml'}[ext];
     if(!mime)throw Error('בחר PNG, JPG, WebP, GIF, ICO או SVG');
     uri='data:image/'+mime+';base64,'+uri.split(',')[1];await saveIcon(uri);
   }));
   controls.append(choose,reset,file);return controls;
 }
 function drawShop(){
   if(!catalog)return;const q=search.value.trim().toLocaleLowerCase(),cat=category.value,st=status.value;
   const skills=catalog.skills.filter(s=>(cat==='all'||s.categories.includes(cat))&&(!q||[s.name,s.title,s.description,...s.capabilities.map(c=>c.id)].join(' ').toLocaleLowerCase().includes(q))&&
     (st==='all'||s.capabilities.some(c=>st==='live'?isLive(c.verification):!isLive(c.verification))));
   metrics.textContent=catalog.installed_skills+' חבילות · '+catalog.mapped_capabilities+'/'+catalog.original_goal+' יכולות ממופות · '+catalog.fully_verified+' אימותים מלאים';
   results.replaceChildren(...skills.map(s=>{
     const card=el('article');card.style.cssText='border:1px solid #9996;border-radius:10px;padding:12px;min-width:0';
     card.dataset.skill=s.name;
     const heading=el('div');heading.style.cssText='display:flex;align-items:center;gap:12px;min-height:48px';
     const title=el('h3',s.title);title.style.margin='0';heading.append(skillIcon(s.icon,s.icon_image),title);
     card.append(heading,el('p',s.description),el('p','יכולות: '+s.capabilities.length+' · '+(s.integrity_verified?'Hash תקין':'Hash לא אומת')));
     const detail=el('details');detail.append(el('summary','פירוט יכולות ומגבלות'));
     for(const c of s.capabilities)detail.append(el('p',c.id+' · '+c.verification));
     for(const limit of s.limitations)detail.append(el('p','מגבלה: '+limit));
     card.append(iconControls(s,heading),detail,button('בקשת הסרה',()=>safe(()=>shopAction('remove',s.name))));return card;
   }));
   if(!skills.length)results.append(el('p','לא נמצאו סקילים מתאימים.'));
 }
 async function shopAction(action,slug){
   if(!selected){toast('בחר שיחה לפני ניהול סקילים');return;}
   const preview=await api('/skill-shops/preview',{action,slug,chat_id:selected});
   const summary={install:'התקנה',update:'עדכון',remove:'הסרה'}[action]||action;
   if(!window.confirm('בקשת '+summary+' עבור '+slug+'\nSHA256: '+preview.digest+'\nהפעולה תריץ קוד Python בהרשאות המשתמש, בכפוף למדיניות הבעלים של השיחה. להמשיך?'))return;
   const result=await api('/skill-shops/commit',{action,slug,expected_digest:preview.digest,chat_id:selected});
   const labels={installed:'הסקיל הותקן',updated:'הסקיל עודכן',removed_to_quarantine:'הסקיל הוסר ונשמר גיבוי',blocked_in_use:'המתן לסיום המשימות הפעילות',blocked_coverage:'הסקיל נדרש לכיסוי היכולות ולא ניתן להסירו',validation_failed:'בדיקת הסקיל נכשלה; הגרסה הקודמת נשמרה',needs_owner:'נדרש אישור בחלון הרשאות הבעלים. לאחר האישור, נסה שוב'};
   toast(labels[result.status]||result.status);
   await loadShop();
 }
 function showAvailable(packages){
   availablePanel.replaceChildren(el('h3','חבילות מקומיות זמינות'));
   for(const source of packages){
     const line=el('div');line.style.cssText='display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #9993';
     const label=el('span',source.slug+' · '+source.source_sha256.slice(0,12));
     const action=source.installed?'update':'install';
     const installed=catalog?.skills.find(s=>s.name===source.slug.replaceAll('-','_'));
     line.append(skillIcon(installed?.icon||'package',installed?.icon_image),label,button(source.installed?'בקשת עדכון':'בקשת התקנה',()=>safe(()=>shopAction(action,source.slug))));
     availablePanel.append(line);
   }
   if(!packages.length)availablePanel.append(el('p','אין כרגע חבילות מקומיות מוכנות להתקנה.'));
 }
 async function loadShop(){
   const [currentCatalog,sourceInfo]=await Promise.all([api('/skill-shops'),api('/skill-shops/available')]);
   catalog=currentCatalog;notice.textContent=catalog.permission_note;
   const current=category.value,cats=['all',...new Set(catalog.skills.flatMap(s=>s.categories))];
   category.replaceChildren(...cats.map(c=>{const o=el('option',c==='all'?'כל הקטגוריות':c);o.value=c;return o}));
   category.value=cats.includes(current)?current:'all';drawShop();showAvailable(sourceInfo.packages||[]);
 }
 search.addEventListener('input',drawShop);category.addEventListener('change',drawShop);status.addEventListener('change',drawShop);
 pages.get('extensions').button.addEventListener('click',()=>safe(loadShop));
 const rag=page('knowledge','ידע ו־RAG');rag.append(el('p','מפת הפרויקט והחיפוש בקוד פועלים מקומית. הם נפרדים מזיכרון השיחה הכרונולוגי.'),button('פתח מפת פרויקט וחיפוש',()=>{settings.close();document.querySelector('.context-open')?.click()}));
 layout.append(nav,content);settings.replaceChildren(head,layout);
 const plugins=button('פלאגינים וסקילים',()=>{settings.showModal();pages.get('extensions').button.click()});plugins.id='extensions-nav';$('schedules').after(plugins);
 window.showSettingsPage=key=>{settings.showModal();pages.get(key)?.button.click()};
 // Transport choices open the existing operational flows; no second dispatcher.
 const chatConnection=$('chatgpt-dialog'),existing=[...chatConnection.children];
 const playPanel=el('section',undefined,'connection-play'),mcpPanel=el('section',undefined,'connection-mcp');
 mcpPanel.hidden=true;
 for(const node of existing){if(node.id!=='gpt-close'&&node.tagName!=='H2')playPanel.append(node)}
 const choices=el('div',undefined,'browser-control');choices.setAttribute('aria-label','מסלול חיבור ChatGPT');
 const playChoice=button('PLAY · דפדפן',()=>{transportSelect.value='play';chooseTransport('play')});
 const mcpChoice=button('MCP · פלאגין',()=>{transportSelect.value='mcp';chooseTransport('mcp')});
 const mcpStatus=el('p','בדיקת חיבור MCP מתבצעת בבחירת המסלול');mcpStatus.setAttribute('role','status');
 function chooseTransport(mode){playPanel.hidden=mode!=='play';mcpPanel.hidden=mode!=='mcp';playChoice.setAttribute('aria-pressed',String(mode==='play'));mcpChoice.setAttribute('aria-pressed',String(mode==='mcp'));if(mode==='mcp')safe(async()=>{const d=await api('/remote/status');mcpStatus.textContent='מצב שער MCP: '+d.status.state+' · '+d.url})}
 choices.append(playChoice,mcpChoice);
 mcpPanel.append(el('p','חיבור באמצעות פלאגין MCP בשיחת ChatGPT. כאן ניתן לבדוק את שער החיבור ולאשר בקשות התחברות.'),mcpStatus,
  button('הגדרות ואישור חיבור MCP',()=>{chatConnection.close();window.showSettingsPage('connections');safe(remoteStatus)}));
 playPanel.prepend(el('p','PLAY מחבר שיחת ChatGPT בדפדפן של הסוכן. בחר שיחה קיימת או פתח שיחה, התחבר לחשבון לפי הצורך והפעל PLAY כדי לשלוח את הוראות העבודה.'));
 chatConnection.insertBefore(choices,$('gpt-close'));chatConnection.insertBefore(playPanel,$('gpt-close'));chatConnection.insertBefore(mcpPanel,$('gpt-close'));chooseTransport('play');
 $('gpt-connect').textContent='בחר שיחת דפדפן קיימת';$('gpt-open').textContent='פתח ChatGPT';$('gpt-listen').textContent='הפעל PLAY ושלח הוראות';
 chatConnection.querySelector('h2').textContent='חיבור ChatGPT';
 const newPlay=button('שיחה חדשה והפעל PLAY',async()=>{if(!project)throw Error('בחר תיקיית פרויקט תחילה');newPlay.disabled=true;try{const result=await api('/chatgpt/new-conversation',{project_id:project,max_steps:Number($('gpt-max').value)});await select(result.chat_id);await gptStatus();await loadConnection()}finally{newPlay.disabled=false}});
 $('gpt-open').before(newPlay);
 const drafts=el('details'),draftTitle=el('summary','טיוטות שמורות ושחזור'),draftList=el('div');
 async function loadDrafts(){if(!selected)throw Error('בחר שיחה מקומית');const result=await api('/chatgpt/drafts',{chat_id:selected,action:'list'});draftList.replaceChildren(...result.items.map(d=>button('שחזר טיוטה · '+d.characters+' תווים · '+new Date(d.created*1000).toLocaleString(),async()=>{const r=await api('/chatgpt/drafts',{chat_id:selected,action:'restore',draft_id:d.id});toast(r.verified?'הטיוטה שוחזרה; לא נשלחה':'השחזור דורש בדיקה; העותק השמור נשמר')})))}
 drafts.append(draftTitle,el('p','שמירת הטיוטה במחשב לפני פינוי שדה ההקלדה. לא נשלחת הודעה. עצור PLAY תחילה.'),button('שמור טיוטה ופנה את השדה',async()=>{if(!selected)throw Error('בחר שיחה מקומית');const r=await api('/chatgpt/drafts',{chat_id:selected,action:'archive'});toast(r.verified?'הטיוטה נשמרה והשדה פונה':r.reason||'עותק נשמר; יש לבדוק את השדה');await loadDrafts()}),button('הצג טיוטות שמורות',loadDrafts),draftList);playPanel.append(drafts);
 const advanced=el('details'),advancedTitle=el('summary','התייעצות ומשימה אוטומטית');advanced.append(advancedTitle);$('gpt-stop').before(advanced);advanced.append($('gpt-question-form'),$('gpt-answer'),$('gpt-objective-form'));
 const savedConnection=el('section',undefined,'saved-connection');
 const connectionUrl=el('input');connectionUrl.type='url';connectionUrl.dir='ltr';connectionUrl.placeholder='https://chatgpt.com/c/…';connectionUrl.setAttribute('aria-label','כתובת שיחת ChatGPT מקושרת');
 const transportSelect=el('select');transportSelect.setAttribute('aria-label','מסלול שמור לשיחה');
 transportSelect.onchange=()=>chooseTransport(transportSelect.value);
 for(const [value,title] of [['play','PLAY · דפדפן'],['mcp','MCP · פלאגין']]){const option=el('option',title);option.value=value;transportSelect.append(option)}
 const favorite=el('input');favorite.type='checkbox';const favoriteLabel=el('label','שיחה מועדפת');favoriteLabel.prepend(favorite);
 const connectionInfo=el('p');connectionInfo.setAttribute('role','status');
 const favorites=el('div',undefined,'connection-favorites');
 async function loadConnection(){
  connectionUrl.value='';favorite.checked=false;connectionInfo.textContent=selected?'טוען קישור שמור…':'בחר שיחה מקומית לשמירת קישור';
  if(selected){const c=await api('/chats/'+selected+'/connection');connectionUrl.value=c.url||'';favorite.checked=c.favorite;transportSelect.value=c.transport;chooseTransport(c.transport);connectionInfo.textContent='ההעדפה שמורה לשיחה זו. חיבור בפועל מופעל בנפרד.'}
  const f=await api('/chatgpt/favorites');favorites.replaceChildren(...f.items.map(c=>button('★ '+c.title+' · '+c.transport.toUpperCase(),()=>safe(async()=>{await select(c.chat_id);await loadConnection()}))));
 }
 savedConnection.append(el('h3','השיחה המקושרת'),connectionUrl,transportSelect,favoriteLabel,
  button('שמור קישור והעדפות',()=>safe(async()=>{if(!selected){if(!project)throw Error('בחר תיקיית פרויקט תחילה');const created=await api('/chats',{project_id:project});await select(created.id)}const body={transport:transportSelect.value,favorite:favorite.checked};if(connectionUrl.value.trim())body.url=connectionUrl.value.trim();await api('/chats/'+selected+'/connection',body);await loadConnection();connectionInfo.textContent='נשמר. ההעדפה תופעל בחיבור הבא; טרם בוצעה התחברות.'})),connectionInfo,el('h3','שיחות מועדפות'),favorites);
 chatConnection.insertBefore(savedConnection,$('gpt-close'));
 $('chatgpt-bridge').addEventListener('click',()=>safe(loadConnection));
 window.restoreChatConnection=async id=>{const c=await api('/chats/'+id+'/connection');if(c.url&&c.transport==='play'){await api('/chatgpt/context',{chat_id:id})}};
 const connectorDialog=el('dialog',undefined,'ai-connectors-dialog');connectorDialog.dir='rtl';
 const connectorHead=el('div',undefined,'settings-heading');connectorHead.append(el('h2','חיבורי AI'),button('סגור',()=>connectorDialog.close()));
 const connectorCards=el('div',undefined,'ai-connector-grid');
 connectorDialog.append(connectorHead,el('p','בחר שירות, ואז בחר חיבור MCP או Web PLAY דרך שיחה בדפדפן.'),connectorCards);document.body.append(connectorDialog);
 const openChatGPT=$('chatgpt-bridge').onclick;
 const connectorNav=button('חיבורי AI',async()=>{connectorDialog.showModal();connectorCards.replaceChildren(el('p','טוען חיבורים…'));const data=await api('/ai-connectors');connectorCards.replaceChildren(...data.items.map(provider=>{
  const card=el('article',undefined,'ai-connector-card'),head=el('div',undefined,'ai-connector-head'),mark=el('span',provider.mark,'ai-connector-mark '+provider.id);mark.setAttribute('aria-hidden','true');head.append(mark,el('h3',provider.name));card.append(head,el('p',provider.description));
  const methods=el('div',undefined,'ai-connector-methods');for(const route of provider.transports){const b=button(route.name,async()=>{connectorDialog.close();if(route.id==='mcp'){const d=el('dialog',undefined,'ai-connectors-dialog');d.dir='rtl';const labels=data.mcp.labels;const url=el('input');url.value=data.mcp.url;url.readOnly=true;url.dir='ltr';url.style.width='100%';url.onclick=()=>url.select();d.append(el('h2',provider.name+' · '+labels.setup),el('p',labels.instructions),url,el('p',route.requires),el('p',labels.status_note),button(labels.approve,()=>{d.close();window.showSettingsPage('connections');safe(remoteStatus)}),button('×',()=>d.close()));document.body.append(d);d.addEventListener('close',()=>d.remove());d.showModal();return}await openChatGPT();chooseTransport(route.id);transportSelect.value=route.id});b.disabled=!route.implemented;b.title=route.requires;methods.append(b)}card.append(methods,el('small',provider.connection_state==='not_implemented'?'בפיתוח · עדיין לא ניתן לחבר':'נדרשת התחברות · בחירת מסלול אינה מחברת אוטומטית'));return card}));});
 connectorNav.id='ai-connectors-nav';$('chatgpt-bridge').before(connectorNav);
 for(const d of document.querySelectorAll('dialog')){d.addEventListener('click',e=>{if(e.target!==d)return;const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close()})}
})();

/* Presentation only: every state and piece of evidence comes from the task API. */
(()=>{
 const activity=new Map(),openEvidence=new Set(),activityReceived=new Map();
 const tools={run_shell:'מריץ פקודה',read_file:'קורא קובץ',write_file:'כותב קובץ',browser_observe:'בודק את הדף',browser_tabs:'בודק לשוניות',context_search:'מחפש בקוד',context_expand:'קורא את המקור',project_context:'קורא את מפת הפרויקט',chatgpt_ask:'ממתין למשוב מהמנחה',candidate_patch:'מעדכן את הקוד',candidate_repair:'מכין תיקון קוד'};
 const states={queued:'המשימה התקבלה',running:'מבצע את המשימה',verifying:'בודק את התוצאה',waiting_review:'ממתין לבדיקת התוצאה',waiting_user:'נדרשת תשובה כדי להמשיך',waiting_desktop:'ממתין לשולחן עבודה זמין',paused:'המשימה מושהית',cancelled:'המשימה בוטלה',failed:'המשימה נכשלה',done:'המשימה הושלמה'};
 const phase={model_inference:'ממתין לתשובת המודל',tool_execution:'ממתין לסיום הפעולה',planning_next_step:'בודק את התוצאה ומתכנן את הצעד הבא',executor_queue:'ממתין בתור לביצוע',result_review:'ממתין לבדיקת התוצאה'};
 const themeButton=button('☀ / ☾',()=>{$('theme').click();themeButton.setAttribute('aria-pressed',String(document.body.classList.contains('dark')))});themeButton.className='theme-shortcut';themeButton.title='החלף מצב בהיר / כהה';themeButton.setAttribute('aria-label',themeButton.title);document.querySelector('.header-actions').prepend(themeButton);
 const extra=el('details',undefined,'sidebar-extra');extra.append(el('summary','חיבורים וכלים'));$('new-chat').after(extra);for(const id of ['ai-connectors-nav','chatgpt-bridge','schedules','extensions-nav'])if($(id))extra.append($(id));
 const context=el('div',undefined,'flow-context');context.append(el('span','המשך השיחה הנבחרת'),button('＋ משימה בשיחה חדשה',()=>newChat()));$('composer').prepend(context);
 function evidence(task){
  const d=el('details',undefined,'tools');d.open=openEvidence.has(task.id);d.append(el('summary','פרטים טכניים'));const content=el('div');d.append(content);let cursor=0,busy=false,last=0;
  d.refreshEvidence=async()=>{if(!d.open||busy||Date.now()-last<4000)return;busy=true;try{const events=await api('/tasks/'+task.id+'/events');for(const e of events.slice(cursor)){const row=el('details');row.append(el('summary',new Date(e.at).toLocaleTimeString()+' · '+({tool_start:'פעולה התחילה',tool_result:'תוצאת פעולה',model_start:'בקשה למודל',state:'שינוי מצב',review:'בדיקה',unknown_action:'תוצאה לא ודאית'}[e.kind]||e.kind)));row.append(el('pre',JSON.stringify(e.data,null,2)));content.append(row)}cursor=events.length;last=Date.now()}finally{busy=false}};
  d.ontoggle=()=>{d.open?openEvidence.add(task.id):openEvidence.delete(task.id);if(d.open)safe(d.refreshEvidence)};return d;
 }
 function makeCard(task){const card=el('article',undefined,'flow-card');card.dataset.task=task.id;card.taskSnapshot=task;const h=el('h2');h.dataset.flow='heading';const steps=el('ol',undefined,'flow-steps');for(const label of ['התקבלה','בביצוע','בבדיקה','הושלמה']){const li=el('li');li.append(el('span',''),document.createTextNode(label));steps.append(li)}const now=el('div',undefined,'flow-now');now.dataset.flow='now';const next=el('div',undefined,'flow-next');next.dataset.flow='next';card.append(h,steps,now,next,evidence(task));const actions=el('div',undefined,'turn-actions');for(const [label,command,allowed] of [['השהיה','pause',['running','queued','waiting_desktop']],['המשך','resume',['paused','failed','waiting_user']],['עצירה','cancel',['running','queued','paused','waiting_desktop','waiting_user']]])if(allowed.includes(task.state))actions.append(button(label,async()=>{await api('/tasks/'+task.id+'/control',{command,expected_revision:task.revision});signature='';await refresh()}));if(task.state==='waiting_review')actions.append(button('אשר תוצאה לאחר בדיקה',async()=>{await api('/tasks/'+task.id+'/review',{decision:'approve',reason:'התוצאה נבדקה ואושרה',expected_revision:task.revision});signature='';await refresh()}));if(task.mode==='code')actions.append(button('סקירת שינויים',()=>window.openDevelopment(task.id)));card.append(actions,el('small','הפעולות והתוצאות נשמרות ביומן גם כשהפרטים סגורים.'));updateCard(card,task);return card}
 function updateCard(card,task){const item=activity.get(task.id),s=item?.state||task.state,x=item?.execution;card.querySelector('[data-flow=heading]').textContent=states[s]||s;const index=s==='done'?3:['verifying','waiting_review'].includes(s)?2:s==='queued'?0:1;[...card.querySelectorAll('.flow-steps li')].forEach((li,i)=>{li.className=i<index||s==='done'?'complete':i===index?'current':'';li.firstChild.textContent=i<index||s==='done'?'✓':''});const tool=x?.current_action?.tool;card.querySelector('[data-flow=now]').textContent='עכשיו: '+(s==='running'?(tool?(tools[tool]||'מבצע פעולה בכלי'):phase[x?.waiting_for]||states[s]):states[s]||s);card.querySelector('[data-flow=next]').textContent=s==='running'?'הבא: בדיקת תוצאת הפעולה לפני המשך':s==='waiting_review'?'הביצוע הסתיים; ההצלחה עדיין ממתינה לאישור':s==='done'?'המשימה סומנה כהושלמה':s==='queued'?'הביצוע יתחיל כשהסוכן יתפנה':task.result?.split('\n')[0]?.slice(0,220)||'';}

 const statusDialog=el('dialog',undefined,'status-dialog');statusDialog.dir='rtl';
 const statusContent=el('div');const statusHead=el('div',undefined,'status-heading');
 statusHead.append(el('h2','מצב הסוכן'),button('סגור ×',()=>statusDialog.close()));statusDialog.append(statusHead,statusContent);document.body.append(statusDialog);
 const statusButton=button('מצב הסוכן',()=>{statusDialog.showModal();updateLiveness()});statusButton.className='top-status';document.querySelector('.header-actions').prepend(statusButton);
 let latestItems=[],lastUpdate=0;
 function updateTopStatus(){const active=latestItems.filter(x=>['running','queued','verifying'].includes(x.state));const stale=Date.now()-lastUpdate>15000;statusButton.classList.toggle('is-live',active.length>0&&!stale);const current=latestItems.find(x=>x.chat_id===selected)||latestItems[0];statusButton.textContent=stale?'מצב · אין עדכון חי':active.length?'בפעילות · '+active.length:current?(states[current.state]||current.state):'הסוכן פנוי';statusButton.title='לחץ למצב מפורט וליומן הפעולות';}
 const dashboard=el('section',undefined,'home-dashboard');dashboard.dir='rtl';dashboard.hidden=true;$('messages').before(dashboard);
 function showHome(){dashboard.hidden=false;document.body.classList.add('dashboard-open');renderHome();}
 function hideHome(){dashboard.hidden=true;document.body.classList.remove('dashboard-open');}
 const homeButton=button('⌂  דף הבית',showHome);homeButton.className='home-navigation';$('new-chat').before(homeButton);
 const oldSelect=select;select=async function(id){hideHome();return oldSelect(id)};
 const oldNew=newChat;newChat=function(){hideHome();return oldNew()};$('new-chat').onclick=newChat;
 let homeSignature='';function renderHome(){if(dashboard.hidden)return;const nextSignature=JSON.stringify([latestItems.map(i=>[i.task_id,i.state,i.execution?.waiting_for,i.execution?.current_action?.tool]),Date.now()-lastUpdate>15000]);if(nextSignature===homeSignature)return;homeSignature=nextSignature;const active=latestItems.filter(x=>['running','queued','verifying'].includes(x.state));const review=latestItems.filter(x=>['failed','waiting_user','waiting_review','waiting_desktop','paused'].includes(x.state));const finished=latestItems.filter(x=>x.state==='done');
 dashboard.replaceChildren(el('small','MELLOWCODEX · מרכז הפעילות'),el('h1','מה קורה עכשיו?'),el('p',lastUpdate&&Date.now()-lastUpdate<15000?'מתעדכן אוטומטית · הפעולות נשמרות ביומן':'אין עדכון חי כרגע · המידע האחרון נשמר'));
 const metrics=el('div',undefined,'dashboard-metrics');for(const [n,label] of [[active.length,'בפעילות'],[review.length,'דורשות תשומת לב'],[finished.length,'הושלמו']]){const tile=el('div');tile.append(el('strong',String(n)),el('span',label));metrics.append(tile)}dashboard.append(metrics,el('small','הסיכום מתייחס ל־'+latestItems.length+' המשימות האחרונות שהשרת החזיר.'));
 for(const [title,items] of [['פועל עכשיו',active],['דורש טיפול או בדיקה',review],['פעילות אחרונה',latestItems.filter(x=>!active.includes(x)&&!review.includes(x))]]){dashboard.append(el('h2',title));if(!items.length){dashboard.append(el('p','אין משימות בקבוצה זו','dashboard-empty'));continue}for(const item of items){const row=el('article',undefined,'dashboard-row');const text=el('div');text.append(el('strong',item.goal||'משימה'),el('p',(states[item.state]||item.state)+' · '+(phase[item.execution?.waiting_for]||item.execution?.current_action?.tool||'')));row.append(text,button('פרטים',async()=>{const task=await api('/tasks/'+item.task_id);statusContent.replaceChildren(makeCard(task));statusDialog.showModal();updateLiveness()}));if(item.chat_id)row.append(button('פתח שיחה',()=>select(item.chat_id)));dashboard.append(row)}}}
 window.addEventListener('task-activity',event=>{latestItems=event.detail.items;lastUpdate=Date.now();updateTopStatus();renderHome()});
 setInterval(()=>{updateTopStatus();if(Date.now()-lastUpdate>15000)renderHome()},2000);
 const original=renderTurns;
 function message(text,kind,label){const box=el('div',undefined,'message '+kind);box.dir='auto';box.append(el('small',label));if(text.length>600){box.append(el('div',text.slice(0,350)+'…'));const d=el('details',undefined,'flow-full');d.append(el('summary','הצג הודעה מלאה'),el('div',text));box.append(d)}else box.append(renderRichText(text));return box}
 function files(box,items){for(const f of items||[]){const a=el('a','↧ '+f.name);a.href='/api/files/'+encodeURIComponent(f.id)+'/content';a.download=f.name;box.append(a);if(/\.(png|jpe?g|webp)$/i.test(f.name||'')){const img=el('img');img.src=a.href;img.alt=f.name;img.loading='lazy';box.append(img)}}}
 renderTurns=async function(turns){
  const area=$('messages'),atBottom=area.scrollHeight-area.scrollTop-area.clientHeight<120;
  if(showCorrespondence&&correspondenceMessages.length){await original(turns);for(const row of area.querySelectorAll('.bridge-message')){if(row.classList.contains('agent_status'))row.remove()}const last=turns.at(-1);if(last)statusContent.replaceChildren(makeCard(last));}
  else if(turns.length){area.replaceChildren();if(chat?.has_older)area.append(button('הודעות קודמות',async()=>{historyBefore=chat.next_before;signature='';await refresh();area.scrollTop=0}));if(historyBefore!==null)area.append(button('חזרה להודעות האחרונות',async()=>{historyBefore=null;signature='';await refresh()}));for(const task of turns){const box=message(task.presentation?.text||task.goal,'user',task.presentation?.source==='mcp'?'בקשה דרך MCP':'הבקשה שלך');files(box,task.attachments);area.append(box);if(task.result)area.append(message(task.result,'assistant','MellowCodex · תוצאת הביצוע'));else area.append(message(task.state==='queued'?'הבקשה התקבלה וממתינה לביצוע.':states[task.state]||task.state,'assistant','MellowCodex · עדכון מצב'));area.append(button("מצב המשימה ופרטים",()=>{statusContent.replaceChildren(makeCard(task));statusDialog.showModal();updateLiveness()}))}}
  else await original(turns);
  if(turns.length&&!statusDialog.open)statusContent.replaceChildren(makeCard(turns.at(-1)));updateTopStatus();context.firstChild.textContent=turns.length?'המשך באותה שיחה':'משימה חדשה';if(atBottom||turns.length<2)area.scrollTop=area.scrollHeight;
 };
 function updateLiveness(){for(const card of document.querySelectorAll('.flow-card')){const task=card.taskSnapshot||chat?.turns?.find(t=>t.id===card.dataset.task);if(!task)continue;const item=activity.get(task.id),state=item?.state||task.state;const active=['running','queued','verifying'].includes(state);const received=activityReceived.get(task.id)||0;const stale=active&&(!received||Date.now()-received>15000);card.dataset.state=state;card.classList.toggle('flow-active',active&&!stale);card.classList.toggle('flow-stale',stale);let badge=card.querySelector('.flow-heartbeat');if(!badge){badge=el('div',undefined,'flow-heartbeat');badge.setAttribute('role','status');badge.tabIndex=0;badge.title='הצג מה הסוכן עושה כעת';const reveal=()=>{const d=card.querySelector('.tools');d.open=true;safe(d.refreshEvidence)};badge.onclick=reveal;badge.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();reveal()}};card.querySelector('h2').after(badge)}badge.textContent=stale?'עדכוני המצב לא מגיעים — לא ניתן לאמת שהביצוע מתקדם':active?((phase[item?.execution?.waiting_for]||states[state])+' · '+(item?.execution?.phase_elapsed_seconds||0)+' שניות בשלב · לחץ לפרטים'):state==='waiting_review'?'ממתין לבדיקה — אין פעולה שרצה כרגע':states[state]||state;}}
 window.addEventListener('task-activity',event=>{for(const item of event.detail.items){activity.set(item.task_id,item);activityReceived.set(item.task_id,Date.now())}for(const card of document.querySelectorAll('.flow-card')){const task=card.taskSnapshot||chat?.turns?.find(t=>t.id===card.dataset.task);if(task)updateCard(card,task);const details=card.querySelector('.tools');if(details?.open)safe(details.refreshEvidence)}updateLiveness()});
 setInterval(updateLiveness,2000);
 signature='';safe(refresh);
})();
