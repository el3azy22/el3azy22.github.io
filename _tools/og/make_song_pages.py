"""يسوي لكل أغنية صفحة مشاركة خاصة: /songs/<id>/ فيها صورة معاينة X بغلاف الأغنية وشعار ناديها،
وتحوّل الزائر لـ /songs/?s=<id>، ويسوي نسخة فيديو (mp4) بالغلاف للحفظ في الاستديو. شغّله بعد إضافة أي أغنية في songs/songs.json (والسيرفر شغال على 8765 من جذر المستودع):
  python3 -m http.server 8765 &   python3 _tools/og/make_song_pages.py"""
import asyncio,json,html,os
from playwright.async_api import async_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CL={'ain':'العين','wahda':'الوحدة','jazira':'الجزيرة','shababahli':'شباب الأهلي','sharjah':'الشارقة','wasl':'الوصل','nasr':'النصر','baniyas':'بني ياس','ajman':'عجمان','kalba':'كلباء','khorfakkan':'خورفكان','dhafra':'الظفرة','hatta':'حتا','united':'يونايتد'}
PAGE='''<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{t} — منصة العازي</title>
<link rel="canonical" href="https://el3azy.com/songs/{id}/">
<meta name="description" content="{d}">
<meta property="og:title" content="{t} — منصة العازي">
<meta property="og:description" content="{d}">
<meta property="og:image" content="https://el3azy.com/songs/{id}/og.jpg?v={v}">
<meta property="og:url" content="https://el3azy.com/songs/{id}/">
<meta property="og:type" content="music.song">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@el3azy22">
<meta name="theme-color" content="#071D2B">
<script>location.replace('../?s={id}')</script>
<style>body{{margin:0;background:#071D2B;color:#FFF5E5;font:18px system-ui;display:grid;place-items:center;height:100vh}}a{{color:#D7B465}}</style>
</head><body><a href="../?s={id}">🎵 {t}</a></body></html>
'''
async def main():
  d=json.load(open(os.path.join(ROOT,'songs/songs.json'),encoding='utf-8'))
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome')
    pg=await b.new_page(viewport={'width':1200,'height':630})
    for s in d['songs']:
      if not s.get('file'):continue
      dr=os.path.join(ROOT,'songs',s['id']);os.makedirs(dr,exist_ok=True)
      await pg.goto(f"http://localhost:8765/_tools/og/song-og.html?id={s['id']}");await pg.wait_for_selector('body[data-ok]');await pg.wait_for_timeout(900)
      await (await pg.query_selector('#og')).screenshot(path=os.path.join(dr,'og.png'))
      from PIL import Image
      Image.open(os.path.join(dr,'og.png')).convert('RGB').save(os.path.join(dr,'og.jpg'),quality=88);os.remove(os.path.join(dr,'og.png'))
      who=('أغنية '+CL[s['club']]) if s.get('club') else 'أغنية دوري أدنوك للمحترفين'
      desc=f"«{s['title']}» {who}. اسمعها ونزّلها مجاناً على منصة العازي."
      v=str(abs(hash(json.dumps(s,ensure_ascii=False)))%10**6)
      open(os.path.join(dr,'index.html'),'w',encoding='utf-8').write(PAGE.format(t=html.escape(s['title']),d=html.escape(desc),id=s['id'],v=v))
      mp4=os.path.join(ROOT,'songs',s['file'].replace('.mp3','.mp4'))   # نسخة فيديو بالغلاف للحفظ في الاستديو
      if not os.path.exists(mp4):
        import subprocess
        subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-framerate','5','-i',os.path.join(ROOT,'songs',s['cover']),'-i',os.path.join(ROOT,'songs',s['file']),'-map','0:v','-map','1:a','-vf','scale=1080:1080,format=yuv420p','-c:v','libx264','-preset','veryfast','-tune','stillimage','-crf','24','-r','5','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart','-metadata','title='+s['title'],'-metadata','artist=العازي',mp4],check=True)
      print('✓',s['id'])
    await b.close()
asyncio.run(main())
