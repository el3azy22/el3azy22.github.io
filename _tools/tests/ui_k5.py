"""اختبار واجهة «خماسي الجولة» (khamsa/) بدون كتابة في Firebase الحقيقي.
- يفتح khamsa/?k5qa ويغيّر الوقت: قبل الفتح، مفتوح، بعد بداية مباراة نادي (قفل لاعب)، وبعد نهاية الجولة (النقاط).
- يمنع googleapis وأي كتابة في Firebase؛ الحفظ يروح لـ mock ونتأكد من شكل الطلب.
- لقطات 360 و390 في /tmp/el3azy-shots/k5_<حالة>_<عرض>.png
"""
import asyncio, json, os, subprocess, sys, time, urllib.request
from playwright.async_api import async_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = '/tmp/el3azy-shots'
BASE = 'http://localhost:8765'
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
        subprocess.Popen(['setsid', sys.executable, '-m', 'http.server', '8765'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)


PD = json.load(open(os.path.join(ROOT, 'predict/data.json'), encoding='utf8'))
OPEN = json.load(open(os.path.join(ROOT, 'predict/open.json'), encoding='utf8'))
CFG = json.load(open(os.path.join(ROOT, 'khamsa/config.json'), encoding='utf8'))
SQ = json.load(open(os.path.join(ROOT, 'tashkila/squads.json'), encoding='utf8'))
FIX = {'shabab': 'shababahli'}
K = lambda p: p[5] or f"{'' if p[0] is None else p[0]}|{p[1]}"
BY = {FIX.get(c['id'], c['id']): c['p'] for c in SQ['clubs']}
# أول جولة من الإطلاق
W = min((int(w) for w, t in OPEN.items() if t >= CFG['launch']), key=lambda w: OPEN[str(w)])
MS = sorted([m for m in PD['matches'] if m['wk'] == W], key=lambda m: m['t'])
OP, FIRST, LAST = OPEN[str(W)], MS[0]['t'], MS[-1]['t']
m0 = MS[0]                       # أول مباراة في الجولة: لاعبه يقفل أول
c0, c1 = m0['h'], MS[1]['h']
pick = lambda c, pos, n=0: K([p for p in BY[c] if p[2] == pos][n])
SAVED = {'c': 'ain', 'cap': 3, 'w': 1, 'p': [{'c': c1, 'k': pick(c1, 'GK')}, {'c': c1, 'k': pick(c1, 'DEF')}, {'c': c0, 'k': pick(c0, 'MID')},
                                          {'c': c0, 'k': pick(c0, 'FWD')}, {'c': MS[2]['h'], 'k': pick(MS[2]['h'], 'MID')}]}
# إحصائيات وهمية بعد الجولة: مهاجم c0 (القائد) سجّل وصنع ونجم المباراة ⇒ (2+4+3+3)×2 = 24 · وسط c0 70 دقيقة وإنذار وشباك نظيفة ⇒ 2
# · حارس c1 شباك نظيفة و4 تصديات ⇒ 7 · مدافع c1 ما لعب ⇒ 0 · الحر 30 دقيقة ⇒ 1   ⇒ المجموع 34
STATS = {'9001': {'t': m0['t'], 'wk': W, 'h': m0['h'], 'a': m0['a'], 'sc': [1, 0], 'ast': 1, 'fm': 1,
                  'p': {SAVED['p'][3]['k']: {'s': 'H', 'm': 90, 'g': 1, 'a': 1, 'b': 3}, SAVED['p'][2]['k']: {'s': 'H', 'm': 70, 'y': 1}}},
         '9002': {'t': MS[1]['t'], 'wk': W, 'h': c1, 'a': MS[1]['a'], 'sc': [0, 0], 'ast': 1, 'p': {SAVED['p'][0]['k']: {'s': 'H', 'm': 90, 'sv': 4}}},
         '9003': {'t': MS[2]['t'], 'wk': W, 'h': MS[2]['h'], 'a': MS[2]['a'], 'sc': [2, 2], 'ast': 1, 'p': {SAVED['p'][4]['k']: {'s': 'H', 'm': 30, 'gc': 1}}}}


async def run(b, T, w, saved, stats=None):
    pg = await b.new_page(viewport={'width': w, 'height': 800}, device_scale_factor=2)
    puts = []
    await pg.add_init_script(f"""
      const __o={T}-Date.now();const __n=Date.now.bind(Date);Date.now=()=>__n()+__o;
      localStorage.setItem('el3azy_club',JSON.stringify('ain'));
      localStorage.setItem('el3azy_fb',JSON.stringify({{t:'x',r:'',u:'qa_k5',exp:Date.now()+36e5}}));
      localStorage.setItem('el3azy_fan_srv',JSON.stringify({{c:'ain',n:'',t:1,x:0}}));""")

    async def fb(route):
        r = route.request
        if r.method in ('PUT', 'PATCH', 'POST', 'DELETE'):
            puts.append((r.url, r.post_data))
            return await route.fulfill(status=200, body='{}')
        if '/k5/' in r.url:
            return await route.fulfill(status=200, body=json.dumps(saved) if saved else 'null', content_type='application/json')
        await route.continue_()
    await pg.route('**/*firebasedatabase.app/**', fb)
    await pg.route('**/*googleapis.com/**', lambda r: r.abort())
    await pg.route('**/gc.zgo.at/**', lambda r: r.abort())
    await pg.route('**/khamsa/stats.json*', lambda r: r.fulfill(status=200, body=json.dumps(stats or {}), content_type='application/json'))
    await pg.goto(BASE + f'/khamsa/?k5qa&w={W}')
    await pg.wait_for_timeout(1800)
    return pg, puts


async def main():
    serve()
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w in (360, 390):
            pg, _ = await run(b, OP - 3600e3, w, None)
            chk('ينطلق بعد' in await pg.text_content('.card'), 'قبل الفتح')
            chk(await pg.locator('.slot').count() == 0, 'الخانات قبل الفتح')
            await pg.screenshot(path=f'{OUT}/k5_soon_{w}.png', full_page=True)
            await pg.close()

            pg, puts = await run(b, OP + 3600e3, w, None)
            chk(await pg.locator('.slot').count() == 5, 'خمس خانات')
            chk(await pg.locator('#go').is_disabled(), 'الاعتماد مفعّل وهو فاضي')
            await pg.screenshot(path=f'{OUT}/k5_empty_{w}.png', full_page=True)
            # الحارس: القائمة فيها حراس بس، والمجموعات مرتبة حسب موعد المباراة
            await pg.locator('.slot').nth(0).click(); await pg.wait_for_timeout(300)
            ks = await pg.locator('#list .pl').evaluate_all('a=>a.map(b=>b.dataset.k)')
            pos = {K(p): p[2] for c in BY.values() for p in c}
            chk(ks and {pos.get(k) for k in ks} == {'GK'}, 'قائمة الحارس فيها غير الحراس')
            await pg.screenshot(path=f'{OUT}/k5_sheet_{w}.png')
            await pg.locator('#list .pl:not([disabled])').first.click(); await pg.wait_for_timeout(200)
            chk(await pg.locator('.slot .cap').count() == 1, 'أول لاعب يصير القائد')
            # المدافع والوسط من نفس نادي الحارس ⇒ الثالث من نفس النادي ممنوع
            first_club = await pg.locator('#list .grp').count()
            for i in (1, 2):
                await pg.locator('.slot').nth(i).click(); await pg.wait_for_timeout(250)
                await pg.locator('#list .pl:not([disabled])').first.click(); await pg.wait_for_timeout(200)
            await pg.locator('.slot').nth(3).click(); await pg.wait_for_timeout(250)
            g0 = (await pg.locator('#list .grp small').first.text_content()).strip()
            chk('عندك لاعبين منه' in g0, f'ثالث لاعب من نفس النادي {g0}')
            await pg.locator('#list .pl:not([disabled])').first.click(); await pg.wait_for_timeout(200)
            # البحث بالإنجليزي في الخانة الحرة
            await pg.locator('.slot').nth(4).click(); await pg.wait_for_timeout(250)
            await pg.fill('#q', 'kaku'); await pg.wait_for_timeout(300)
            names = ' '.join(await pg.locator('#list .pl span:nth-child(2)').all_text_contents())
            chk('كاكو' in names, f'البحث بالاسم المعروف {names[:80]}')
            await pg.fill('#q', ''); await pg.wait_for_timeout(200)
            await pg.locator('#list .pl:not([disabled])').nth(3).click(); await pg.wait_for_timeout(200)
            # القائد: نخلي المهاجم القائد
            await pg.locator('.slot').nth(3).click(); await pg.wait_for_timeout(250)
            await pg.click('#capB'); await pg.wait_for_timeout(200)
            chk(not await pg.locator('#go').is_disabled(), 'الاعتماد ما تفعّل')
            await pg.click('#go'); await pg.wait_for_timeout(800)
            k5 = [x for x in puts if '/k5/' in x[0]]
            chk(len(k5) == 1 and f'/k5/{W}/qa_k5.json' in k5[0][0], f'طلب الحفظ {k5}')
            if k5:
                d = json.loads(k5[0][1])
                chk(d['c'] == 'ain' and d['cap'] == 3 and d['w'] == {'.sv': 'timestamp'} and len(d['p']) == 5, f'شكل الحفظ {d}')
                pos = [next(p[2] for p in BY[v['c']] if K(p) == v['k']) for v in d['p'].values()]
                chk(pos[:4] == ['GK', 'DEF', 'MID', 'FWD'] and pos[4] != 'GK', f'المراكز {pos}')
                cl = [v['c'] for v in d['p'].values()]
                chk(max(cl.count(c) for c in cl) <= 2, f'أكثر من لاعبين من نادي {cl}')
            chk('تم الحفظ' in await pg.text_content('#go'), 'زر بعد الحفظ')
            await pg.screenshot(path=f'{OUT}/k5_saved_{w}.png', full_page=True)
            await pg.close()

            # بعد بداية أول مباراة: لاعبين ناديها مقفولين، والباقي يتبدلون
            pg, _ = await run(b, FIRST + 1800e3, w, SAVED)
            chk(await pg.locator('.slot').nth(2).is_disabled() and await pg.locator('.slot').nth(3).is_disabled(), 'لاعبين النادي اللي بدت مباراته ما انقفلوا')
            chk(not await pg.locator('.slot').nth(0).is_disabled(), 'لاعب ما بدت مباراته انقفل')
            chk(await pg.locator('.slot .lk').count() == 2, 'علامة القفل')
            await pg.locator('.slot').nth(4).click(); await pg.wait_for_timeout(300)
            chk('بدت مباراته' in await pg.text_content('#list'), 'النادي المقفول في القائمة')
            await pg.click('#shClose'); await pg.wait_for_timeout(300)
            await pg.screenshot(path=f'{OUT}/k5_locked_{w}.png', full_page=True)
            await pg.close()

            # بعد الجولة: النقاط
            pg, _ = await run(b, LAST + 4 * 3600e3, w, SAVED, STATS)
            t = await pg.text_content('.res')
            chk('34' in t, f'المجموع (24+2+7+0+1) {t}')
            badges = await pg.locator('.slot .pts').all_text_contents()
            chk(any('+24' in x for x in badges) and any('+7' in x for x in badges) and 'ما لعب' in await pg.text_content('#pitch'), f'نقاط اللاعبين {badges}')
            await pg.screenshot(path=f'{OUT}/k5_done_{w}.png', full_page=True)
            await pg.close()
        await b.close()
    print(f'النتيجة: {ok} نجح · {fail} فشل  (الجولة {W})')
    sys.exit(1 if fail else 0)


asyncio.run(main())
