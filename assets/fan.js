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
async function sync(){
  const c=club();if(c===null)return;
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
.fz-sh h2{color:#D7B465;font-size:21px;margin:4px 0 6px}
.fz-sh .fz-why{font-size:13px;opacity:.8;line-height:1.8;margin-bottom:12px}
.fz-sh .fz-why b{color:#D7B465;font-weight:600}
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
.fz-link{background:none;border:0;color:#D7B465;font:400 12.5px 'Readex Pro';text-decoration:underline;padding:6px;cursor:pointer}
`;
function addCss(){if(document.getElementById('fz-css'))return;const s=document.createElement('style');s.id='fz-css';s.textContent=css;document.head.appendChild(s)}

function open(){
  addCss();const cur=club(),edit=cur!==null;let pick=cur||null;
  const L=edit?lock():{free:true},locked=!L.free;
  const hrs=t=>{const h=Math.max(1,Math.ceil((t-Date.now())/36e5));return h===1?'ساعة':h===2?'ساعتين':h<=10?h+' ساعات':h+' ساعة'};
  const note=locked?`🔒 غيّرت ناديك هالموسم، تقدر تغيره الموسم الياي`
    :L.grace?`تقدر تعدل خلال ${hrs(L.grace)}، وبعدها تغيير واحد في الموسم`
    :L.left?`تقدر تغير ناديك مرة وحدة في الموسم`
    :`عندك 24 ساعة تعدل، وبعدها تغيير واحد في الموسم`;
  const bg=document.createElement('div');bg.className='fz-bg';
  bg.innerHTML=`<div class="fz-sh" role="dialog" aria-modal="true">
    <div class="fz-tile"><svg viewBox="2.6 2.6 26.8 26.8" fill="none" stroke="#D7B465" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5.5 5.6q5.3-1.9 10.5 0t10.5 0v4.6q-5.3 1.9-10.5 0t-10.5 0z" fill="rgba(215,180,101,.25)"/><path d="M10.8 4.7v4.5M16 5.6v4.6M21.2 6.6v4.5" stroke-width="1.3"/><path d="M5.5 6.6H3.4M5.5 9.2H3.4M26.5 6.6h2.1M26.5 9.2h2.1" stroke-width="1.2"/><circle cx="16" cy="16.3" r="2.7"/><path d="M11.6 21.2 7.6 10.6M20.4 21.2l4-10.6"/><path d="M10.6 28v-3.2a5.4 5.4 0 0 1 10.8 0V28"/></svg></div>
    <h2>${edit?'بطاقة المشجع':'تشجع أي نادي أنت؟'}</h2>
    <p class="fz-why">نتيجتك في كل أقسام المنصة تنحسب لـ<b>جمهور ناديك</b>،<br>وكل ما لعبت تساعده يتصدر منافسة الجماهير.</p>
    <div class="fz-grid">${ORDER.map(k=>`<button type="button" data-c="${k}" class="${k===pick?'on':''}"${locked&&k!==cur?' disabled':''}>${crest(k,34)}<span>${CL[k]}</span></button>`).join('')}</div>
    <p class="fz-lock">${note}</p>
    <input class="fz-name" maxlength="16" placeholder="اسمك (اختياري)" value="${esc(name())}">
    <p class="fz-hint">اكتب اسمك عشان يطلع في <b>نخبة جمهور ناديك</b> وفي <b>أعلى المشجعين</b>. مب تسجيل، وإذا خليته فاضي يطلع «مشجع».</p>
    <button class="fz-ok" type="button"></button>
    <div class="fz-row"><button class="fz-link fz-none" type="button"${locked||cur===''?' style="visibility:hidden"':''}>ما أشجع نادي معيّن</button><button class="fz-link fz-close" type="button" style="opacity:.7">${edit?'إغلاق':'بعدين'}</button></div></div>`;
  document.body.appendChild(bg);
  const ok=bg.querySelector('.fz-ok');
  const upd=()=>{ok.disabled=!pick;ok.textContent=pick?(edit&&pick===cur?'حفظ':'أنا مع جمهور '+CL[pick]+' 💪'):'اختار ناديك'};upd();
  bg.querySelectorAll('.fz-grid button').forEach(b=>b.onclick=()=>{if(b.disabled)return;pick=b.dataset.c;bg.querySelectorAll('.fz-grid button').forEach(x=>x.classList.toggle('on',x===b));upd();try{navigator.vibrate&&navigator.vibrate(12)}catch(e){}});
  const close=()=>bg.remove();
  bg.onclick=e=>{if(e.target===bg)close()};
  bg.querySelector('.fz-close').onclick=close;
  bg.querySelector('.fz-none').onclick=()=>{set('',bg.querySelector('.fz-name').value);close()};
  ok.onclick=()=>{if(!pick)return;set(pick,bg.querySelector('.fz-name').value);close()};
}

function chipHTML(){const c=club(),n=name();
  if(c===null)return '';
  return (c?crest(c,24)+`<span>${CL[c]}</span>`:`<span class="fz-ball">⚽</span><span>محايد</span>`)+(n?`<small>· ${esc(n)}</small>`:'')}
function render(){
  addCss();const c=club();
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
  const feat=document.getElementById('feat');let card=document.querySelector('.fz-card');
  if(c===null&&feat){if(!card){card=document.createElement('a');card.className='tool fz-card';card.setAttribute('role','button');card.href='#';
      card.innerHTML=`<div class="ic">${'<svg viewBox="2.6 2.6 26.8 26.8" fill="none" stroke="url(#gg)" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5.5 5.6q5.3-1.9 10.5 0t10.5 0v4.6q-5.3 1.9-10.5 0t-10.5 0z" class="s"/><path d="M10.8 4.7v4.5M16 5.6v4.6M21.2 6.6v4.5" stroke-width="1.3"/><path d="M5.5 6.6H3.4M5.5 9.2H3.4M26.5 6.6h2.1M26.5 9.2h2.1" stroke-width="1.2"/><circle cx="16" cy="16.3" r="2.7"/><path d="M11.6 21.2 7.6 10.6M20.4 21.2l4-10.6"/><path d="M10.6 28v-3.2a5.4 5.4 0 0 1 10.8 0V28"/></svg>'}</div><div><b>تشجع أي نادي انت؟</b><span class="d">اختار ناديك، ونتيجتك في التحديات تنحسب لجمهوره</span></div><div class="go">‹</div>`;
      card.onclick=e=>{e.preventDefault();open()};feat.parentNode.insertBefore(card,feat)}}
  else if(card)card.remove();
}
window.EL3FAN={club,name,set,open,render,sync,tok,lock};
const go=()=>{render();sync()};
document.readyState==='loading'?document.addEventListener('DOMContentLoaded',go):go();
})();
