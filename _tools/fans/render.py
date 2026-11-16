"""يصوّر صورة «دوري الجماهير» الأسبوعية (fans/week.png بدقة 2160x2700) من fans/week.html، وصورة معاينة الصفحة (fans/og.jpg) لو مب موجودة.
التشغيل من جذر المستودع بعد _tools/fans/build.py:  python3 _tools/fans/render.py   (يحتاج playwright + chromium)"""
import asyncio, json, os, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PORT = 8799


async def main():
    d = json.load(open(os.path.join(ROOT, 'fans/data.json'), encoding='utf8'))
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    try:
        async with async_playwright() as p:
            exe = os.environ.get('CHROME')
            b = await (p.chromium.launch(executable_path=exe) if exe else p.chromium.launch())
            if d.get('done'):
                pg = await b.new_page(viewport={'width': 1080, 'height': 1350}, device_scale_factor=2)
                await pg.goto(f'http://localhost:{PORT}/fans/week.html')
                await pg.wait_for_selector('body[data-ok="1"]', timeout=20000)
                await pg.wait_for_timeout(1200)
                await (await pg.query_selector('#card')).screenshot(path=os.path.join(ROOT, 'fans/week.png'))
                json.dump({'w': d['done'], 'story': d.get('story', '')}, open(os.path.join(ROOT, 'fans/week.json'), 'w', encoding='utf8'), ensure_ascii=False)
                print('fans/week.png ✓ الجولة', d['done'])
            og = os.path.join(ROOT, 'fans/og.jpg')
            if not os.path.exists(og):
                pg = await b.new_page(viewport={'width': 1200, 'height': 630})
                await pg.goto(f'http://localhost:{PORT}/_tools/og/fans-og.html')
                await pg.wait_for_selector('body[data-ok]')
                await pg.wait_for_timeout(800)
                await (await pg.query_selector('#og')).screenshot(path=og.replace('.jpg', '.png'))
                from PIL import Image
                Image.open(og.replace('.jpg', '.png')).convert('RGB').save(og, quality=88)
                os.remove(og.replace('.jpg', '.png'))
                print('fans/og.jpg ✓')
            await b.close()
    finally:
        srv.terminate()

asyncio.run(main())
