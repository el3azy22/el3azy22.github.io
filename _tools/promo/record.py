# يسجل stage.html (فيديو منصة العازي الترويجي) لقطات بتوقيتها عن طريق CDP screencast
#   python3 record.py /home/claude/promo/frames            ← تسجيل كامل
#   python3 record.py /home/claude/promo/shots --shots 3,9,15   ← صور فحص بس عند هالثواني
#   --from 18 يبدا من ثانية معينة (بداية مشهد) · --dur 12 يسجل مدة معينة
import asyncio,json,base64,os,shutil,sys,argparse
from playwright.async_api import async_playwright
HERE=os.path.dirname(os.path.abspath(__file__))
TLF=os.environ.get('TL','timeline.json');STAGE=os.environ.get('STAGE','stage.html')   # فيديو ثاني: TL=rate-timeline.json STAGE=rate-stage.html
TL=json.load(open(os.path.join(HERE,TLF),encoding='utf-8'))
RD=json.load(open(os.path.join(HERE,TL['demo']['rateDemo']),encoding='utf-8')) if TL['demo'].get('rateDemo') else None
ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--shots',default='');ap.add_argument('--from',dest='frm',type=float,default=0)
ap.add_argument('--dur',type=float,default=None);ap.add_argument('--base',default='http://localhost:8765');A=ap.parse_args()
DUR=A.dur if A.dur else TL['duration']-A.frm+0.6
# بيانات عرض لنسبة الجماهير وتحدي الأندية (ما نلمس Firebase الحقيقي)
S={"n":1240,"w":781,"g1":40,"g2":60,"g3":87,"g4":250,"g5":200,"g6":144}
AVG={'ain':4.6,'wahda':4.4,'jazira':4.1,'shababahli':4.3,'sharjah':3.9,'wasl':4.5,'nasr':3.8,'baniyas':3.5,'ajman':3.2,'kalba':3.0,'khorfakkan':3.3,'dhafra':2.9,'hatta':2.8,'united':3.1}
NS={'ain':180,'wahda':150,'jazira':120,'shababahli':110,'sharjah':95,'wasl':160,'nasr':85,'baniyas':60,'ajman':45,'kalba':40,'khorfakkan':38,'dhafra':30,'hatta':25,'united':28}
C={"1":{"pro":{k:{"n":NS[k],"t":round(NS[k]*AVG[k])} for k in AVG},"easy":{k:{"n":NS[k],"t":round(NS[k]*AVG[k])} for k in AVG}}}
async def main():
  shutil.rmtree(A.out,ignore_errors=True);os.makedirs(A.out)
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--autoplay-policy=no-user-gesture-required','--mute-audio'])
    ctx=await b.new_context(viewport={'width':1080,'height':1920},device_scale_factor=1)
    # التاريخ ثابت على 17 نوفمبر 2026 (يوم انطلاق منو اللاعب؟) + ما يسأل عن النادي (صوت المتصفح نفسه مكتوم)
    await ctx.add_init_script("""(()=>{const T=%s;const R=Date;class FD extends R{constructor(...a){if(a.length)super(...a);else super(T)}static now(){return T}};window.Date=FD;
      try{localStorage.setItem('el3azy_mano_club','""');localStorage.setItem('el3azy_rate_seenHow','true');localStorage.setItem('el3azy_mano_sound','true')}catch(e){}})()"""%(TL['demo'].get('nowMs','Date.UTC(2026,10,17,17,0,0)')))
    async def fix(route):  # لاعب العرض بدل لاعب اليوم الحقيقي (عشان ما ينحرق أول تحدي)
      r=await route.fetch();d=await r.json();d['schedule'][0]=TL['demo']['manoAnswer']
      await route.fulfill(response=r,body=json.dumps(d,ensure_ascii=False),headers={**r.headers,'content-type':'application/json'})
    await ctx.route('**/mano/data.json*',fix)
    await ctx.route('**/identitytoolkit.googleapis.com/**',lambda r:r.fulfill(status=200,content_type='application/json',body='{"idToken":"x","refreshToken":"y","localId":"demo","expiresIn":"3600"}'))
    async def fb(route):
      u=route.request.url
      if route.request.method in('PATCH','PUT','POST'): return await route.fulfill(status=200,content_type='application/json',body='{}')
      if RD:
        for k in ('ra','rs','rn'):
          if f'/{k}/' in u: return await route.fulfill(status=200,content_type='application/json',body=json.dumps(RD['fb'][k]))
          if u.split('?')[0].endswith(f'/{k}.json'): return await route.fulfill(status=200,content_type='application/json',body=json.dumps({RD['key']:RD['fb']['rn']}))
      if '/s/' in u: return await route.fulfill(status=200,content_type='application/json',body=json.dumps(S))
      if '/c.json' in u: return await route.fulfill(status=200,content_type='application/json',body=json.dumps(C))
      await route.fulfill(status=200,content_type='application/json',body='null')
    await ctx.route('**/*firebasedatabase.app/**',fb)
    if RD: await ctx.route('**/rate/data.json*',lambda r:r.fulfill(status=200,content_type='application/json',body=json.dumps(RD['data'],ensure_ascii=False)))
    await ctx.route('**/goatcounter.com/**',lambda r:r.fulfill(status=200,body=''))
    await ctx.route('**/gc.zgo.at/**',lambda r:r.fulfill(status=200,content_type='text/javascript',body=''))
    pg=await ctx.new_page()
    pg.on('console',lambda m:print('[console]',m.type,m.text[:200]) if m.type=='error' else None)
    await pg.goto(A.base+'/_tools/promo/'+STAGE)
    await pg.wait_for_function('window.ready===true',timeout=60000);await pg.wait_for_timeout(1500)
    print('prep:',await pg.evaluate('prep()'));await pg.wait_for_timeout(1500)
    if A.shots:
      ts=sorted(float(x) for x in A.shots.split(','));frm=A.frm
      import time;await pg.evaluate(f'start({frm})');w0=time.time()-frm
      for s in ts:
        await pg.wait_for_timeout(max(0,(s-(time.time()-w0))*1000))
        await pg.screenshot(path=f'{A.out}/t{s:05.1f}.jpg',quality=88,type='jpeg')
      await b.close();print('shots',len(ts));return
    cdp=await ctx.new_cdp_session(pg);frames=[]
    async def on(f):
      frames.append((f['metadata']['timestamp'],f['data']))
      try: await cdp.send('Page.screencastFrameAck',{'sessionId':f['sessionId']})
      except Exception: pass
    cdp.on('Page.screencastFrame',lambda f: asyncio.ensure_future(on(f)))
    await cdp.send('Page.startScreencast',{'format':'jpeg','quality':93,'maxWidth':1080,'maxHeight':1920,'everyNthFrame':1})
    await pg.wait_for_timeout(400)
    t0=await pg.evaluate(f'start({A.frm})')   # لحظة الثانية صفر من الخط الزمني (epoch)
    await pg.wait_for_timeout(DUR*1000)
    await cdp.send('Page.stopScreencast');await b.close()
  lst=[]
  for i,(t,d) in enumerate(frames):
    open(f'{A.out}/{i:05d}.jpg','wb').write(base64.b64decode(d));lst.append(t)
  json.dump({'ts':lst,'t0':t0,'from':A.frm},open(f'{A.out}/ts.json','w'))
  gaps=[b-a for a,b in zip(lst,lst[1:])]
  print(len(lst),'frames · avg fps %.1f · max gap %.0f ms'%(len(gaps)/max(1e-9,lst[-1]-lst[0]),1000*max(gaps)))
asyncio.run(main())
