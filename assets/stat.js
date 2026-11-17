/* عداد الإحصائيات الخاص بمنصة العازي (Firebase v/<يوم>): زيارات، زوار، الزوار العائدون، زيارات كل قسم، وأحداث الأغاني.
   ما يرسل أي بيانات شخصية: زيادة +1 بس على أرقام مجمعة. اليوم بتوقيت الإمارات (اليوم 1 = 17 نوفمبر 2026).
   ما يعد في الاختبارات الآلية (navigator.webdriver) إلا مع ?stattest. */
(()=>{
  const DB='https://el3azy-3b64e-default-rtdb.europe-west1.firebasedatabase.app',S=1794859200000,DAY=864e5;
  const day=Math.floor((Date.now()-S)/DAY)+1;
  const test=/[?&]stattest\b/.test(location.search);
  const on=day>=1&&day<=999&&(test||!navigator.webdriver);
  const inc=p=>{if(!on)return;try{fetch(`${DB}/v/${day}/${p}.json`,{method:'PUT',body:'{".sv":{"increment":1}}',keepalive:true}).catch(()=>{})}catch(e){}};
  window.el3stat=(id,ev)=>{if(/^[a-z0-9-]{1,20}$/.test(id)&&/^(play|dl|share)$/.test(ev))inc(`s/${id}/${ev}`)};
  if(!on)return;
  const seg=(location.pathname.split('/').filter(Boolean)[0]||'home').toLowerCase();
  const sec=['mano','predict','fans','rate','songs','tashkila'].includes(seg)?seg:(seg==='home'||seg==='index.html'?'home':null);
  if(!sec)return;
  let ls=null;try{ls=window.localStorage}catch(e){}
  const get=k=>{try{return ls?ls.getItem(k):null}catch(e){return null}},put=(k,v)=>{try{ls&&ls.setItem(k,v)}catch(e){}};
  inc('t');inc('p/'+sec);
  if(get('el3_vd')!==String(day)){            // أول زيارة لهالتلفون اليوم
    const f0=get('el3_first');let first=f0===null?NaN:+f0;
    // اللي زار المنصة قبل العداد (عنده بطاقة مشجع أو بيانات لعب) ينحسب زار في يوم قبل
    if(isNaN(first)&&ls){for(let i=0;i<ls.length;i++){if(/^el3azy/.test(ls.key(i)||'')){first=day-1;break}}}
    if(isNaN(first))first=day;
    put('el3_first',String(first));put('el3_vd',String(day));
    inc('u');if(first<day)inc('r');
  }
})();
