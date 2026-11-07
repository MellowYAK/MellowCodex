/* Text-only Markdown subset. No raw HTML, scripts or untrusted attributes. */
function renderRichText(text){
 const root=document.createElement('div');root.className='rich-text';
 function inline(parent,value){const re=/(`[^`\n]+`|\*\*[^*\n]+\*\*|\[[^\]\n]+\]\(https?:\/\/[^\s)]+\))/g;let at=0;for(const m of value.matchAll(re)){parent.append(document.createTextNode(value.slice(at,m.index)));const token=m[0];let e;if(token[0]==='`'){e=document.createElement('code');e.textContent=token.slice(1,-1)}else if(token.startsWith('**')){e=document.createElement('strong');e.textContent=token.slice(2,-2)}else{const end=token.indexOf('](');e=document.createElement('a');e.textContent=token.slice(1,end);e.href=token.slice(end+2,-1);e.target='_blank';e.rel='noopener noreferrer'}parent.append(e);at=m.index+token.length}parent.append(document.createTextNode(value.slice(at)))}
 let code=null,list=null;
 for(const line of String(text).split('\n')){if(line.startsWith('```')){if(code)code=null;else{const pre=document.createElement('pre');code=document.createElement('code');pre.append(code);root.append(pre)}list=null;continue}if(code){code.append(document.createTextNode(line+'\n'));continue}if(!line.trim()){list=null;continue}const bullet=line.match(/^\s*(?:[-*]|\d+\.)\s+(.*)$/);if(bullet){if(!list){list=document.createElement('ul');root.append(list)}const li=document.createElement('li');inline(li,bullet[1]);list.append(li);continue}list=null;const heading=line.match(/^#{1,4}\s+(.*)$/),p=document.createElement(heading?'h3':'p');inline(p,heading?heading[1]:line);root.append(p)}
 return root;
}
