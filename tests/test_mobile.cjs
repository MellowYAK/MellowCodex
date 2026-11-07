const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('hub/static/app.js','utf8').split('\n').find(l=>l.startsWith('const uid='));
const ctx={crypto:{getRandomValues:a=>{for(let i=0;i<a.length;i++)a[i]=Math.floor(Math.random()*4294967296);return a}}};vm.createContext(ctx);vm.runInContext(source+';this.makeId=uid',ctx);
const ids=new Set(Array.from({length:1000},()=>ctx.makeId()));assert.equal(ids.size,1000);assert([...ids].every(id=>id.length>=8));console.log('HTTP mobile UUID fallback passed (crypto.randomUUID absent)');
