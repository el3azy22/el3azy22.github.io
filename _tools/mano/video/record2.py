# يسجل مقاطع المرحلة ٢ (نسبة الجماهير + تحدي الأندية) + لقطة الأساطير + النهاية بالباركود، ببيانات عرض
import asyncio,json,base64,os,shutil,sys,time,re
from playwright.async_api import async_playwright
OUT=sys.argv[1] if len(sys.argv)>1 else '/tmp/frames2';DUR=float(sys.argv[2]) if len(sys.argv)>2 else 22
S={"n":1240,"w":781,"g1":40,"g2":60,"g3":87,"g4":250,"g5":200,"g6":144}
AVG={'ain':4.6,'wahda':4.4,'jazira':4.1,'shababahli':4.3,'sharjah':3.9,'wasl':4.5,'nasr':3.8,'baniyas':3.5,'ajman':3.2,'kalba':3.0,'khorfakkan':3.3,'dhafra':2.9,'hatta':2.8,'united':3.1}
NS={'ain':180,'wahda':150,'jazira':120,'shababahli':110,'sharjah':95,'wasl':160,'nasr':85,'baniyas':60,'ajman':45,'kalba':40,'khorfakkan':38,'dhafra':30,'hatta':25,'united':28}
C={"1":{"pro":{k:{"n":NS[k],"t":round(NS[k]*AVG[k])} for k in AVG}}}
async def main():
  shutil.rmtree(OUT,ignore_errors=True);os.makedirs(OUT)
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx=await b.new_context(viewport={'width':1080,'height':1920},device_scale_factor=1)
    await ctx.add_init_script("""(()=>{const T=Date.UTC(2026,10,17,17,0,0);const R=Date;class FD extends R{constructor(...a){if(a.length)super(...a);else super(T)}static now(){return T}};window.Date=FD;
      try{localStorage.setItem('el3azy_mano_club','"wasl"');localStorage.setItem('el3azy_mano_sound','false')}catch(e){}})()""")
    async def fix(route):
      r=await route.fetch();d=await r.json();d['schedule'][0]='renato-fabrizio-tapia-cortijo'
      await route.fulfill(response=r,body=json.dumps(d,ensure_ascii=False),headers={**r.headers,'content-type':'application/json'})
    await ctx.route('**/mano/data.json*',fix)
    await ctx.route('**/identitytoolkit.googleapis.com/**',lambda r:r.fulfill(status=200,content_type='application/json',body='{"idToken":"x","refreshToken":"y","localId":"demo","expiresIn":"3600"}'))
    async def fb(route):
      u=route.request.url
      if route.request.method=='PATCH': return await route.fulfill(status=200,content_type='application/json',body='{}')
      if '/s/' in u: return await route.fulfill(status=200,content_type='application/json',body=json.dumps(S))
      if '/c.json' in u: return await route.fulfill(status=200,content_type='application/json',body=json.dumps(C))
      await route.fulfill(status=200,content_type='application/json',body='null')
    await ctx.route('**/*firebasedatabase.app/**',fb)
    await ctx.route('**/goatcounter.com/**',lambda r:r.fulfill(status=200,body=''))
    pg=await ctx.new_page()
    await pg.goto('http://localhost:8765/_tools/mano/video/stage2.html')
    await pg.wait_for_function('window.ready===true');await pg.evaluate("document.fonts.ready");await pg.wait_for_timeout(1500)
    await pg.evaluate('prep()');await pg.wait_for_timeout(2500)
    cdp=await ctx.new_cdp_session(pg);frames=[]
    async def on(f):
      frames.append((f['metadata']['timestamp'],f['data']))
      try: await cdp.send('Page.screencastFrameAck',{'sessionId':f['sessionId']})
      except Exception: pass
    cdp.on('Page.screencastFrame',lambda f: asyncio.ensure_future(on(f)))
    await cdp.send('Page.startScreencast',{'format':'jpeg','quality':92,'maxWidth':1080,'maxHeight':1920,'everyNthFrame':1})
    await pg.wait_for_timeout(300)
    ts=time.time();await pg.evaluate('start()')
    await pg.wait_for_timeout(DUR*1000)
    await cdp.send('Page.stopScreencast');await b.close()
  lst=[]
  for i,(t,d) in enumerate(frames):
    open(f'{OUT}/{i:05d}.jpg','wb').write(base64.b64decode(d));lst.append(t)
  json.dump({'ts':lst,'start':ts},open(f'{OUT}/ts.json','w'));print(len(lst),'frames')
asyncio.run(main())
