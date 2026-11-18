"""اختبار واجهة «توقّع تشكيلة ناديك» في صفحة تشكيلتي (بدون كتابة في Firebase الحقيقي).
- يفتح tashkila/?tpqa كأنه مشجع نادي، ويغيّر الوقت عشان يمر على الحالات: قبل الفتح، مفتوح، مقفول، النتيجة.
- يمنع googleapis وأي كتابة في Firebase؛ الحفظ يروح لـ mock ونتأكد من شكل الطلب.
- يحفظ لقطات 360 و390 في /tmp/el3azy-shots/tp_<حالة>_<عرض>.png

  python3 _tools/tests/ui_tp.py [--club wasl]
"""
import asyncio, json, os, subprocess, sys, time, urllib.request
from playwright.async_api import async_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = '/tmp/el3azy-shots'
BASE = 'http://localhost:8765'
CLUB = sys.argv[sys.argv.index('--club') + 1] if '--club' in sys.argv else 'wasl'
TC = {'shababahli': 'shabab'}
ok = fail = 0


def chk(c, m):
    global ok, fail
    if c:
        ok += 1
    else:
        fail += 1
        print('❌', m)


def serve():
    try:
        urllib.request.urlopen(BASE, timeout=2)
    except Exception:
        subprocess.Popen(['setsid', sys.executable, '-m', 'http.server', '8765'], cwd=ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)


PD = json.load(open(os.path.join(ROOT, 'predict/data.json'), encoding='utf8'))
OPEN = json.load(open(os.path.join(ROOT, 'predict/open.json'), encoding='utf8'))
SQ = json.load(open(os.path.join(ROOT, 'tashkila/squads.json'), encoding='utf8'))
M = sorted([m for m in PD['matches'] if CLUB in (m['h'], m['a']) and m['t'] > time.time() * 1000],
           key=lambda m: m['t'])[0]
squad = next(c for c in SQ['clubs'] if c['id'] == TC.get(CLUB, CLUB))['p']
K = lambda p: p[5] or f"{'' if p[0] is None else p[0]}|{p[1]}"
# تشكيلة رسمية وهمية للاختبار: حارس + 10 من بداية القائمة غير الحراس
gk = [p for p in squad if p[2] == 'GK'][:1]
real = [K(p) for p in gk + [p for p in squad if p[2] != 'GK'][:10]]
side = 'hs' if M['h'] == CLUB else 'as'
LU = {M['id']: {'t': M['t'], 'wk': M['wk'], 'h': M['h'], 'a': M['a'], 'hs': [], 'as': [], 'hn': [], 'an': []}}
LU[M['id']][side] = real
# توقع المشجع: 8 صح + 3 غلط
others = [K(p) for p in squad if K(p) not in real and p[2] != 'GK']
mine = real[:8] + others[:3]


async def run(b, state, w, saved):
    T = {'soon': (OPEN.get(str(M['wk'])) or M['t'] - 5 * 864e5) - 3600e3, 'pick': M['t'] - 30 * 3600e3,
         'locked': M['t'] - 3600e3, 'reveal': M['t'] + 3 * 3600e3}[state]
    pg = await b.new_page(viewport={'width': w, 'height': 800}, device_scale_factor=2)
    puts = []
    await pg.add_init_script(f"""
      const __o={T}-Date.now();const __n=Date.now.bind(Date);Date.now=()=>__n()+__o;
      localStorage.setItem('el3azy_club',JSON.stringify('{CLUB}'));
      localStorage.setItem('el3azy_fb',JSON.stringify({{t:'x',r:'',u:'qa_tp',exp:Date.now()+36e5}}));
      localStorage.setItem('el3azy_fan_srv',JSON.stringify({{c:'{CLUB}',n:'',t:1,x:0}}));""")

    async def fb(route):
        r = route.request
        if r.method in ('PUT', 'PATCH', 'POST', 'DELETE'):
            puts.append((r.url, r.post_data))
            return await route.fulfill(status=200, body='{}')
        if '/tp/' in r.url:
            body = json.dumps({'c': CLUB, 'x': '~'.join(mine), 'w': 1}) if saved else 'null'
            return await route.fulfill(status=200, body=body, content_type='application/json')
        await route.continue_()
    await pg.route('**/*firebasedatabase.app/**', fb)
    await pg.route('**/*googleapis.com/**', lambda r: r.abort())
    await pg.route('**/gc.zgo.at/**', lambda r: r.abort())
    if state == 'reveal':
        await pg.route('**/tashkila/lineups.json*', lambda r: r.fulfill(status=200, body=json.dumps(LU), content_type='application/json'))
    await pg.add_init_script("addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');s.textContent='#addDlg,#sheet:not(.on),#veil:not(.on){display:none!important}';document.head.appendChild(s)})")
    await pg.goto(BASE + '/tashkila/?tpqa=tp')
    await pg.wait_for_timeout(1800)
    return pg, puts


