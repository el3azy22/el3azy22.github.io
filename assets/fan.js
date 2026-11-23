/* منصة العازي · هوية المشجع (نادي + اسم اختياري) — مشتركة بين كل الصفحات
   - المحلي: el3azy_club (رمز النادي، '' = ما يشجع نادي معيّن، null = ما اختار)، el3azy_name، el3azy_fb (الحساب المجهول)
   - السيرفر: f/{uid} = {c, n} و fc/{club} = عدد مشجعي كل نادي (يقراه أي أحد) */
(()=>{
const SRC=document.currentScript&&document.currentScript.src;const ROOT=SRC?new URL('../',SRC).href:'/';
const FB={key:'AIzaSyCJVYgLTqvj2k1KnvLYo6Z1feOS4E8fj94',db:'https://el3azy-3b64e-default-rtdb.europe-west1.firebasedatabase.app'};
const CL={ain:'العين',wahda:'الوحدة',jazira:'الجزيرة',shababahli:'شباب الأهلي',sharjah:'الشارقة',wasl:'الوصل',nasr:'النصر',baniyas:'بني ياس',ajman:'عجمان',kalba:'كلباء',khorfakkan:'خورفكان',dhafra:'الظفرة',hatta:'حتا',united:'يونايتد'};
const ORDER=Object.keys(CL);
const CREST={jazira:[1,1],sharjah:[.979,1.133],dhafra:[.92,1.106],ain:[.83,1.197],nasr:[1,1],wahda:[.91,1.176],wasl:[.973,1.165],baniyas:[1.234,.681],hatta:[.989,1.122],khorfakkan:[1.048,1.069],shababahli:[1.037,1.074],ajman:[1.154,1.016],kalba:[.995,1],united:[.995,.995]};
const crest=(c,s)=>{const f=CREST[c]||[1,1];return `<img src="${ROOT}mano/assets/${c}.png" alt="" style="width:${Math.round(s*f[0])}px;height:${Math.round(s*f[1])}px;object-fit:contain">`};
const PID={get(k,old){try{const v=localStorage.getItem('el3azy_'+k);if(v!=null)return JSON.parse(v);const o=old&&localStorage.getItem(old);return o!=null?JSON.parse(o):null}catch(e){return null}},set(k,v){try{localStorage.setItem('el3azy_'+k,JSON.stringify(v))}catch(e){}}};
const club=()=>PID.get('club','el3azy_mano_club');           // null = ما اختار
const name=()=>PID.get('name')||'';
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const BAD=/(كلب|حمار|زق|خرا|منيو|شرموط|قحب|عاهر|fuck|shit|bitch)/i;
const cleanName=s=>{s=(s||'').replace(/[<>"'`\\]/g,'').replace(/\s+/g,' ').trim().slice(0,16);return BAD.test(s)?'':s};
const gc=n=>{try{window.goatcounter&&goatcounter.count({path:n,title:n,event:true})}catch(e){}};

async function tok(){
  let a=PID.get('fb','el3azy_mano_fb')||PID.get('fb','el3azy_rate_fb');
  if(a&&a.exp>Date.now()+6e4)return a;
  let r=null;
  if(a&&a.r){r=await fetch('https://securetoken.googleapis.com/v1/token?key='+FB.key,{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:'grant_type=refresh_token&refresh_token='+encodeURIComponent(a.r)}).then(x=>x.ok?x.json():null).catch(()=>null);
    if(r&&r.id_token)a={t:r.id_token,r:r.refresh_token,u:r.user_id,exp:Date.now()+r.expires_in*1e3};else r=null}
  if(!r){r=await fetch('https://identitytoolkit.googleapis.com/v1/accounts:signUp?key='+FB.key,{method:'POST',headers:{'content-type':'application/json'},body:'{"returnSecureToken":true}'}).then(x=>x.json());
    if(!r.idToken)throw new Error('auth');a={t:r.idToken,r:r.refreshToken,u:r.localId,exp:Date.now()+r.expiresIn*1e3}}
  PID.set('fb',a);return a;
}
/* يسجل اختيار المشجع في قاعدة البيانات، والسيرفر هو الحَكَم:
   - بعد كل اختيار نادي: 24 ساعة يقدر يعدّل فيها
   - وبعدها تغيير واحد في الموسم (x = الموسم اللي غيّر فيه). الموسم يبدا 1 أغسطس
   - «محايد» يقدر يختار نادي أي وقت. الاسم يتغير بحرية */
const DAY=864e5,S0=1785528000000,YMS=31557600000;
const season=t=>Math.floor((t-S0)/YMS);
function lock(){const s=PID.get('fan_srv');const now=Date.now();
  if(!s||!s.t||s.c==='none')return{free:true,first:!s||s.c==='none'};
  if(now-s.t<DAY)return{free:true,grace:s.t+DAY};
  if(s.x==null||s.x<season(now))return{free:true,left:true};
  return{free:false};
}
let syncing=null;
// المنطقة الزمنية للتلفون (داخل الإمارات أو برا) — تنرسل مرة، وتتحدث لو تغيرت
async function sendTz(){try{let z='';try{z=Intl.DateTimeFormat().resolvedOptions().timeZone||''}catch(e){}
  if(!z||!/^[A-Za-z_]+(\/[A-Za-z0-9_+-]+){0,2}$/.test(z)||z.length>40||PID.get('tz_sent')===z)return;
  const a=await tok(),r=await fetch(FB.db+'/g/'+a.u+'.json?auth='+a.t,{method:'PUT',body:JSON.stringify(z)});if(r.ok)PID.set('tz_sent',z)}catch(e){}}
async function sync(){
  const c=club();if(c===null)return;sendTz();
  const cv=c||'none',n=name(),srv=PID.get('fan_srv');
  if(srv&&srv.t&&srv.c===cv&&srv.n===n)return;
  if(syncing)return syncing;
  syncing=(async()=>{try{
    const a=await tok();const U=FB.db+'/f/'+a.u+'.json?auth='+a.t;
    const cur=await fetch(U).then(r=>r.ok?r.json():null).catch(()=>null);
    if(cur&&cur.c===cv&&cur.n===n&&cur.t){PID.set('fan_srv',cur);return}
    const now=Date.now(),TS={'.sv':'timestamp'};let t=TS,x=cur?cur.x:undefined;
    if(cur&&cur.t){
      if(cur.c===cv||now-cur.t<DAY)t=cur.t;            // نفس النادي أو خلال مهلة الـ24 ساعة
      else if(cur.c!=='none')x=season(now);             // التغيير الوحيد في هالموسم
    }
    const b={};b['f/'+a.u]={c:cv,n,t,x};
    if(!cur||cur.c!==cv){b['fc/'+cv]={'.sv':{increment:1}};if(cur&&cur.c)b['fc/'+cur.c]={'.sv':{increment:-1}}}
    const r=await fetch(FB.db+'/.json?auth='+a.t,{method:'PATCH',body:JSON.stringify(b)});
    if(r.ok){const v=await fetch(U).then(r=>r.ok?r.json():null).catch(()=>null);PID.set('fan_srv',v||{c:cv,n,t:typeof t==='number'?t:now,x})}
    else if(cur&&cur.c&&cur.c!==cv){ // السيرفر رفض تغيير النادي: نرجع للنادي المسجل
      PID.set('club',cur.c==='none'?'':cur.c);PID.set('fan_srv',cur);render();window.dispatchEvent(new Event('el3fan'))}
  }catch(e){}finally{syncing=null}})();
  return syncing;
}
function set(c,n){const old=club();PID.set('club',c);if(n!==undefined)PID.set('name',cleanName(n));if(old!==c)gc('club-'+(c||'none'));sync();render();window.dispatchEvent(new Event('el3fan'))}


/* ---------- «رمز النقل»: ينقل البطاقة لتلفون أو متصفح ثاني بدون تسجيل (قرار إبراهيم 18 نوفمبر) ----------
   التلفون القديم يسوي رمز من 8 حروف، صالح 10 دقايق ومرة وحدة. البيانات (الحساب المجهول + بيانات اللعب المحلية)
   تنشفّر بالرمز نفسه (AES-GCM) وتنحفظ في x/<sha256(الرمز)>، فاللي ما عنده الرمز ما يوصل لها ولا يقدر يقراها. */
const AB='ABCDEFGHJKMNPQRSTUVWXYZ23456789',TE=new TextEncoder();
const hex=b=>[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');
const b64=b=>{const u=new Uint8Array(b);let s='';for(let i=0;i<u.length;i+=8192)s+=String.fromCharCode.apply(null,u.subarray(i,i+8192));return btoa(s)};
const ub64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const normCode=s=>(s||'').toUpperCase().replace(/[^A-Z0-9]/g,'');
const fmtCode=c=>c.slice(0,4)+'-'+c.slice(4);
// يقبل الرمز أو رابط النقل كامل (لو لصق الرابط في خانة الرمز)
const pickCode=v=>{v=v||'';const m=v.match(/nql=([A-Za-z0-9]{4}-?[A-Za-z0-9]{4})/)||v.match(/\b([A-Za-z0-9]{4}-[A-Za-z0-9]{4})\b/);return normCode(m?m[1]:v).slice(0,8)};
async function kd(code){const h=hex(await crypto.subtle.digest('SHA-256',TE.encode('el3azy-x|'+code)));
  const k=await crypto.subtle.importKey('raw',await crypto.subtle.digest('SHA-256',TE.encode('el3azy-k|'+code)),'AES-GCM',false,['encrypt','decrypt']);return{h,k}}
const MOVE=k=>/^el3azy_/.test(k)&&!/^el3azy_(fb|mano_fb|rate_fb|gc_key|adm_range)$/.test(k);
async function makeCode(){
  await sync();const a=await tok();
  const code=Array.from(crypto.getRandomValues(new Uint8Array(8)),v=>AB[v%AB.length]).join('');
  const ls={};try{for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(MOVE(k))ls[k]=localStorage.getItem(k)}}catch(e){}
  const {h,k}=await kd(code),iv=crypto.getRandomValues(new Uint8Array(12));
  const ct=await crypto.subtle.encrypt({name:'AES-GCM',iv},k,TE.encode(JSON.stringify({r:a.r,u:a.u,ls})));
  const e=Date.now()+10*60e3;
  const r=await fetch(`${FB.db}/x/${h}.json?auth=${a.t}`,{method:'PUT',body:JSON.stringify({u:a.u,c:b64(ct),i:b64(iv),e})});
  if(!r.ok)throw new Error('save');gc('move-make');return{code,e};
}
async function useCode(input){
  const code=normCode(input);if(code.length!==8)throw new Error('bad');
  let {h,k}=await kd(code);
  let d=await fetch(`${FB.db}/x/${h}.json`).then(r=>r.ok?r.json():null).catch(()=>null),rk=false;
  if(!d||!d.c){({h,k}=await kdR(code));d=await fetch(`${FB.db}/rk/${h}.json`).then(r=>r.ok?r.json():null).catch(()=>null);rk=true}   // رمز الاسترجاع الثابت
  if(!d||!d.c)throw new Error('bad');
  const p=JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:ub64(d.i)},k,ub64(d.c))));
  const r=await fetch('https://securetoken.googleapis.com/v1/token?key='+FB.key,{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:'grant_type=refresh_token&refresh_token='+encodeURIComponent(p.r)}).then(x=>x.ok?x.json():null).catch(()=>null);
  if(!r||!r.id_token||r.user_id!==p.u)throw new Error('net');
  const a={t:r.id_token,r:r.refresh_token,u:r.user_id,exp:Date.now()+r.expires_in*1e3};
  try{const old=[];for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(MOVE(k)||/^el3azy_(mano_fb|rate_fb)$/.test(k))old.push(k)}old.forEach(k=>localStorage.removeItem(k));
    Object.entries(p.ls||{}).forEach(([k,v])=>{if(MOVE(k))localStorage.setItem(k,v)})}catch(e){}
  PID.set('fb',a);if(rk)PID.set('rk',code);
  const f=await fetch(`${FB.db}/f/${a.u}.json?auth=${a.t}`).then(x=>x.ok?x.json():null).catch(()=>null);
  if(f&&f.c){PID.set('fan_srv',f);PID.set('club',f.c==='none'?'':f.c);PID.set('name',f.n||'')}
  if(!rk)fetch(`${FB.db}/x/${h}.json?auth=${a.t}`,{method:'DELETE'}).catch(()=>{});
  gc(rk?'rk-use':'move-use');return f;
}
/* ---------- «رمز الاسترجاع» (قرار إبراهيم 20 نوفمبر): رمز ثابت لكل بطاقة، لو ضاعت من التلفون (مثلاً متصفح X مسحها) يكتبه في «عندي رمز نقل» وترجع.
   فيه الحساب المجهول بس (مشفّر بالرمز) في rk/<sha256>. النقاط والنادي والاسم يرجعون من السيرفر. ما ينتهي، وصاحبه يقدر يغيّره */
