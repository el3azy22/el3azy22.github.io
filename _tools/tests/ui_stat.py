"""عداد الإحصائيات الخاص (assets/stat.js + قواعد v) على المحاكي.
يحتاج المحاكي (9000) و http.server (8765). كل طلبات Firebase تروح للمحاكي، وgoogleapis مقطوع.
  python3 _tools/tests/ui_stat.py
"""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import requests
import test_rules as T
from ui_mano import to_emu, PROD
from playwright.async_api import async_playwright

S = 1794859200000
day = (int(time.time() * 1000) - S) // 86400000 + 1
V = lambda: requests.get(T.url(f'v/{day}'), headers=T.OWNER).json() or {}


async def visit(b, paths, ls=None, js=None, tz=None):
    ctx = await b.new_context(timezone_id=tz) if tz else await b.new_context()
    if ls:
        await ctx.add_init_script(''.join(f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});" for k, v in ls.items()))
    pg = await ctx.new_page()
    await pg.route(PROD + '/**', to_emu())
    await pg.route('**googleapis.com/**', lambda r: r.abort())
    for p in paths:
        await pg.goto('http://localhost:8765' + p + ('&' if '?' in p else '?') + 'stattest')
        await pg.wait_for_timeout(900)
    if js:
        await pg.evaluate(js); await pg.wait_for_timeout(700)
    await ctx.close()


async def main():
    T.load_rules(S, []); T.reset()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        await visit(b, ['/', '/mano/'])                                   # تلفون يديد: صفحتين
        v = V()
        T.check('تلفون يديد: زيارتين، زائر واحد، مب عائد', (v.get('t'), v.get('u'), v.get('r'), v.get('p')), (2, 1, None, {'home': 1, 'mano': 1}))
        await visit(b, ['/fans/'], ls={'el3azy_club': '"wasl"'})          # زار المنصة قبل العداد
        v = V()
        T.check('تلفون زار قبل: زائر وعائد', (v.get('t'), v.get('u'), v.get('r'), v['p'].get('fans')), (3, 2, 1, 1))
        await visit(b, ['/songs/'], ls={'el3_vd': str(day), 'el3_first': str(day)},
                    js="el3stat('wasl','play');el3stat('wasl','dl');el3stat('wasl','hack');el3stat('../x','play')")
        v = V()
        T.check('نفس التلفون في نفس اليوم: زيارة بس بدون زائر يديد', (v.get('t'), v.get('u'), v['p'].get('songs')), (4, 2, 1))
        T.check('أحداث الأغاني: تشغيل وتنزيل بس (الغلط ما ينحسب)', v.get('s'), {'wasl': {'play': 1, 'dl': 1}})
        # منطقة التلفون (داخل الإمارات أو برا) تنحفظ لصاحب البطاقة بس، وتقراها لوحة المدير بس
        fbk = lambda u: json.dumps({'t': T.tok(u), 'r': '', 'u': u, 'exp': int(time.time() * 1000) + 3600000})
        await visit(b, ['/'], ls={'el3azy_club': '"wasl"', 'el3azy_fb': fbk('ugeo1')}, tz='Asia/Dubai')
        await visit(b, ['/'], ls={'el3azy_club': '"ain"', 'el3azy_fb': fbk('ugeo2')}, tz='Asia/Riyadh')
        await visit(b, ['/'], ls={'el3azy_fb': fbk('ugeo3')}, tz='Asia/Riyadh')
        g = requests.get(T.url('g'), headers=T.OWNER).json() or {}
        T.check('منطقة التلفون تنحفظ لأصحاب البطاقات بس', g, {'ugeo1': 'Asia/Dubai', 'ugeo2': 'Asia/Riyadh'})
        await b.close()
    T.check('صاحب البطاقة ما يقرا المناطق', requests.get(T.url('g', 'ugeo1')).status_code, 401)
    T.check('المدير يقرا المناطق', requests.get(T.url('g', 'Vt7pBIwn9jhQCI2LSORFpnU3aCa2')).status_code, 200)
    T.check('منطقة بشكل غلط ترفض', requests.put(T.url('g/ugeo1', 'ugeo1'), data=json.dumps('<script>')).status_code, 401)
    T.check('ما يكتب منطقة غيره', requests.put(T.url('g/ugeo1', 'ugeo2'), data=json.dumps('Asia/Dubai')).status_code, 401)
    put = lambda path, val: requests.put(T.url(path), data=json.dumps(val)).status_code
    T.check('السيرفر يرفض زيادة +2', put(f'v/{day}/t', V()['t'] + 2), 401)
    T.check('السيرفر يرفض قسم مب موجود', put(f'v/{day}/p/hack', 1), 401)
    T.check('السيرفر يرفض يوم 0', put('v/0/t', 1), 401)
    T.check('السيرفر يرفض حقل غريب', put(f'v/{day}/zz', 1), 401)
    T.check('السيرفر يرفض حدث أغنية غريب', put(f'v/{day}/s/wasl/hack', 1), 401)
    T.check('السيرفر يقبل +1', put(f'v/{day}/t', V()['t'] + 1), 200)
    print(f'\nالنتيجة: {T.ok} نجح · {T.fail} فشل')
    sys.exit(1 if T.fail else 0)

asyncio.run(main())
