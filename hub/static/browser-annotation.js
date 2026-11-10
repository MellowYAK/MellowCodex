(() => {
  if (window.__mellowSelection) window.__mellowSelection.cancel();
  const state={result:null,active:true};
  window.__mellowSelection=state;
  const overlay=document.createElement('div'), box=document.createElement('div');
  overlay.setAttribute('data-mellow-picker','');
  overlay.style.cssText='position:fixed!important;inset:0!important;z-index:2147483647!important;cursor:crosshair!important;background:transparent!important;touch-action:none!important';
  box.style.cssText='position:fixed!important;pointer-events:none!important;border:2px solid #2563eb!important;background:#2563eb18!important;box-sizing:border-box!important';
  overlay.append(box);document.documentElement.append(overlay);
  let start=null,target=null;
  const stop=e=>{e.preventDefault();e.stopImmediatePropagation()};
  function hit(x,y){overlay.style.setProperty('pointer-events','none','important');let n=document.elementFromPoint(x,y);overlay.style.removeProperty('pointer-events');while(n?.shadowRoot){const c=n.shadowRoot.elementFromPoint(x,y);if(!c||c===n)break;n=c}return n}
  function rect(r){return {x:r.x,y:r.y,width:r.width,height:r.height}}
  function paint(r){for(const [k,v] of Object.entries({left:r.x,top:r.y,width:r.width,height:r.height}))box.style.setProperty(k,v+'px','important')}
  function cleanup(){overlay.remove();for(const [n,f] of listeners)window.removeEventListener(n,f,true);state.active=false}
  state.cancel=()=>{cleanup();state.result={cancelled:true}};
  function describe(n){
    const css=getComputedStyle(n), styles={};for(const k of ['display','position','color','background-color','font-family','font-size','font-weight','margin','padding','border','border-radius','width','height','overflow','z-index','transform'])styles[k]=css.getPropertyValue(k).slice(0,200);
    const attrs={};for(const k of ['id','class','role','aria-label','alt','type'])if(n.hasAttribute(k))attrs[k]=n.getAttribute(k).slice(0,200);
    let text='';const walker=document.createTreeWalker(n,NodeFilter.SHOW_TEXT);let t,count=0;while((t=walker.nextNode())&&count++<100&&text.length<1000){if(!t.parentElement?.closest('input,textarea,select,[contenteditable],script,style'))text+=t.textContent+' '}
    const path=[];for(let p=n;p&&path.length<7;p=p.parentElement){const tag=p.tagName.toLowerCase();path.unshift(tag+(p.id?'#'+CSS.escape(p.id):''));}
    return {tag:n.tagName.toLowerCase(),attributes:attrs,text:text.trim().slice(0,1000),dom_path:path.join(' > '),css:styles,frame_boundary:n.tagName==='IFRAME'};
  }
  function down(e){stop(e);if(e.button!==0)return;start={x:e.clientX,y:e.clientY};target=hit(e.clientX,e.clientY)}
  function move(e){stop(e);if(start){paint({x:Math.min(start.x,e.clientX),y:Math.min(start.y,e.clientY),width:Math.abs(e.clientX-start.x),height:Math.abs(e.clientY-start.y)})}else{const n=hit(e.clientX,e.clientY);if(n)paint(n.getBoundingClientRect())}}
  function up(e){stop(e);if(!start||!target)return;
    const drag=Math.hypot(e.clientX-start.x,e.clientY-start.y)>6;
    const r=drag?{x:Math.min(start.x,e.clientX),y:Math.min(start.y,e.clientY),width:Math.abs(e.clientX-start.x),height:Math.abs(e.clientY-start.y)}:rect(target.getBoundingClientRect());
    const url=new URL(location.href);url.search='';url.hash='';url.username='';url.password='';
    state.result={kind:drag?'region':'element',url:url.href,title:document.title.slice(0,200),rect:r,viewport:{width:innerWidth,height:innerHeight,scrollX,scrollY,devicePixelRatio},element:describe(target),limits:['DOM/CSS describe the selected element (region: drag-start element).','Cross-origin iframe internals and closed shadow roots are not inspected.','URL query and fragment, form values and arbitrary attributes omitted.']};
    box.remove();overlay.style.setProperty('pointer-events','auto','important');
    // Keep interception through the matching click so links/buttons never activate.
    setTimeout(cleanup,150);
  }
  function key(e){if(e.key==='Escape'){stop(e);state.cancel()}}
  const listeners=[['pointerdown',down],['pointermove',move],['pointerup',up],['click',stop],['dblclick',stop],['contextmenu',stop],['keydown',key]];
  for(const [n,f] of listeners)window.addEventListener(n,f,true);
  return true;
})()