async function kdR(code){const h=hex(await crypto.subtle.digest('SHA-256',TE.encode('el3azy-rk|'+code)));
  const k=await crypto.subtle.importKey('raw',await crypto.subtle.digest('SHA-256',TE.encode('el3azy-rkk|'+code)),'AES-GCM',false,['encrypt','decrypt']);return{h,k}}
async function newRk(){
  const a=await tok(),code=Array.from(crypto.getRandomValues(new Uint8Array(8)),v=>AB[v%AB.length]).join('');
  const {h,k}=await kdR(code),iv=crypto.getRandomValues(new Uint8Array(12));
  const ct=await crypto.subtle.encrypt({name:'AES-GCM',iv},k,TE.encode(JSON.stringify({r:a.r,u:a.u})));
  const r=await fetch(`${FB.db}/rk/${h}.json?auth=${a.t}`,{method:'PUT',body:JSON.stringify({u:a.u,c:b64(ct),i:b64(iv)})});
  if(!r.ok)throw new Error('save');return code}
async function myRk(){const c=PID.get('rk');if(c)return c;const n=await newRk();PID.set('rk',n);gc('rk-make');return n}
async function swapRk(){const old=PID.get('rk'),n=await newRk();PID.set('rk',n);
  if(old){const a=await tok(),{h}=await kdR(old);fetch(`${FB.db}/rk/${h}.json?auth=${a.t}`,{method:'DELETE'}).catch(()=>{})}gc('rk-swap');return n}
