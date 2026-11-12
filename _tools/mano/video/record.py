import asyncio,json,time
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx=await b.new_context(viewport={'width':540,'height':960},device_scale_factor=2,record_video_dir='/tmp/recv',record_video_size={'width':1080,'height':1920})
    await ctx.add_init_script("""(()=>{const T=Date.UTC(2026,10,17,6,0,0);const R=Date;class FD extends R{constructor(...a){if(a.length)super(...a);else super(T)}static now(){return T}};window.Date=FD;})()""")
    async def fix(route):
      r=await route.fetch();d=await r.json();d['schedule'][0]='renato-fabrizio-tapia-cortijo'
      await route.fulfill(response=r,body=json.dumps(d,ensure_ascii=False),headers={**r.headers,'content-type':'application/json'})
    await ctx.route('**/mano/data.json*',fix)
    t0=time.time()
    pg=await ctx.new_page()
    await pg.goto('http://localhost:8765/_tools/mano/video/stage.html')
    await pg.wait_for_function('window.ready===true')
    await pg.evaluate("document.fonts.ready")
    await pg.wait_for_timeout(1500)
    off=time.time()-t0
    await pg.evaluate('start()')
    await pg.wait_for_timeout(37500)
    path=await pg.video.path()
    await ctx.close();await b.close()
    print(off,path)
asyncio.run(main())
