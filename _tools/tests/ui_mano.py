"""رحلة «منو اللاعب؟» من الواجهة ضد محاكي Firebase: الحفظ، الخبير، وانقطاع الاتصال قبل التأكيد.
يحتاج: المحاكي (9000) + python3 -m http.server 8765 من جذر المستودع + Chrome.
  python3 _tools/tests/ui_mano.py"""
import asyncio, base64, json, os, sys, time
import requests
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
import test_rules as T

PROD = 'https://el3azy-3b64e-default-rtdb.europe-west1.firebasedatabase.app'
D = json.load(open(os.path.join(T.ROOT, 'mano', 'data.json')))
NM = {p['id']: p['n'] for p in D['players']}
E = D.get('schedule') or ['soufiane-rahimi'] + [p['id'] for p in D['players'] if p.get('ap', 0) >= 5 and p['id'] != 'soufiane-rahimi'][:40]   # بعد النقل: الجدول في q (الاختبار يكتبه في المحاكي)
P = ['alassane-diallo']
day = (int(time.time() * 1000) - 1794859200000) // 86400000 + 1


def fake_signup(uid):
    async def h(route):
        await route.fulfill(content_type='application/json', body=json.dumps({'idToken': T.tok(uid), 'refreshToken': 'r', 'localId': uid, 'expiresIn': '3600'}))
    return h


def to_emu(lose_patch=False):
    async def h(route):
        r = route.request
        u = r.url.replace(PROD, T.B).replace('.json?', f'.json?ns={T.NS}&').replace('.json', '.json' if '?' in r.url else f'.json?ns={T.NS}')
        resp = requests.request(r.method, u, data=r.post_data)
        if lose_patch and r.method == 'PATCH':
            await route.fulfill(status=503, body='')   # وصل السيرفر بس الرد ضاع
        else:
            await route.fulfill(status=resp.status_code, body=resp.text, content_type='application/json')
    return h


async def play(b, uid, club, easy, pro=None, lose=False, extra=None, act=None, look=None):
    seed = {f'g_{day}_easy': easy, 'seenHow': True, 'mode': 'pro' if pro else 'easy', **(extra or {})}
    if pro:
        seed[f'g_{day}_pro'] = pro
        seed[f'pa_{day}'] = P[0]          # لاعب الخبير عشوائي لكل جهاز: نثبته للاختبار
    js = ';'.join(f"localStorage.setItem('el3azy_mano_{k}',{json.dumps(json.dumps(v))})" for k, v in seed.items())
    js += f";localStorage.setItem('el3azy_club',JSON.stringify('{club}'))"
    ctx = await b.new_context(viewport={'width': 390, 'height': 800})
    await ctx.add_init_script(js)
    pg = await ctx.new_page()
    await pg.route('**/identitytoolkit.googleapis.com/**', fake_signup(uid))
    await pg.route('**/securetoken.googleapis.com/**', lambda r: r.abort())
    await pg.route(PROD + '/**', to_emu(lose))
    await pg.goto('http://localhost:8765/mano/'); await pg.wait_for_timeout(3000)
    if act:      # يكتب اسم لاعب في خانة البحث ويختار أول اقتراح
        await pg.fill('#gIn', NM[act]); await pg.wait_for_timeout(300); await pg.press('#gIn', 'Enter'); await pg.wait_for_timeout(2500)
    if look:
        await look(pg)
    st = await pg.evaluate(f"[localStorage.getItem('el3azy_mano_sub_{day}_easy'),localStorage.getItem('el3azy_mano_sub_{day}_pro')]")
    await ctx.close()
    return [json.loads(x) if x else None for x in st]