async def main():
    serve()
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        # بدون ?tpqa والإطلاق 0: الصفحة مثل ما هي
        pg = await b.new_page()
        await pg.route('**/*firebasedatabase.app/**', lambda r: r.abort() if r.request.method != 'GET' else r.continue_())
        await pg.goto(BASE + '/tashkila/')
        await pg.wait_for_timeout(1200)
        chk(await pg.locator('.tp-tabs').count() == 0, 'التبويب ظاهر قبل الإطلاق')
        chk((await pg.text_content('header h1')).strip() == 'اختار تشكيلتك', 'العنوان تغيّر قبل الإطلاق')
        await pg.close()

        for w in (360, 390):
            pg, puts = await run(b, 'pick', w, False)
            chk(await pg.locator('.tp-tabs').count() == 1, 'ما في تبويبات')
            chk((await pg.text_content('header h1')).strip() == 'تشكيلتي', 'العنوان')
            chk(await pg.locator('#clubs').is_hidden(), 'الأندية ظاهرة في وضع التوقع')
            chk(await pg.locator('#addPlayer').is_hidden(), 'زر الإضافة اليدوية ظاهر')
            chk(await pg.locator('#tpGo').is_disabled(), 'الاعتماد مفعّل بدون 11')
            chk('يقفل بعد' in await pg.text_content('.tp-card'), 'العد التنازلي')
            await pg.screenshot(path=f'{OUT}/tp_pick-empty_{w}.png', full_page=True)
            # نعبي 11 من القائمة
            for i in range(11):
                await pg.locator('#slots .slot').nth(i).click()
                await pg.wait_for_timeout(250)
                chk(await pg.locator('#sheetAdd').is_hidden(), 'إضافة يدوية في القائمة')
                await pg.locator('#list .pl:not([disabled])').first.click()
                await pg.wait_for_timeout(200)
            chk(not await pg.locator('#tpGo').is_disabled(), 'الاعتماد ما تفعّل بعد 11')
            await pg.click('#tpGo')
            await pg.wait_for_timeout(800)
            tp = [x for x in puts if '/tp/' in x[0]]
            chk(len(tp) == 1 and f"/tp/{M['id']}/qa_tp.json" in tp[0][0], f'طلب الحفظ {tp}')
            if tp:
                d = json.loads(tp[0][1])
                chk(d['c'] == CLUB and len(d['x'].split('~')) == 11 and d['w'] == {'.sv': 'timestamp'}, f'شكل الحفظ {d}')
                chk(len(set(d['x'].split('~'))) == 11, 'لاعب مكرر')
            chk('محفوظ' in await pg.text_content('#tpSub'), 'رسالة الحفظ')
            await pg.screenshot(path=f'{OUT}/tp_pick-saved_{w}.png', full_page=True)
            # الرجوع لصمّم تشكيلتك
            await pg.click('.tp-tabs button[data-m=free]')
            await pg.wait_for_timeout(300)
            chk(await pg.locator('#clubs').is_visible() and await pg.locator('.tp-card').count() == 0, 'الرجوع للوضع الحر')
            await pg.close()

            pg, _ = await run(b, 'pick', w, True)
            chk(await pg.locator('#slots .slot:not(.empty)').count() == 11, 'ما رجع التوقع المحفوظ')
            await pg.close()

            pg, _ = await run(b, 'locked', w, True)
            chk('انقفل' in await pg.text_content('.tp-card') and await pg.locator('#tpGo').count() == 0, 'حالة القفل')
            await pg.locator('#slots .slot').first.click()
            await pg.wait_for_timeout(300)
            chk(not await pg.locator('#sheet.on').count(), 'القائمة تنفتح بعد القفل')
            await pg.screenshot(path=f'{OUT}/tp_locked_{w}.png', full_page=True)
            await pg.close()

            pg, _ = await run(b, 'reveal', w, True)
            chk('8' in await pg.text_content('.tp-res .big'), 'النتيجة')
            chk(await pg.locator('.slot.tp-ok').count() == 8 and await pg.locator('.slot.tp-no').count() == 3, 'علامات ✓ ✕')
            chk(await pg.locator('.tp-miss').count() == 1, 'قائمة الأساسيين اللي ما توقعهم')
            await pg.screenshot(path=f'{OUT}/tp_reveal_{w}.png', full_page=True)
            await pg.close()

            if OPEN.get(str(M['wk'])):
                pg, _ = await run(b, 'soon', w, False)
                chk('ينفتح' in await pg.text_content('.tp-card'), 'حالة قبل الفتح')
                await pg.close()
        await b.close()
    print(f'النتيجة: {ok} نجح · {fail} فشل  (نادي {CLUB}، مباراة {M["id"]})')
    sys.exit(1 if fail else 0)


asyncio.run(main())
