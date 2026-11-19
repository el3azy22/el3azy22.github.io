"""«ملف المشجع» في بطاقة المشجع: نقاطه (هالأسبوع/الموسم) ومركزه وكل تحدي، و«تعديل البطاقة».
يحتاج http.server (8765). Firebase مقطوع (ما في كتابة).  python3 _tools/tests/ui_points.py"""
import asyncio, json, sys
from playwright.async_api import async_playwright

ok = fail = 0
def check(n, got, want):
    global ok, fail
    g = got == want; ok += g; fail += not g
    print(('✅' if g else '❌'), n, '→', got, '' if g else f'(المتوقع {want})')

R = {'w': 1, 'week': {'AAAAAAAAAAAA': {'all': [45, 57, 1954, 'wahda'], 'mano': [120, 30, 1946, 'wahda'], 'tp': [30, 7, 121, 'wahda'], 'act': [3, 3]}},
     'season': {'AAAAAAAAAAAA': {'all': [80, 90, 1954, 'wahda'], 'mano': [150, 63, 1946, 'wahda'], 'pred': [60, 20, 587, 'wahda'], 'tp': [30, 7, 121, 'wahda']}}}


D = {'xi': 11, 'challenges': [{'id': 'mano'}, {'id': 'pred'}, {'id': 'tp'}], 'weeks': [{'w': 1, 'live': True, 'boards': {'all': {'xi': {'wahda': [['x', 60, 'AAAAAAAAAAAA', 7, 0]]}}}}]}


async def card(b, uid, club='wahda'):
    ctx = await b.new_context(viewport={'width': 390, 'height': 860})
    await ctx.add_init_script(f"localStorage.setItem('el3azy_club',JSON.stringify('{club}'));localStorage.setItem('el3azy_fan_srv',JSON.stringify({{c:'{club}',n:'',t:1}}));"
                              f"localStorage.setItem('el3azy_fb',JSON.stringify({{t:'x',r:'',u:'{uid}',exp:Date.now()+36e5}}))")
    pg = await ctx.new_page()
    await pg.route('**/*firebasedatabase.app/**', lambda r: r.abort())
    await pg.route('**/googleapis.com/**', lambda r: r.abort())
    await pg.route('**/fans/ranks.json*', lambda r: r.fulfill(status=200, body=json.dumps(R), content_type='application/json'))
    await pg.route('**/fans/data.json*', lambda r: r.fulfill(status=200, body=json.dumps(D), content_type='application/json'))
    await pg.goto('http://localhost:8765/'); await pg.wait_for_timeout(1500)
    await pg.click('.fz-chip'); await pg.wait_for_timeout(1000)
    out = {'week': await pg.inner_text('#pf')}
    if await pg.locator('.pf-seg button[data-t=season]').count():
        await pg.click('.pf-seg button[data-t=season]'); await pg.wait_for_timeout(200)
        out['season'] = await pg.inner_text('#pf')
        out['grid_before'] = await pg.locator('.fz-grid').is_visible()
        await pg.click('.pf-ed'); await pg.wait_for_timeout(200)
        out['grid_after'] = await pg.locator('.fz-grid').is_visible()
    await ctx.close()
    return out


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        o = await card(b, 'AAAAAAAAAAAAxyz')
        w, se = o['week'], o.get('season', '')
        check('هالأسبوع: المجموع والمركز', ('57' in w, '#45' in w), (True, True))
        check('هالأسبوع: مكانه في نخبة ناديه', 'أنت رقم 7 في نخبة جمهور الوحدة' in w.replace('\n', ' '), True)
        check('هالأسبوع: نقاط كل تحدي', [x in w for x in ('30', '7')], [True, True])
        check('الموسم: المجموع والمركز والتوقعات', ('90' in se, '#80' in se, '20' in se), (True, True, True))
        check('اختيار النادي مخفي لين «تعديل البطاقة»', (o.get('grid_before'), o.get('grid_after')), (False, True))
        o = await card(b, 'ZZZZZZZZZZZZxyz')
        check('بدون نقاط: رسالة', 'ما عندك نقاط' in o['week'], True)
        await b.close()
    print(f'\nالنتيجة: {ok} نجح · {fail} فشل')
    sys.exit(1 if fail else 0)

asyncio.run(main())