/* ---------- الواجهة ---------- */
const css=`
.fz-chip{display:inline-flex!important;align-items:center;gap:7px;width:auto!important;height:38px!important;padding:0 11px 0 9px!important;border:1px solid rgba(215,180,101,.45)!important;border-radius:12px!important;background:rgba(215,180,101,.07)!important;color:#F6E3AE!important;font:600 13px 'Readex Pro',system-ui,sans-serif!important;white-space:nowrap;cursor:pointer;text-decoration:none;max-width:62vw;min-width:0;flex:0 1 auto;overflow:hidden;-webkit-tap-highlight-color:transparent}
.fz-chip img{flex-shrink:0}
.fz-chip span{overflow:hidden;text-overflow:ellipsis}
.topnav>*:not(.fz-chip){flex-shrink:0}
.fz-chip small{color:#FFF5E5;opacity:.6;font-weight:400;overflow:hidden;text-overflow:ellipsis;min-width:0}
.fz-top{display:flex;justify-content:flex-end;padding:2px 0 4px}
.fz-card{margin-top:22px;cursor:pointer}
.fz-bg{position:fixed;inset:0;z-index:9998;background:rgba(3,14,22,.82);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);display:grid;place-items:center;padding:18px}
.fz-sh{background:linear-gradient(165deg,#14384F,#071D2B);border:1px solid rgba(215,180,101,.4);border-radius:24px;padding:22px 18px 16px;max-width:390px;width:100%;max-height:90vh;overflow-y:auto;color:#FFF5E5;font-family:'Readex Pro',system-ui,sans-serif;text-align:center;animation:fzpop .3s}
@keyframes fzpop{from{transform:scale(.94);opacity:0}to{transform:none;opacity:1}}
.fz-tile{width:58px;height:58px;margin:0 auto 6px;border-radius:17px;display:grid;place-items:center;background:linear-gradient(160deg,rgba(215,180,101,.22),rgba(215,180,101,.05));border:1px solid rgba(215,180,101,.55)}
.fz-tile svg{width:32px;height:32px}
.fz-sh h2{color:#D7B465;font-size:21px;margin:4px 0 6px;display:block!important;text-align:center}
.fz-sh h2:before,.fz-sh h2:after{display:none!important}
.fz-sh .fz-why{font-size:13px;opacity:.8;line-height:1.8;margin-bottom:12px}
.fz-sh .fz-why b{color:#D7B465;font-weight:600}
.fz-sh [hidden]{display:none!important}
.pf{text-align:center}
.pf-rkc{margin:6px 0 2px;padding:9px 12px;border-radius:12px;background:#071D2B;border:1px solid rgba(215,180,101,.3);text-align:right}
.rk-l{display:flex;align-items:center;gap:8px}.rk-l span{font-size:12.5px;color:#F1DDAE;white-space:nowrap}
.rk-l b{flex:1;text-align:center;font-size:16px;letter-spacing:1.5px;color:#F6E3AE;white-space:nowrap;user-select:all;-webkit-user-select:all}
.rk-l .fz-link{font-weight:700;padding:2px;text-decoration:underline}
.pf-rkc small{display:block;font-size:11px;opacity:.65;margin-top:3px}.pf-rkc small .fz-link{font-size:11px;padding:0}
.pf-head{display:flex;align-items:center;gap:12px;text-align:right;margin:2px 0 14px}
.pf-cz{flex:none;width:66px;height:66px;border-radius:50%;display:grid;place-items:center;background:radial-gradient(circle at 50% 35%,rgba(255,245,229,.12),rgba(7,29,43,.6));border:1.5px solid rgba(215,180,101,.55)}
.pf-nm{flex:1;min-width:0}.pf-nm b{display:block;font-size:19px;line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pf-nm span{font-size:12.5px;color:#D7B465}
.pf-rk{flex:none;text-align:center;border-radius:14px;padding:6px 10px;background:linear-gradient(180deg,#F6E3AE,#B08A3E);color:#071D2B;line-height:1.25}
.pf-rk b{display:block;font-size:18px;direction:ltr}.pf-rk small{font-size:10.5px;font-weight:600}
.pf-seg{display:flex;background:rgba(7,29,43,.7);border:1px solid rgba(215,180,101,.25);border-radius:12px;padding:3px;margin-bottom:12px}
.pf-seg button{flex:1;border:0;background:none;color:#FFF5E5;opacity:.7;font:600 13px 'Readex Pro';padding:7px;border-radius:9px;cursor:pointer}
.pf-seg button.on{background:rgba(215,180,101,.2);color:#F6E3AE;opacity:1}
.pf-big b{display:block;font-size:54px;font-weight:700;line-height:1.1;background:linear-gradient(180deg,#FFFBF2 25%,#F1DDAE 70%,#D7B465);-webkit-background-clip:text;background-clip:text;color:transparent}
.pf-big span{font-size:13px;opacity:.75}
.pf-xi{margin:10px 0 12px;font-size:12.5px;line-height:1.7;background:rgba(7,29,43,.6);border:1px solid rgba(215,180,101,.28);border-radius:12px;padding:8px 10px}
.pf-xi b{color:#F6E3AE}
.pf-tiles{display:flex;gap:7px;margin-bottom:14px}
.pf-t{flex:1;min-width:0;background:rgba(7,29,43,.7);border:1px solid rgba(215,180,101,.2);border-radius:14px;padding:9px 6px 8px}
.pf-t i{display:block;font-style:normal;font-size:18px}.pf-t span{display:block;font-size:11px;opacity:.75;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pf-t b{display:block;font-size:20px;margin:2px 0 6px}
.pf-t u{display:block;height:4px;border-radius:2px;background:rgba(255,245,229,.1);overflow:hidden;text-decoration:none}.pf-t u i{display:block;height:100%;background:linear-gradient(90deg,#B08A3E,#F6E3AE)}
.pf-em{font-size:13px;opacity:.8;line-height:1.8;margin:6px 0 14px}
.pf .fz-ok{text-decoration:none;margin-bottom:4px}
.fz-grid{display:flex;flex-wrap:wrap;justify-content:center;gap:7px;margin-bottom:12px}
.fz-grid button{position:relative;width:calc(25% - 6px);height:76px;background:rgba(7,29,43,.75);border:1.5px solid rgba(215,180,101,.18);border-radius:14px;display:grid;justify-items:center;align-content:center;gap:5px;color:#FFF5E5;font:500 11px 'Readex Pro';cursor:pointer;transition:.15s}
.fz-grid button.on{border-color:#D7B465;background:rgba(215,180,101,.14);transform:translateY(-2px);box-shadow:0 6px 18px rgba(215,180,101,.2)}
.fz-grid button.on:after{content:'✓';position:absolute;top:-7px;left:-7px;width:20px;height:20px;border-radius:50%;background:#D7B465;color:#071D2B;font-size:12px;font-weight:700;display:grid;place-items:center}
@font-face{font-family:'Readex In';src:url(/tashkila/assets/ReadexPro.ttf);font-weight:160 700;font-display:swap;ascent-override:100%;descent-override:50%}
.fz-name{display:block;width:100%;box-sizing:border-box;background:#071D2B;border:1px solid rgba(215,180,101,.4);border-radius:12px;padding:11px 12px;color:#FFF5E5;font:500 15px 'Readex In','Readex Pro';text-align:center;margin-bottom:4px;outline:none}
.fz-name:focus{border-color:#D7B465}
.fz-hint{font-size:12px;opacity:.8;line-height:1.6;margin:0 2px 12px}.fz-hint b{color:#D7B465;font-weight:600}
.fz-ok{display:block;width:100%;border:0;border-radius:14px;padding:13px;font:700 15px 'Readex Pro';background:linear-gradient(180deg,#F6E3AE,#B08A3E);color:#071D2B;cursor:pointer}
.fz-ok:disabled{opacity:.4}
.fz-row{display:flex;justify-content:space-between;margin-top:8px}
.fz-grid button:disabled{opacity:.3;cursor:default}
.fz-lock{font-size:11.5px;color:#D7B465;opacity:.85;margin:-4px 2px 12px;line-height:1.7}
.fz-mv{display:flex;justify-content:center;gap:4px;flex-wrap:wrap;margin-top:10px;padding-top:10px;border-top:1px solid rgba(215,180,101,.18)}
.fz-code{direction:ltr;font:700 34px 'Readex Pro';letter-spacing:4px;color:#F6E3AE;background:#071D2B;border:1.5px dashed rgba(215,180,101,.6);border-radius:16px;padding:12px 8px;margin:4px 0 8px;user-select:all;-webkit-user-select:all}
.fz-in{direction:ltr;text-transform:uppercase;letter-spacing:3px;font-weight:700!important;font-size:20px!important}
.fz-err{font-size:12.5px;color:#ef8f86;min-height:20px;margin:2px 0 8px}
.fz-link{background:none;border:0;color:#D7B465;font:400 12.5px 'Readex Pro';text-decoration:underline;padding:6px;cursor:pointer}
`;
/* «ملف المشجع»: أول ما يفتح بطاقته يشوف نقاطه (هالأسبوع/الموسم) ومكانه في نخبة جمهور ناديه. تعديل البطاقة تحت */
const PTN={mano:['🕵️','منو اللاعب؟'],pred:['🔮','التوقعات'],tp:['🧩','التشكيلة'],grid:['🔢','الشبكة'],bus:['🚌','الباص']};
async function profile(bg,close){const box=bg.querySelector('#pf');if(!box)return;
  const nf=n=>Number(n||0).toLocaleString('en-US'),sh=bg.querySelector('.fz-sh'),ed=bg.querySelector('.fz-ed');
  const top=[sh.querySelector('.fz-tile'),sh.querySelector('h2')];top.forEach(e=>e&&(e.hidden=true));
  const toEdit=()=>{box.hidden=true;ed.hidden=false;top.forEach(e=>e&&(e.hidden=false));sh.scrollTop=0};
  let R=null,D=null;
  try{[R,D]=await Promise.all(['ranks','data'].map(f=>fetch(ROOT+'fans/'+f+'.json?v='+Math.floor(Date.now()/6e4)).then(r=>r.ok?r.json():null).catch(()=>null)))}catch(e){}
  const a=PID.get('fb'),u=a&&a.u?a.u.slice(0,12):null,c=club(),n=(name()||'').trim();
  let T='week';
  const draw=()=>{
    const M=(R&&u&&R[T]&&R[T][u])||{},all=M.all,ks=Object.keys(PTN).filter(k=>(D&&D.challenges||[]).some(x=>x.id===k)||M[k]);
    let xi='';
    if(T==='week'&&D&&c&&c!=='none'&&all){const W=(D.weeks||[]).find(w=>w.live)||(D.weeks||[])[D.weeks.length-1],B=W&&W.boards&&W.boards.all,L=((B&&B.xi)||{})[c]||[],X=D.xi||11,k=L.findIndex(x=>x[2]===u),ac=M.act;
      if(k>=0)xi=`⚽ أنت رقم <b>${nf(L[k][3]||k+1)}</b> في نخبة جمهور <b>${CL[c]}</b>`;
      else if(ac&&ac[0]<ac[1])xi=`⏳ نقاطك تدخل نخبة جمهور <b>${CL[c]}</b> لما تلعب في <b>${ac[1]}</b> أيام مختلفة (لعبت ${ac[0]===1?'يوم واحد':ac[0]===2?'يومين':ac[0]+' أيام'})`;
      else if(L.length>=X){const need=L[X-1][1]-all[1]+1;xi=`تحتاج <b>${need===1?'نقطة وحدة':need===2?'نقطتين':nf(need)+(need<=10?' نقاط':' نقطة')}</b> وتدخل نخبة جمهور <b>${CL[c]}</b> (أفضل ${X} مشجع)`}}
    if(!c||c==='none')xi='اختار ناديك عشان نقاطك تنحسب لجمهوره';
    const sum=all?all[1]:0;
    box.innerHTML=`<div class="pf-head"><div class="pf-cz">${c&&c!=='none'?crest(c,44):'<span style="font-size:28px">⚽</span>'}</div>
      <div class="pf-nm"><b>${n?esc(n):'مشجع'}</b><span>${c&&c!=='none'?'جمهور '+CL[c]:'ما يشجع نادي معيّن'}</span></div>
      ${all?`<div class="pf-rk"><b>#${nf(all[0])}</b><small>من ${nf(all[2])}</small></div>`:''}</div>
     <div class="pf-seg"><button type="button" data-t="week" class="${T==='week'?'on':''}">هالأسبوع</button><button type="button" data-t="season" class="${T==='season'?'on':''}">الموسم</button></div>
     ${all?`<div class="pf-big"><b>${nf(sum)}</b><span>${sum===1?'نقطة':sum===2?'نقطتين':'نقطة'} ${T==='week'?'هالأسبوع':'في الموسم'}</span></div>
       ${xi?`<div class="pf-xi">${xi}</div>`:'<div style="height:10px"></div>'}
       <div class="pf-tiles">${ks.map(k=>{const v=M[k]?M[k][1]:0;return `<div class="pf-t"><i>${PTN[k][0]}</i><span>${PTN[k][1]}</span><b>${nf(v)}</b><u><i style="width:${sum?Math.round(v/sum*100):0}%"></i></u></div>`}).join('')}</div>`
      :`<div class="pf-em">ما عندك نقاط ${T==='week'?'هالأسبوع':'في الموسم'} لين الحين.<br>العب أي تحدي، ونقاطك تطلع هني خلال 15 دقيقة تقريباً.</div>`}
     <a class="fz-ok" href="${ROOT}fans/">🏆 الترتيب كامل</a>
     <div class="fz-row"><button class="fz-link pf-ed" type="button">✏️ تعديل البطاقة</button><button class="fz-link pf-x" type="button" style="opacity:.7">إغلاق</button></div>
     <div class="pf-rkc" hidden></div>
     <div class="fz-mv"><button class="fz-link pf-mk" type="button">📲 انقل بطاقتك لتلفون ثاني</button></div>`;
    rkRow(box.querySelector('.pf-rkc'));
    box.querySelectorAll('.pf-seg button').forEach(b=>b.onclick=()=>{T=b.dataset.t;draw()});
    box.querySelector('.pf-ed').onclick=toEdit;box.querySelector('.pf-x').onclick=close;box.querySelector('.pf-mk').onclick=()=>moveOut(bg);
  };
  draw();
}
function rkRow(el){if(!el||!crypto.subtle)return;
  const paint=c=>{el.hidden=false;el.innerHTML=`<div class="rk-l"><span>🔐 رمز الاسترجاع</span><b dir="ltr">${fmtCode(c)}</b><button class="fz-link rk-cp" type="button">انسخ</button></div>
    <small>صوّره واحفظه، يرجّع بطاقتك لو ضاعت · <button class="fz-link rk-sw" type="button">غيّره</button></small>`;
    el.querySelector('.rk-cp').onclick=async e=>{try{await navigator.clipboard.writeText(fmtCode(c));e.target.textContent='✓ انسخ'}catch(_){prompt('انسخ:',fmtCode(c))}};
    el.querySelector('.rk-sw').onclick=async e=>{if(!confirm('نسوي لك رمز جديد، والقديم ما يشتغل بعدها. أكيد؟'))return;e.target.textContent='...';try{paint(await swapRk())}catch(_){e.target.textContent='غيّره'}}};
  const c=PID.get('rk');if(c)return paint(c);myRk().then(paint).catch(()=>{})}
function addCss(){if(document.getElementById('fz-css'))return;const s=document.createElement('style');s.id='fz-css';s.textContent=css;document.head.appendChild(s)}

function open(){
  addCss();const cur=club(),edit=cur!==null;let pick=cur||null;
  const L=edit?lock():{free:true},locked=!L.free;
  const hrs=t=>{const h=Math.max(1,Math.ceil((t-Date.now())/36e5));return h===1?'ساعة':h===2?'ساعتين':h<=10?h+' ساعات':h+' ساعة'};
  const note=locked?`🔒 غيّرت ناديك هالموسم، تقدر تغيره الموسم القادم`
    :L.grace?`تقدر تعدل خلال ${hrs(L.grace)}، وبعدها تغيير واحد في الموسم`
    :L.left?`تقدر تغير ناديك مرة وحدة في الموسم`
    :`عندك 24 ساعة تعدل، وبعدها تغيير واحد في الموسم`;
  const bg=document.createElement('div');bg.className='fz-bg';
  bg.innerHTML=`<div class="fz-sh" role="dialog" aria-modal="true">
    <div class="fz-tile"><svg viewBox="2.6 2.6 26.8 26.8" fill="none" stroke="#D7B465" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5.5 5.6q5.3-1.9 10.5 0t10.5 0v4.6q-5.3 1.9-10.5 0t-10.5 0z" fill="rgba(215,180,101,.25)"/><path d="M10.8 4.7v4.5M16 5.6v4.6M21.2 6.6v4.5" stroke-width="1.3"/><path d="M5.5 6.6H3.4M5.5 9.2H3.4M26.5 6.6h2.1M26.5 9.2h2.1" stroke-width="1.2"/><circle cx="16" cy="16.3" r="2.7"/><path d="M11.6 21.2 7.6 10.6M20.4 21.2l4-10.6"/><path d="M10.6 28v-3.2a5.4 5.4 0 0 1 10.8 0V28"/></svg></div>
    <h2>${edit?'بطاقة المشجع':'تشجع أي نادي أنت؟'}</h2>
    ${edit?'<div class="pf" id="pf"><div class="pf-em">لحظة...</div></div>':''}<div class="fz-ed"${edit?' hidden':''}>
    <p class="fz-why">نتيجتك في كل أقسام المنصة تنحسب لـ<b>جمهور ناديك</b>،<br>وكل ما لعبت تساعده يتصدر منافسة الجماهير.</p>
    <div class="fz-grid">${ORDER.map(k=>`<button type="button" data-c="${k}" class="${k===pick?'on':''}"${locked&&k!==cur?' disabled':''}>${crest(k,34)}<span>${CL[k]}</span></button>`).join('')}</div>
    <p class="fz-lock">${note}</p>
    <input class="fz-name" maxlength="16" placeholder="اسمك (اختياري)" value="${esc(name())}">
    <p class="fz-hint">اكتب اسمك عشان يطلع في <b>نخبة جمهور ناديك</b> وفي <b>أعلى المشجعين</b>. مب تسجيل، وإذا خليته فاضي يطلع «مشجع».</p>
    <button class="fz-ok" type="button"></button>
    <div class="fz-row"><button class="fz-link fz-none" type="button"${locked||cur===''?' style="visibility:hidden"':''}>ما أشجع نادي معيّن</button><button class="fz-link fz-close" type="button" style="opacity:.7">${edit?'إغلاق':'بعدين'}</button></div>
    <div class="fz-mv">${edit?'<button class="fz-link fz-mk" type="button">📲 انقل بطاقتك لتلفون ثاني</button>':''}<button class="fz-link fz-gt" type="button">${edit?'عندي رمز نقل':'📲 عندي رمز نقل من تلفون ثاني'}</button></div></div></div>`;
  document.body.appendChild(bg);
  const ok=bg.querySelector('.fz-ok');
  const upd=()=>{ok.disabled=!pick;ok.textContent=pick?(edit&&pick===cur?'حفظ':'أنا مع جمهور '+CL[pick]+' 💪'):'اختار ناديك'};upd();
  bg.querySelectorAll('.fz-grid button').forEach(b=>b.onclick=()=>{if(b.disabled)return;pick=b.dataset.c;bg.querySelectorAll('.fz-grid button').forEach(x=>x.classList.toggle('on',x===b));upd();try{navigator.vibrate&&navigator.vibrate(12)}catch(e){}});
  const close=()=>bg.remove();
  bg.onclick=e=>{if(e.target===bg)close()};
  bg.querySelector('.fz-close').onclick=close;
  bg.querySelector('.fz-none').onclick=()=>{set('',bg.querySelector('.fz-name').value);close()};
  ok.onclick=()=>{if(!pick)return;set(pick,bg.querySelector('.fz-name').value);close()};
  const mk=bg.querySelector('.fz-mk');if(mk)mk.onclick=()=>moveOut(bg);
  bg.querySelector('.fz-gt').onclick=()=>moveIn(bg);
  if(edit)profile(bg,close);
}
const TILE='<div class="fz-tile"><svg viewBox="0 0 32 32" fill="none" stroke="#D7B465" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="5" width="11" height="20" rx="2.5" fill="rgba(215,180,101,.25)"/><rect x="17" y="7" width="11" height="20" rx="2.5"/><path d="M12 15h8m-2.5-2.5L20 15l-2.5 2.5"/></svg></div>';
async function moveOut(bg){
  const sh=bg.querySelector('.fz-sh');sh.innerHTML=TILE+'<h2>انقل بطاقتك</h2><p class="fz-why">لحظة، نجهز الرمز...</p>';
  let m;try{m=await makeCode()}catch(e){sh.innerHTML=TILE+'<h2>انقل بطاقتك</h2><p class="fz-err">ما قدرنا نسوي الرمز، تأكد من الإنترنت وجرب مرة ثانية.</p><button class="fz-link fz-close" type="button">إغلاق</button>';sh.querySelector('.fz-close').onclick=()=>bg.remove();return}
  const link=location.origin+'/#nql='+m.code;
  sh.innerHTML=TILE+`<h2>انقل بطاقتك</h2>
    <p class="fz-why">في التلفون الثاني (أو المتصفح الثاني) افتح <b>el3azy.com</b>،<br>واضغط بطاقة المشجع ← <b>«عندي رمز نقل»</b> واكتب:</p>
    <div class="fz-code">${fmtCode(m.code)}</div>
    <p class="fz-lock">⏳ ينتهي بعد <b class="fz-t"></b> · ينستخدم مرة وحدة · لا ترسله لأحد</p>
    <button class="fz-ok fz-cc" type="button">انسخ الرمز</button>
    <p class="fz-hint" style="margin-top:10px">تنقل من X إلى سفاري في نفس التلفون؟ <button class="fz-link fz-cp" type="button" style="padding:2px;font-size:12px">انسخ رابط النقل</button><br>والصقه في سفاري، وينفتح الرمز جاهز.</p>
    <p class="fz-hint">نقاطك وناديك وتوقعاتك تنتقل كلها، وتقدر تلعب من الثنين.</p>
    <div class="fz-row" style="justify-content:center"><button class="fz-link fz-close" type="button">تم</button></div>`;
  const t=sh.querySelector('.fz-t'),tk=()=>{const s=Math.max(0,Math.round((m.e-Date.now())/1e3));if(!document.body.contains(t)){clearInterval(iv);return}t.textContent=`${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;if(!s){clearInterval(iv);t.textContent='انتهى'}},iv=setInterval(tk,1000);tk();
  const cp=async(t,btn,done)=>{try{await navigator.clipboard.writeText(t);btn.textContent=done}catch(_){prompt('انسخ:',t)}};
  sh.querySelector('.fz-cc').onclick=e=>cp(fmtCode(m.code),e.target,'✓ تم نسخ الرمز');
  sh.querySelector('.fz-cp').onclick=e=>cp(link,e.target,'✓ تم نسخ الرابط');
  sh.querySelector('.fz-close').onclick=()=>bg.remove();
}
function moveIn(bg,pre){
  if(!bg){addCss();bg=document.createElement('div');bg.className='fz-bg';bg.innerHTML='<div class="fz-sh" role="dialog" aria-modal="true"></div>';document.body.appendChild(bg);bg.onclick=e=>{if(e.target===bg)bg.remove()}}
  const sh=bg.querySelector('.fz-sh'),had=club()!==null;
  sh.innerHTML=TILE+`<h2>عندي رمز نقل</h2>
    <p class="fz-why">اكتب الرمز اللي طلع لك في تلفونك الثاني<br>(بطاقة المشجع ← «انقل بطاقتك لتلفون ثاني»).</p>
    <input class="fz-name fz-in" placeholder="XXXX-XXXX" autocomplete="off" autocapitalize="characters" spellcheck="false" value="${pre?fmtCode(pickCode(pre)):''}">
    <p class="fz-err"></p>
    ${had?'<p class="fz-hint">البطاقة اللي في هالتلفون بتتبدل بالبطاقة اللي تنقلها.</p>':''}
    <button class="fz-ok fz-go" type="button">انقل البطاقة</button>
    <div class="fz-row" style="justify-content:center"><button class="fz-link fz-close" type="button" style="opacity:.7">إلغاء</button></div>`;
  const inp=sh.querySelector('.fz-in'),go=sh.querySelector('.fz-go'),err=sh.querySelector('.fz-err');
  inp.oninput=()=>{const c=pickCode(inp.value);inp.value=c.length>4?fmtCode(c):c;err.textContent=''};
  sh.querySelector('.fz-close').onclick=()=>bg.remove();
  go.onclick=async()=>{if(pickCode(inp.value).length!==8){err.textContent='الرمز 8 حروف وأرقام';return}
    go.disabled=true;go.textContent='لحظة...';
    try{const f=await useCode(pickCode(inp.value));
      sh.innerHTML=TILE+`<h2>رجعت لك بطاقتك ✅</h2><p class="fz-why">${f&&f.c&&f.c!=='none'?`جمهور <b>${CL[f.c]||''}</b>${f.n?' · '+esc(f.n):''}<br>`:''}نقاطك وتوقعاتك كلها هني.</p>`;
      setTimeout(()=>location.reload(),1400)}
    catch(e){go.disabled=false;go.textContent='انقل البطاقة';err.textContent=e.message==='net'?'ما قدرنا نكمل، تأكد من الإنترنت وجرب مرة ثانية':'الرمز غلط أو انتهى. سو رمز جديد من تلفونك الثاني'}};
  if(!pre)setTimeout(()=>inp.focus(),50);
}

function chipHTML(){const c=club(),n=name();
  if(c===null)return '';
  return (c?crest(c,24)+`<span>${CL[c]}</span>`:`<span class="fz-ball">⚽</span><span>محايد</span>`)+(n?`<small>· ${esc(n)}</small>`:'')}
function render(){
  addCss();const c=club();try{banner()}catch(e){}
  // الشعار فوق: في شريط الأقسام، أو أعلى الصفحة الرئيسية
  document.querySelectorAll('.fz-chip').forEach(e=>e.remove());document.querySelectorAll('.fz-top').forEach(e=>e.remove());
  if(c!==null){
    const chip=document.createElement('a');chip.className='fz-chip';chip.setAttribute('role','button');chip.setAttribute('aria-label','بطاقة المشجع');chip.innerHTML=chipHTML();chip.onclick=e=>{e.preventDefault();open()};
    const nav=document.querySelector('.topnav');
    if(nav){nav.style.justifyContent='space-between';nav.insertBefore(chip,nav.firstChild);
      requestAnimationFrame(()=>{const cut=[...chip.querySelectorAll('span,small')].some(e=>e.scrollWidth>e.clientWidth+1);const sm=chip.querySelector('small');if(cut&&sm)sm.style.display='none'})} // المساحة ضيقة: اسم النادي أولى من اسم المشجع
    else{const w=document.querySelector('.wrap');if(w){let h=w.querySelector('.fz-top');if(!h){h=document.createElement('div');h.className='fz-top';w.insertBefore(h,w.firstChild)}h.appendChild(chip)}}
  }
  // بطاقة «تشجع أي نادي انت؟» فوق «منو اللاعب؟» في الصفحة الرئيسية
  const feat=document.getElementById('fanSlot')||document.getElementById('feat');let card=document.querySelector('.fz-card');
  if(c===null&&feat){if(!card){card=document.createElement('a');card.className='tool fz-card';card.setAttribute('role','button');card.href='#';
      card.innerHTML=`<div class="ic">${'<svg viewBox="2.6 2.6 26.8 26.8" fill="none" stroke="url(#gg)" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5.5 5.6q5.3-1.9 10.5 0t10.5 0v4.6q-5.3 1.9-10.5 0t-10.5 0z" class="s"/><path d="M10.8 4.7v4.5M16 5.6v4.6M21.2 6.6v4.5" stroke-width="1.3"/><path d="M5.5 6.6H3.4M5.5 9.2H3.4M26.5 6.6h2.1M26.5 9.2h2.1" stroke-width="1.2"/><circle cx="16" cy="16.3" r="2.7"/><path d="M11.6 21.2 7.6 10.6M20.4 21.2l4-10.6"/><path d="M10.6 28v-3.2a5.4 5.4 0 0 1 10.8 0V28"/></svg>'}</div><div><b>تشجع أي نادي انت؟</b><span class="d">اختار ناديك، ونتيجتك في التحديات تنحسب لجمهوره</span></div><div class="go">‹</div>`;
      card.onclick=e=>{e.preventDefault();open()};feat.parentNode.insertBefore(card,feat)}}
  else if(card)card.remove();
}
/* ---------- تنبيه المكان (قرار إبراهيم 20 نوفمبر) ----------
   داخل متصفح X وغيره: البطاقة ممكن تنمسح لما يسكّر التطبيق → «داخل X ممكن تضيع بطاقتك» (يختفي لين باجر لو سكّره).
   سفاري الآيفون: يمسح بيانات الموقع لو ما انفتح 7 أيام → «حط المنصة على شاشتك» (يختفي شهر). من الأيقونة ما يطلع شي */
const UA=navigator.userAgent||'';
const INAPP=[[/Twitter/i,'X'],[/Instagram/,'انستقرام'],[/Snapchat/,'سناب'],[/musical_ly|TikTok|BytedanceWebview/,'تيك توك'],[/FBAN|FBAV|FB_IAB/,'فيسبوك']].find(([r])=>r.test(UA));
const IOSSAF=!INAPP&&/iP(hone|ad|od)/.test(UA)&&/Safari\//.test(UA)&&!/CriOS|FxiOS|EdgiOS|OPiOS|GSA\//.test(UA)&&!navigator.standalone&&!(window.matchMedia&&matchMedia('(display-mode: standalone)').matches);
const wbCss=`.fz-wb{margin:8px 0 2px;padding:7px 12px;border-radius:12px;border:1px solid rgba(215,180,101,.4);background:rgba(11,34,50,.85);display:flex;gap:8px;align-items:center;font:400 12.5px 'Readex Pro',system-ui,sans-serif;color:#FFF5E5;white-space:nowrap;direction:rtl}
.fz-wb>span{flex:1;overflow:hidden;text-overflow:ellipsis}.fz-wb .fz-link{font-weight:700;padding:2px 4px;font-size:12.5px}.fz-wb .wb-x{background:none;border:0;color:#FFF5E5;opacity:.45;font-size:16px;padding:0 2px;cursor:pointer}
.fz-steps{text-align:right;font-size:13.5px;line-height:1.8;margin:4px 0 12px;padding:0;list-style:none;counter-reset:s}
.fz-steps li{counter-increment:s;display:flex;gap:10px;align-items:flex-start;padding:7px 0;border-bottom:1px solid rgba(215,180,101,.12)}
.fz-steps li:before{content:counter(s);flex:none;width:24px;height:24px;border-radius:50%;display:grid;place-items:center;background:#D7B465;color:#0B2232;font-weight:700;font-size:13px;margin-top:2px}`;
function wbHow(){addCss();const bg=document.createElement('div');bg.className='fz-bg';const has=club()!==null;
  const op=`اضغط <b>⋯</b> أو <b>🧭</b> فوق، واختار <b>«فتح في المتصفح»</b>`,st=INAPP?(has?[`اضغط <b>«انقل بطاقتك»</b> تحت، وانسخ الرمز`,op,`في سفاري: <b>بطاقة المشجع</b> ← <b>«عندي رمز نقل»</b> والصق الرمز`]:[op,`في سفاري: <b>مشاركة</b> ← <b>«إضافة إلى الشاشة الرئيسية»</b>`])
    :[`اضغط <b>مشاركة</b> تحت`,`اختار <b>«إضافة إلى الشاشة الرئيسية»</b> ← <b>إضافة</b>`,has?`افتح المنصة من الأيقونة، وانقل بطاقتك لها برمز النقل`:`افتح المنصة من الأيقونة`];
  bg.innerHTML=`<div class="fz-sh" role="dialog" aria-modal="true"><h2>${INAPP?'افتحها برا '+INAPP[1]:'حط المنصة على شاشتك'}</h2>
    <p class="fz-why">${INAPP?'المتصفح اللي داخل التطبيق ممكن يمسح بطاقتك ونقاطك لما تسكّره':'تفتحها بضغطة وحدة، وبطاقتك تظل محفوظة'}</p>
    <ol class="fz-steps">${st.map(x=>`<li><span>${x}</span></li>`).join('')}</ol>
    ${has?'<button class="fz-ok wb-mv" type="button">📲 انقل بطاقتك</button>':''}<div class="fz-row" style="justify-content:center"><button class="fz-link fz-close" type="button">تم</button></div></div>`;
  document.body.appendChild(bg);bg.onclick=e=>{if(e.target===bg)bg.remove()};bg.querySelector('.fz-close').onclick=()=>bg.remove();
  const mv=bg.querySelector('.wb-mv');if(mv)mv.onclick=()=>moveOut(bg);gc(INAPP?'wb-how-app':'wb-how-saf')}
function banner(){
  if(!(INAPP||IOSSAF)||/\/(bus|admin)\//.test(location.pathname)||document.querySelector('.fz-wb'))return;
  const K=INAPP?'wb_app':'wb_saf',v=PID.get(K);if(v&&Date.now()<v)return;
  if(!document.getElementById('fz-wbcss')){const c=document.createElement('style');c.id='fz-wbcss';c.textContent=wbCss;document.head.appendChild(c)}
  const b=document.createElement('div');b.className='fz-wb';b.setAttribute('role','note');
  b.innerHTML=`<span>${INAPP?`🔐 داخل <bdi>${INAPP[1]}</bdi> ممكن تضيع بطاقتك`:'📲 حط المنصة على شاشتك'}</span><button class="fz-link wb-how" type="button">كيف؟</button><button class="wb-x" type="button" aria-label="إغلاق">×</button>`;
  b.querySelector('.wb-how').onclick=wbHow;
  b.querySelector('.wb-x').onclick=()=>{const t=new Date(Date.now()+4*36e5);PID.set(K,INAPP?Date.UTC(t.getUTCFullYear(),t.getUTCMonth(),t.getUTCDate()+1)-4*36e5:Date.now()+30*864e5);b.remove();gc(INAPP?'wb-x-app':'wb-x-saf')};
  const slot=document.getElementById('fanSlot'),nav=document.querySelector('.wrap>.topnav');
  if(slot)slot.parentNode.insertBefore(b,slot);else if(nav)nav.after(b);else return;
  gc(INAPP?'wb-show-app':'wb-show-saf')}
window.EL3FAN={club,name,set,open,render,sync,tok,lock};
const go=()=>{render();sync();
  const m=location.hash.match(/nql=([A-Za-z0-9-]{8,9})/);if(m){history.replaceState(null,'',location.pathname+location.search);moveIn(null,m[1])}};
document.readyState==='loading'?document.addEventListener('DOMContentLoaded',go):go();
})();
