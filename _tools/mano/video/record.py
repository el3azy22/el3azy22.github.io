# يسجل فيديو شرح منو اللاعب 1080x1920 عبر CDP screencast (شغّل http.server 8765 من جذر المستودع)
import asyncio,json,base64,os,shutil,sys
from playwright.async_api import async_playwright
OUT=sys.argv[1] if len(sys.argv)>1 else '/tmp/frames'
DUR=45
async def main():
  shutil.rmtree(OUT,ignore_errors=True);os.makedirs(OUT)
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx=await b.new_context(viewport={'width':1080,'height':1920},device_scale_factor=1)
    await ctx.add_init_script("""(()=>{const T=Date.UTC(2026,10,17,6,0,0);const R=Date;class FD extends R{constructor(...a){if(a.length)super(...a);else super(T)}static now(){return T}};window.Date=FD;})()""")
    async def fix(route):
      r=await route.fetch();d=await r.json();d['schedule'][0]='renato-fabrizio-tapia-cortijo'
      await route.fulfill(response=r,body=json.dumps(d,ensure_ascii=False),headers={**r.headers,'content-type':'application/json'})
    await ctx.route('**/mano/data.json*',fix)
    pg=await ctx.new_page()
    await pg.goto('http://localhost:8765/_tools/mano/video/stage.html')
    await pg.wait_for_function('window.ready===true');await pg.evaluate("document.fonts.ready");await pg.wait_for_timeout(2000)
    cdp=await ctx.new_cdp_session(pg);frames=[]
    async def on(f):
      frames.append((f['metadata']['timestamp'],f['data']))
      try: await cdp.send('Page.screencastFrameAck',{'sessionId':f['sessionId']})
      except Exception: pass
    cdp.on('Page.screencastFrame',lambda f: asyncio.ensure_future(on(f)))
    await cdp.send('Page.startScreencast',{'format':'jpeg','quality':92,'maxWidth':1080,'maxHeight':1920,'everyNthFrame':1})
    await pg.wait_for_timeout(300)
    t0=frames[-1][0] if frames else None
    import time;ts=time.time();await pg.evaluate('start()')
    await pg.wait_for_timeout(DUR*1000)
    await cdp.send('Page.stopScreencast')
    await b.close()
  # start reference: wall time of start() mapped to screencast timestamps ~ first frame after call
  lst=[]
  start=[t for t,_ in frames if t>=frames[0][0]]
  for i,(t,d) in enumerate(frames):
    open(f'{OUT}/{i:05d}.jpg','wb').write(base64.b64decode(d));lst.append(t)
  json.dump({'ts':lst,'start':ts},open(f'{OUT}/ts.json','w'))
  print(len(lst),'frames',lst[-1]-lst[0],'s')
asyncio.run(main())
