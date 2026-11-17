"""«منو اللاعب؟» بعد إخفاء الجواب: لاعب اليوم من السيرفر (q) بقفل الوقت، والخبير عشوائي لكل مشجع.
يحتاج المحاكي + http.server 8765 + Chrome.   python3 _tools/tests/ui_q.py"""
import asyncio, datetime, json, os, sys, time
import requests
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
import test_rules as T
from ui_mano import fake_signup, to_emu, PROD

D = json.load(open(os.path.join(T.ROOT, 'mano', 'data.json')))
E = D['schedule'] if 'schedule' in D else [p['id'] for p in D['players'] if p.get('ap', 0) >= 5][:10]
POOL = set(D.get('pool') or D.get('schedule_pro'))
DAYMS = 86400000
now = int(time.time() * 1000)
mid = (now + 4 * 3600000) // DAYMS * DAYMS - 4 * 3600000          # 12 بالليل الإمارات اليوم (الحقيقي)
PAGE_T = datetime.datetime.fromtimestamp((1794859200000 + 2 * DAYMS + (now - mid)) / 1000, datetime.timezone.utc)  # الصفحة: اليوم 3


def strip(route_data):
    async def h(route):
        r = await route.fetch(); d = await r.json(); d.pop('schedule', None); d.pop('schedule_pro', None)
        await route.fulfill(response=r, body=json.dumps(d, ensure_ascii=False), headers={**r.headers, 'content-type': 'application/json'})
    return h


async def page(b, uid, seed=None, broken=False):
    ctx = await b.new_context(viewport={'width': 390, 'height': 800})
    js = ";".join(f"localStorage.setItem('el3azy_mano_{k}',{json.dumps(json.dumps(v))})" for k, v in (seed or {}).items())
    await ctx.add_init_script(js + ";localStorage.setItem('el3azy_mano_seenHow','true');localStorage.setItem('el3azy_club',JSON.stringify(''))")
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.clock.install(time=PAGE_T)
    await pg.route('**/mano/data.json*', strip(None))
    await pg.route('**/identitytoolkit.googleapis.com/**', fake_signup(uid))
    await pg.route('**/securetoken.googleapis.com/**', lambda r: r.abort())
    if broken:
        await pg.route(PROD + '/**', lambda r: r.abort())
    else:
        await pg.route(PROD + '/**', to_emu())
    await pg.goto('http://localhost:8765/mano/'); await pg.clock.run_for(3000); await pg.wait_for_timeout(1500)
    return ctx, pg, errs


async def ls(pg, k):
    v = await pg.evaluate(f"localStorage.getItem('el3azy_mano_{k}')")
    return json.loads(v) if v else None


async def main():
    T.load_rules(mid - 2 * DAYMS, []); T.reset()
    requests.put(T.url('q'), data=json.dumps({str(d + 1): E[d] for d in range(5)}), headers=T.OWNER)
    print('— إخفاء الجواب + الخبير العشوائي (الصفحة على اليوم 3) —')
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx, pg, errs = await page(b, 'q1')
        T.check('لاعب اليوم ينجاب من السيرفر', (await ls(pg, 'qa_3'), await ls(pg, 'qa_4')), (E[2], None))
        T.check('بدون أخطاء في الصفحة', errs, [])
        await ctx.close()
        pros = []
        for i in range(3):
            ctx, pg, errs = await page(b, f'q{i+2}', {'g_3_easy': {'guesses': [E[2]], 'done': True, 'win': True}, 'mode': 'pro'})
            pa = await ls(pg, 'pa_3'); pros.append(pa)
            if i == 0:
                await pg.reload(); await pg.clock.run_for(2000); await pg.wait_for_timeout(800)
                T.check('لاعب الخبير يظل نفسه بعد تحديث الصفحة', await ls(pg, 'pa_3'), pa)
                T.check('صفحة الخبير بدون أخطاء', errs, [])
            await ctx.close()
        T.check('لاعب الخبير من قائمة الخبير ومب لاعب اليوم', all(x in POOL and x != E[2] for x in pros), True)
        T.check('3 مشجعين: لاعبين خبير مختلفين', len(set(pros)) > 1, True)
        ctx, pg, errs = await page(b, 'q9', broken=True)
        T.check('السيرفر ما يرد: رسالة واضحة وزر إعادة', 'ما قدرنا نجيب لاعب اليوم' in await pg.inner_text('#app'), True)
        await ctx.close(); await b.close()
    print(f'\nالنتيجة: {T.ok} نجح · {T.fail} فشل')
    sys.exit(1 if T.fail else 0)

asyncio.run(main())
