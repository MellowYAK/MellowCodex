const $=id=>document.getElementById(id);
let active;
chrome.tabs.query({active:true,currentWindow:true}).then(tabs=>{active=tabs[0];const url=new URL(active.url);if(!['http:','https:'].includes(url.protocol))throw Error('פתח אתר רגיל ב־Chrome כדי להעביר את הכניסה שלו.');$('site').textContent=url.origin;}).catch(e=>{$('status').textContent=e.message;$('transfer').disabled=true;});
$('transfer').onclick=async()=>{
  const code=$('code').value.trim();if(!code){$('status').textContent='הדבק את קוד הצימוד מהסוכן.';return;}
  $('transfer').disabled=true;
  try{
    const url=new URL(active.url);
    const granted=await chrome.permissions.request({origins:[url.origin+'/*']});
    if(!granted)throw Error('לא ניתנה הרשאה לאתר. לא הועבר מידע.');
    const cookies=await chrome.cookies.getAll({url:active.url});
    const results=await chrome.scripting.executeScript({target:{tabId:active.id},func:()=>({url:location.href,localStorage:Object.fromEntries(Object.entries(localStorage)),sessionStorage:Object.fromEntries(Object.entries(sessionStorage))})});
    const state=results[0].result;
    if(new URL(state.url).origin!==url.origin)throw Error('האתר השתנה. פתח את התוסף מחדש.');
    const response=await fetch('http://127.0.0.1:8876/bridge/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code,cookies,...state})});
    const result=await response.json();if(!response.ok)throw Error(result.detail||'ההעברה נכשלה');
    $('code').value='';
    $('status').textContent=`הועברו ${result.imported_cookies} מתוך ${result.requested_cookies} קוקיז.\nבדוק בדפדפן הסוכן שהאתר נשאר מחובר. ייתכן שהאתר ידרוש כניסה מחדש.`;
  }catch(e){$('status').textContent=e.message;}finally{$('transfer').disabled=false;}
};
