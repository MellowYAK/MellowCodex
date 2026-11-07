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
 for(const node of children){if(node===close||node.tagName==='H2')continue;if(node.tagName==='SECTION'){const h=node.querySelector('h3')?.textContent||'';(node.classList.contains('model-settings')?models:h.includes('דחיסת')?visual:connection).append(node)}else if(node.contains($('project-notes'))||['save-notes','worktree'].includes(node.id))projectPage.append(node);else general.append(node)}
 projectPage.append(button('פתח את זיכרון השיחה',()=>{settings.close();window.openContinuity()}));
 const ext=page('extensions','פלאגינים וסקילים');ext.append(el('p','מרכז ההרחבות של הסוכן'),el('p','חיבור ChatGPT זמין תחת חיבורים. כלים מקומיים רשומים זמינים לסוכן דרך extensions_list. קטלוג התקנה לפלאגינים ולסקילים עדיין בפיתוח; הוא לא מוצג כפעיל לפני אימות.'));
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
  const methods=el('div',undefined,'ai-connector-methods');for(const route of provider.transports){const b=button(route.name,async()=>{connectorDialog.close();await openChatGPT();chooseTransport(route.id);transportSelect.value=route.id});b.disabled=!route.implemented;b.title=route.requires;methods.append(b)}card.append(methods,el('small',provider.connection_state==='not_implemented'?'בפיתוח · עדיין לא ניתן לחבר':'נדרשת התחברות · בחירת מסלול אינה מחברת אוטומטית'));return card}));});
 connectorNav.id='ai-connectors-nav';$('chatgpt-bridge').before(connectorNav);
 for(const d of document.querySelectorAll('dialog')){d.addEventListener('click',e=>{if(e.target!==d)return;const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close()})}
})();
