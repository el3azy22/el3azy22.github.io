"""لقطات مراجعة منصة العازي بالأرقام الحقيقية (360 و390) قبل أي رفع.
- يقرا ملفات المستودع المحلية (fans/data.json وغيره) عن طريق http.server على 8765.
- يمنع أي كتابة في Firebase الحقيقي، ويقطع googleapis (ما ينشئ حسابات وهمية). القراءة مسموحة.

  python3 _tools/tests/shots.py                      # كل الصفحات
  python3 _tools/tests/shots.py fans fans-xi         # صفحات معيّنة
  python3 _tools/tests/shots.py --club wahda fans-xi # كأنك مشجع من الوحدة داخل تشكيلتها
  الصور في /tmp/el3azy-shots/<صفحة>_<عرض>.png
الصفحات: home mano predict fans fans-xi fans-season fans-pred card week
"""
import asyncio, json, os, subprocess, sys, time, urllib.request
from playwright.async_api import async_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = '/tmp/el3azy-shots'
BASE = 'http://localhost:8765'
PAGES = ['home', 'mano', 'predict', 'fans', 'fans-xi', 'fans-season', 'fans-pred', 'card', 'week']


def serve():
    try:
        urllib.request.urlopen(BASE, timeout=2)
    except Exception:
        subprocess.Popen(['setsid', sys.executable, '-m', 'http.server', '8765'], cwd=ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)


def fan_of(club):
    """مشجع حقيقي من تشكيلة النادي (بدون اسم لو موجود) عشان نشوف سطر «أنت في التشكيلة»."""
    if not club:
        return None
    d = json.load(open(os.path.join(ROOT, 'fans/data.json'), encoding='utf8'))
    w = next((x for x in d['weeks'] if x.get('live')), d['weeks'][-1])
    L = (w['boards']['all'].get('xi') or {}).get(club) or []
    return (next((x for x in L if not x[0]), L[0])[2]) if L else None


async def shot(b, page, w, club, uid):
    pg = await b.new_page(viewport={'width': w, 'height': 800}, device_scale_factor=2)

    async def guard(r):
        if r.request.method in ('PUT', 'PATCH', 'POST', 'DELETE'):
            await r.abort()
        else:
            await r.continue_()
    await pg.route('**firebasedatabase.app/**', guard)
    await pg.route('**googleapis.com/**', lambda r: r.abort())
    init = ''
    if club:
        init += f"localStorage.setItem('el3azy_club',JSON.stringify('{club}'));"
    if uid:
        init += f"localStorage.setItem('el3azy_fb',JSON.stringify({{u:'{uid}',t:'x',exp:9e15}}));"
    if init:
        await pg.add_init_script(init)
    url = {'home': '/', 'mano': '/mano/', 'predict': '/predict/', 'card': '/fans/', 'week': '/fans/week.html'}.get(page, '/fans/')
    if page == 'week':
        await pg.set_viewport_size({'width': 1080, 'height': 1350})
    await pg.goto(BASE + url)
    await pg.wait_for_timeout(2200)
    if page == 'fans-xi' and club:
        await pg.click(f'.tr[data-c="{club}"]')
    if page == 'fans-season':
        await pg.click('#tabs button[data-t="season"]')
        if club:
            await pg.click(f'.tr[data-c="{club}"]')
    if page == 'fans-pred':
        await pg.click('.bseg button[data-b="pred"]')
    if page == 'card':
        await pg.evaluate('EL3FAN.open()')
    await pg.wait_for_timeout(500)
    p = f'{OUT}/{page}_{w if page != "week" else 1080}.png'
    await pg.screenshot(path=p, full_page=page not in ('card', 'week'))
    await pg.close()
    return p


async def main():
    args = sys.argv[1:]
    club = None
    if '--club' in args:
        i = args.index('--club'); club = args[i + 1]; del args[i:i + 2]
    pages = args or PAGES
    os.makedirs(OUT, exist_ok=True)
    serve()
    uid = fan_of(club)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        for page in pages:
            for w in ((1080,) if page == 'week' else (360, 390)):
                print(await shot(b, page, w, club, uid))
                if page == 'week':
                    break
        await b.close()


if __name__ == '__main__':
    asyncio.run(main())
