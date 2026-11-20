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
# «منو بيسجل؟»: هداف المشجع من تشكيلته (مب الحارس) سجّل هدفين ومنهم أول هدف = 3+1+2
SCK = mine[1]
LU[M['id']]['hg' if side == 'hs' else 'ag'] = {SCK: 2}
LU[M['id']].update({'fg': SCK, 'fin': 1})


async def run(b, state, w, saved, lu=None):
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
            body = json.dumps(saved if isinstance(saved, dict) else {'c': CLUB, 'x': '~'.join(mine), 's': SCK, 'w': 1}) if saved else 'null'
            return await route.fulfill(status=200, body=body, content_type='application/json')
        await route.continue_()
    await pg.route('**/*firebasedatabase.app/**', fb)
    await pg.route('**/*googleapis.com/**', lambda r: r.abort())
    await pg.route('**/gc.zgo.at/**', lambda r: r.abort())
    if state == 'reveal':
        await pg.route('**/tashkila/lineups.json*', lambda r: r.fulfill(status=200, body=json.dumps(lu or LU), content_type='application/json'))
    await pg.add_init_script("addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');s.textContent='#addDlg,#sheet:not(.on),#veil:not(.on){display:none!important}';document.head.appendChild(s)})")
    await pg.goto(BASE + '/tashkila/?tpqa=tp')
    await pg.wait_for_timeout(1800)
    return pg, puts


async def share_img(pg, path):
    """نضغط زر المشاركة ونمسك الصورة والنص (navigator.share وهمي)"""
    await pg.evaluate("""()=>{navigator.canShare=()=>true;navigator.share=async d=>{const r=new FileReader();
      window.__sh=await new Promise(ok=>{r.onload=()=>ok({img:r.result,text:d.text});r.readAsDataURL(d.files[0])})}}""")
    await pg.click('#tpSh')
    await pg.wait_for_function('window.__sh', timeout=15000)
    d = await pg.evaluate('window.__sh')
    import base64
    open(path, 'wb').write(base64.b64decode(d['img'].split(',', 1)[1]))
    return d['text']


