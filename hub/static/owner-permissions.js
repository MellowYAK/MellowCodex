/* Read-only owner permission UI. This page cannot grant owner consent. */
(() => {
  const labels = {safe:'בטוח', ask:'אישור לכל פעולה', full:'שליטה מלאה ומורחבת'};
  const badge = document.createElement('button');
  badge.id='owner-permission-badge'; badge.type='button';
  badge.textContent='הרשאות: בודק מצב';
  badge.setAttribute('aria-label','מצב הרשאות בעל המחשב');
  const header=document.querySelector('main > header');
  if (!header) return;
  header.insertBefore(badge,header.querySelector('.header-actions'));
  const dialog=document.createElement('dialog'); dialog.id='owner-permissions-dialog'; dialog.dir='rtl';
  const title=document.createElement('h2'); title.textContent='הרשאות בעל המחשב';
  const status=document.createElement('p'); status.setAttribute('role','status');
  const source=document.createElement('p');
  const selector=document.createElement('select'); selector.setAttribute('aria-label','רמת הרשאה פעילה');
  for (const [id,label] of Object.entries(labels)) {const opt=document.createElement('option');opt.value=id;opt.textContent=label;selector.appendChild(opt);}
  selector.disabled=true;
  const scope=document.createElement('p');
  scope.textContent='ברירת מחדל כללית וחריגה לשיחה: שינוי דורש אישור בעל המחשב ברכיב המקומי המוגן. דף זה מציג מצב בלבד.';
  const duration=document.createElement('label');duration.textContent='משך הרשאה מתוכנן (דקות): ';
  const durationInput=document.createElement('input');durationInput.type='number';durationInput.min='1';durationInput.value='60';durationInput.disabled=true;duration.appendChild(durationInput);
  const blocker=document.createElement('p');
  blocker.textContent='שינוי הרשאות חסום עד לחיבור ואימות שירות בעל המחשב. לחיצה בממשק זה אינה אישור בעלים. שליטה מלאה אינה פעילה.';
  const close=document.createElement('button');close.type='button';close.textContent='סגור';close.onclick=()=>dialog.close();
  dialog.append(title,status,source,selector,scope,duration,blocker,close);document.body.appendChild(dialog);
  let chatId='',sequence=0,busy=false;
  function selectedChat(){return typeof selected==='string'?selected:'';}
  async function refresh(){
    const requested=selectedChat();chatId=requested;const token=++sequence;busy=true;
    try{
      const res=await fetch('/api/owner-permissions/status?chat_id='+encodeURIComponent(requested),{credentials:'same-origin',cache:'no-store'});
      if(!res.ok)throw Error('HTTP '+res.status);
      const current=await res.json();
      if(token!==sequence||selectedChat()!==requested)return;
      if(!Object.hasOwn(labels,current.effective))throw Error('תגובה לא תקינה ממנגנון ההרשאות');
      const origin=current.source==='chat'?'שיחה זו':current.source==='global'?'ברירת מחדל כללית':'שירות בעלים לא זמין';
      badge.textContent='הרשאות: '+labels[current.effective]+' · '+origin;
      badge.dataset.permission=current.effective;selector.value=current.effective;
      blocker.textContent=current.owner_broker_verified?'Change permissions using the native Owner permissions (UAC) toolbar. Global/chat selection and exact action approval occur in that protected window. Chat overrides expire after one hour.':'Protected owner service is unavailable. Permission changes are disabled.';
      scope.textContent='Safe: reviewed read operations. Ask: approve each exact action. Full: all task-scoped ordinary tools, including unknown-risk scripts. Elevated operations require separate native support; Guard deployment review remains required. Chat expiry: '+(current.override_expires_at?new Date(current.override_expires_at*1000).toLocaleString():'none');
      source.textContent='כללי: '+(labels[current.global_default]||'לא ידוע')+' · שיחה זו: '+(labels[current.override]||'ירושה מהכללי')+' · גרסה: '+String(current.revision);
      status.textContent=current.owner_broker_verified?'שירות הבעלים מאומת; דף זה לקריאה בלבד.':'שירות בעל המחשב לא אומת. שינוי הרשאות אינו זמין.';
    }catch(err){
      if(token!==sequence||selectedChat()!==requested)return;
      badge.textContent='הרשאות: לא זמין';delete badge.dataset.permission;source.textContent='';
      status.textContent='לא ניתן לקרוא את מצב ההרשאות: '+String(err.message||err);
    }finally{if(token===sequence)busy=false;}
  }
  window.ownerPermissionSelectedChat=()=>refresh();
  badge.addEventListener('click',()=>{refresh();dialog.showModal();});
  refresh();
  setInterval(()=>{if(selectedChat()!==chatId||!busy&&dialog.open)refresh();},2500);
  setInterval(()=>{if(!busy)refresh();},20000);
})();