async def main():
    T.load_rules(1794859200000, []); T.reset()
    if E:
        requests.put(T.url('q'), data=json.dumps({str(i + 1): x for i, x in enumerate(E[:30])}), headers=T.OWNER)
    print(f'— رحلة منو اللاعب (اليوم {day}) —')
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        win2 = {'guesses': [E[5], E[day - 1]], 'done': True, 'win': True}
        st = await play(b, 'ua1', 'wahda', win2)
        T.check('لاعب اليوم من محاولتين: الجهاز يسجل إنه انحفظ', st[0], {'g': 2, 'c': 'wahda'})
        T.check('السيرفر: سجل المشجع', {k: v for k, v in T.get(f'p/{day}/easy/ua1').json().items() if k != 't'}, {'c': 'wahda', 'd': day, 'g': 2})
        T.check('السيرفر: نقاط الوحدة = 5', T.get(f'c/{day}/easy/wahda').json(), {'n': 1, 't': 5})
        prof = {'guesses': [E[3]] * 5 + [P[0]], 'done': True, 'win': True}
        st = await play(b, 'ua2', 'ain', win2, prof)
        T.check('لاعب اليوم + الخبير من 6 محاولات', st, [{'g': 2, 'c': 'ain'}, {'g': 6, 'c': 'ain'}])
        T.check('السيرفر: نقاط العين في الخبير = 1', T.get(f'c/{day}/pro/ain').json(), {'n': 1, 't': 1})
        st = await play(b, 'ua3', 'wasl', win2, lose=True)
        T.check('انقطع الرد بعد الحفظ: الجهاز يتأكد ويعتمد المحفوظ', st[0], {'g': 2, 'c': 'wasl'})
        T.check('ما انحسبت مرتين', T.get(f'c/{day}/easy/wasl').json(), {'n': 1, 't': 5})
        lose6 = {'guesses': [E[3]] * 6, 'done': True, 'win': False}
        st = await play(b, 'ua4', 'nasr', lose6)
        T.check('ما عرفه: ينحسب لعبة بدون نقاط', (st[0], T.get(f'c/{day}/easy/nasr').json()), ({'g': 0, 'c': 'nasr'}, {'n': 1}))
        T.check('عداد اللاعبين اليوم = 4 والعارفين = 3', (T.get(f's/{day}/easy').json().get('n'), T.get(f's/{day}/easy').json().get('w')), (4, 3))
        t0 = 1794859200000 + (day - 1) * 86400000 + 3600000
        st = await play(b, 'ua5', 'kalba', win2, extra={f'st_{day}_easy': t0, f'fin_{day}_easy': t0 + 83000})
        T.check('وقت الحل ينرسل (83 ثانية) والسيرفر يقبله', (st[0], T.get(f'p/{day}/easy/ua5').json().get('sec')), ({'g': 2, 'c': 'kalba'}, 83))
        # الجواب مخفي بعد النهاية (ضد السكرين شوت)، و«اكشف الاسم» يبينه مع علامة مائية باسم المشجع
        nm = NM[E[day - 1]]
        async def look(pg):
            app = await pg.inner_text('#app')
            T.check('بعد النهاية: اسم اللاعب مخفي في الصفحة', nm in app.split('جواب أمس')[0], False)
            T.check('بعد النهاية: زر «اكشف الاسم» موجود', await pg.locator('#showBtn').count(), 1)
            await pg.click('#showBtn'); await pg.wait_for_timeout(500)
            T.check('بعد الكشف: الاسم يطلع مع العلامة المائية', (nm in await pg.inner_text('#app'), await pg.locator('.wm').count() > 0), (True, True))
            await pg.evaluate("Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'))")
            await pg.wait_for_timeout(300)
            T.check('لما يطلع من الصفحة: الاسم يرجع ينخفي', await pg.locator('#showBtn').count(), 1)
        await play(b, 'ua8', 'wahda', {'guesses': [E[5], E[day - 1]], 'done': True, 'win': True}, look=look)
        # سجل نهاية اللعبة الخاص (رصد الكشّاف): ينكتب لحظة ما تخلص اللعبة، حتى بدون نادي
        five = {'guesses': [E[3], E[4], E[6], E[7], E[8]], 'done': False, 'win': False}
        await play(b, 'ua6', '', five, act=E[9])
        adm = T.get(f'r/{day}/easy/ua6', 'Vt7pBIwn9jhQCI2LSORFpnU3aCa2').json() or {}
        T.check('خسارة كاملة تنسجل في السجل الخاص مع البصمة', (adm.get('g'), len(adm.get('dv') or ''), bool(adm.get('t'))), (0, 12, True))
        await play(b, 'ua7', '', {'guesses': [], 'done': False, 'win': False}, act=E[day - 1])
        adm2 = T.get(f'r/{day}/easy/ua7', 'Vt7pBIwn9jhQCI2LSORFpnU3aCa2').json() or {}
        T.check('فوز من أول محاولة ينسجل وبنفس بصمة التلفون', (adm2.get('g'), adm2.get('dv')), (1, adm.get('dv')))
        await b.close()
    print(f'\nالنتيجة: {T.ok} نجح · {T.fail} فشل')
    sys.exit(1 if T.fail else 0)

if __name__ == '__main__':
    asyncio.run(main())