async def main():
    serve()
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        # بدون ?tpqa والإطلاق 0: الصفحة مثل ما هي
        pg = await b.new_page()
        await pg.route('**/*firebasedatabase.app/**', lambda r: r.abort() if r.request.method != 'GET' else r.continue_())
        await pg.route('**/tashkila/config.json*', lambda r: r.fulfill(status=200, body='{"start":0}', content_type='application/json'))
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
            # نختار خطة غير الافتراضية، ونعبي 11 من القائمة
            await pg.click('.fm:text-is("4-4-2")')
            await pg.wait_for_timeout(200)
            for i in range(11):
                await pg.locator('#slots .slot').nth(i).click()
                await pg.wait_for_timeout(250)
                chk(await pg.locator('#sheetAdd').is_hidden(), 'إضافة يدوية في القائمة')
                await pg.locator('#list .pl:not([disabled])').first.click()
                await pg.wait_for_timeout(200)
            chk(await pg.locator('#tpSh').count() == 0, 'زر المشاركة قبل القفل')
            # ⚽ منو بيسجل؟ — لاعبين التشكيلة (بدون الحارس) والمهاجمين أول، وتحتهم الجوكر
            chips = await pg.locator('#tpSc .row .ch').evaluate_all('a=>a.map(b=>b.dataset.k)')
            chk(len(chips) == 10, f'لاعبين التشكيلة في الهداف {len(chips)}')
            pos = {K(p): p[2] for p in squad}
            od = [{'FWD': 0, 'MID': 1, 'DEF': 2}.get(pos.get(k), 3) for k in chips]
            chk(od == sorted(od), f'ترتيب الهداف (المهاجمين أول) {od}')
            chk('ما اخترت هداف' in await pg.text_content('#tpSc .sel'), 'بدون هداف')
            await pg.locator('#tpSc .ch').first.click()
            await pg.wait_for_timeout(200)
            chk(await pg.locator('#slots .ballb').count() == 1, '⚽ على الملعب')
            chk('هدافك' in await pg.text_content('#tpSc .sel'), 'سطر الهداف')
            await pg.click('#tpSc .seg button[data-t=rest]')
            await pg.wait_for_timeout(200)
            rk = await pg.locator('#tpSc .row .ch').evaluate_all('a=>a.map(b=>b.dataset.k)')
            chk(rk and not set(rk) & set(chips), 'باقي اللاعبين فيهم لاعبين من التشكيلة')
            await pg.locator('#tpSc .row .ch').first.click()
            await pg.wait_for_timeout(200)
            chk(await pg.locator('#slots .ballb').count() == 0 and 'من خارج تشكيلتك' in await pg.text_content('#tpSc .sel'), 'لاعب من خارج التشكيلة')
            jk = await pg.locator('#tpSc .ch[aria-pressed=true]').get_attribute('data-k')
            await pg.locator('#tpSc').scroll_into_view_if_needed()
            await pg.screenshot(path=f'{OUT}/tp_pick-joker_{w}.png', full_page=True)
            await pg.click('#tpSc .seg button[data-t=xi]')
            await pg.wait_for_timeout(200)
            await pg.locator('#tpSc .row .ch').first.click()
            await pg.wait_for_timeout(200)
            sck = chips[0]
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
            chk(tp and d.get('f') == '4-4-2', 'الخطة ما انحفظت')
            chk(tp and d.get('s') == sck, f'الهداف ما انحفظ {d.get("s")}')
            chk(jk not in d['x'].split('~'), 'الجوكر من التشكيلة')
            # تعديل بعد الحفظ: الزر يقول «اعتمد التعديل»
            await pg.locator('#tpSc .row').first.locator('.ch').nth(1).click()
            await pg.wait_for_timeout(200)
            chk('التعديل' in await pg.text_content('#tpGo') and 'اعتمد التعديل' in await pg.text_content('#tpSub'), 'تنبيه التعديل')
            await pg.locator('#tpSc .row').first.locator('.ch').nth(0).click()
            await pg.wait_for_timeout(200)
            chk('محفوظ' in await pg.text_content('#tpSub'), 'رجع لنفس المحفوظ')
            before = await pg.locator('#slots .slot').all_text_contents()
            await pg.screenshot(path=f'{OUT}/tp_pick-saved_{w}.png', full_page=True)
            # الرجوع لصمّم تشكيلتك
            await pg.click('.tp-tabs button[data-m=free]')
            await pg.wait_for_timeout(300)
            chk(await pg.locator('#clubs').is_visible() and await pg.locator('.tp-card').count() == 0, 'الرجوع للوضع الحر')
            await pg.close()

            pg, _ = await run(b, 'pick', w, True)
            chk(await pg.locator('#slots .slot:not(.empty)').count() == 11, 'ما رجع التوقع المحفوظ')
            await pg.close()
            # بلاغ: «أحفظ التشكيلة وأطلع وأرجع، تتغير» — لازم ترجع نفس الخطة وكل لاعب في مكانه
            pg, _ = await run(b, 'pick', w, d)
            chk(await pg.locator('.fm[aria-pressed=true]').text_content() == '4-4-2', 'الخطة ما رجعت')
            chk(await pg.locator('#slots .slot').all_text_contents() == before, 'اللاعبين ما رجعوا لنفس أماكنهم')
            chk(await pg.locator('#tpSc .ch[aria-pressed=true]').get_attribute('data-k') == sck and await pg.locator('#slots .ballb').count() == 1, 'الهداف ما رجع')
            await pg.close()
            # توقع قديم بدون خطة محفوظة: نستنتج الخطة من مراكز اللاعبين بترتيبهم
            pg, _ = await run(b, 'pick', w, {k: v for k, v in d.items() if k != 'f'})
            chk(await pg.locator('#slots .slot').all_text_contents() == before, 'التوقع القديم ما رجع بنفس الترتيب')
            await pg.close()

            pg, _ = await run(b, 'locked', w, True)
            chk('انقفل' in await pg.text_content('.tp-card') and await pg.locator('#tpGo').count() == 0, 'حالة القفل')
            await pg.locator('#slots .slot').first.click()
            await pg.wait_for_timeout(300)
            chk(not await pg.locator('#sheet.on').count(), 'القائمة تنفتح بعد القفل')
            chk(await pg.locator('#tpSh').count() == 1 and 'توقعي' in await pg.text_content('#tpSh'), 'زر مشاركة التوقع بعد القفل')
            chk(await pg.locator('.tp-sc.ro').count() == 1 and await pg.locator('#tpSc').count() == 0, 'الهداف بعد القفل للعرض بس')
            await pg.screenshot(path=f'{OUT}/tp_locked_{w}.png', full_page=True)
            if w == 390:
                await share_img(pg, f'{OUT}/tp_share_locked.jpg')
            await pg.close()

            pg, _ = await run(b, 'reveal', w, True)
            chk('8 من 11' in await pg.text_content('.tp-res'), 'النتيجة')
            chk('14 نقطة' in await pg.text_content('.tp-res'), f"المجموع مع الهداف {await pg.text_content('.tp-res')}")
            chk('+6' in await pg.text_content('.tp-scr i') and 'أول هدف' in await pg.text_content('.tp-scr'), 'نتيجة الهداف')
            chk(await pg.locator('#slots .ballb').count() == 1, '⚽ على الملعب في النتيجة')
            chk(await pg.locator('.slot.tp-ok').count() == 8 and await pg.locator('.slot.tp-no').count() == 3, 'علامات ✓ ✕')
            chk(await pg.locator('.tp-miss').count() == 1, 'قائمة الأساسيين اللي ما توقعهم')
            chk('نتيجتي' in await pg.text_content('#tpSh'), 'زر مشاركة النتيجة')
            await pg.screenshot(path=f'{OUT}/tp_reveal_{w}.png', full_page=True)
            if w == 390:
                t = await share_img(pg, f'{OUT}/tp_share_reveal.jpg')
                chk('توقعت 8 من 11 صح' in (t or '') and '(+6)' in (t or ''), f'نص المشاركة {t}')
            await pg.close()
            # قبل نهاية المباراة: نقاط الهداف ما تنحسب لين تخلص
            pg, _ = await run(b, 'reveal', w, True, {M['id']: {k: v for k, v in LU[M['id']].items() if k != 'fin'}})
            chk('8 نقاط' in await pg.text_content('.tp-res') and 'بعد نهاية المباراة' in await pg.text_content('.tp-scr'), 'الهداف قبل النهاية')
            await pg.close()
            # ما سجّل
            pg, _ = await run(b, 'reveal', w, True, {M['id']: {**{k: v for k, v in LU[M['id']].items() if k not in ('hg', 'ag', 'fg')}}})
            chk('ما سجّل' in await pg.text_content('.tp-scr') and '8 نقاط' in await pg.text_content('.tp-res'), 'الهداف ما سجّل')
            await pg.screenshot(path=f'{OUT}/tp_reveal-nogoal_{w}.png', full_page=True)
            await pg.close()

            if OPEN.get(str(M['wk'])):
                pg, _ = await run(b, 'soon', w, False)
                chk('ينفتح' in await pg.text_content('.tp-card'), 'حالة قبل الفتح')
                await pg.close()
        await b.close()
    print(f'النتيجة: {ok} نجح · {fail} فشل  (نادي {CLUB}، مباراة {M["id"]})')
    sys.exit(1 if fail else 0)


asyncio.run(main())
