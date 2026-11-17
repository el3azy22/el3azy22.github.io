"""«شبكة الدوري»: الصفحة الحقيقية مع المحاكي (قواعد السيرفر الحقيقية) — الشبكة من السيرفر بقفل الوقت،
المحاولات تنكتب بالترتيب، العدادات، الاسترجاع بعد مسح بيانات المتصفح، الوقت الإضافي، الضياع والإعادة.
يحتاج المحاكي + http.server 8765 + Chrome.   python3 _tools/tests/ui_grid.py"""
import asyncio, datetime, json, os, random, sys, time
import requests
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'grid'))
import test_rules as T
from ui_mano import fake_signup, to_emu, PROD
import build as GB

DAYMS = 86400000
now = int(time.time() * 1000)
mid = (now + 4 * 3600000) // DAYMS * DAYMS - 4 * 3600000
PAGE_T = datetime.datetime.fromtimestamp((1794859200000 + 2 * DAYMS + (now - mid)) / 1000, datetime.timezone.utc)  # الصفحة: اليوم 3
PL = GB.players()
g = GB.fill({}, 3, 4, PL, random.Random(int(os.environ.get("GSEED") or 5)))
G3 = g['3']


async def page(b, uid, seed=None, lose=False, tut=False):
    ctx = await b.new_context(viewport={'width': 390, 'height': 800})
    js = ";".join(f"localStorage.setItem({json.dumps(k)},{json.dumps(json.dumps(v))})" for k, v in (seed or {}).items())
    await ctx.add_init_script(js + ";localStorage.setItem('el3azy_club',JSON.stringify('wahda'))" + ("" if tut else ";localStorage.setItem('el3azy_grid_tut','1')"))
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.clock.install(time=PAGE_T)
    await pg.route('**/identitytoolkit.googleapis.com/**', fake_signup(uid))
    await pg.route('**/securetoken.googleapis.com/**', lambda r: r.abort())
    await pg.route('**/gc.zgo.at/**', lambda r: r.abort())
    await pg.route(PROD + '/**', to_emu(lose))
    await pg.goto('http://localhost:8765/grid/'); await pg.clock.run_for(2500); await pg.wait_for_timeout(1500)
    return ctx, pg, errs


async def play(pg, k, pid):
    await pg.click(f'#x{k}'); await pg.wait_for_timeout(150)
    await pg.evaluate("id=>{const b=document.createElement('button');b.dataset.id=id;document.querySelector('#os').append(b);b.onclick=null}", pid)
    await pg.evaluate(f"""()=>{{const p=JSON.parse(localStorage.getItem('el3azy_grid_3')||'null');}}""")
    await pg.fill('#oi', 'zz'); await pg.wait_for_timeout(50)
    # نختار من نتايج البحث الحقيقية: نكتب اسم اللاعب الإنجليزي
    p = next(x for x in PL if x['id'] == pid)
    await pg.fill('#oi', p['e'] or p['n']); await pg.wait_for_timeout(200)
    btn = pg.locator(f'#os button[data-id="{pid}"]')
    if await btn.count() == 0:
        return False
    await btn.first.click(); await pg.wait_for_timeout(500)
    await pg.clock.run_for(500); await pg.wait_for_timeout(600)
    return True


def srv(path):
    return requests.get(T.url(path), headers=T.OWNER).json()


async def main():
    T.load_rules(mid - 2 * DAYMS, []); T.reset({'gq': g})
    print('— شبكة الدوري (الصفحة على اليوم 3) —')
    right, taken = {}, set()
    for k in sorted(G3['a']):          # جواب مختلف لكل خانة (اللاعب ما يتكرر)
        right[k] = next(x for x in G3['a'][k] if x not in taken); taken.add(right[k])
    wrong_k = '11'
    wrong_p = next(p['id'] for p in PL if p['id'] not in G3['a'][wrong_k] and p['c'] != G3['r'][1])
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        ctx, pg, errs = await page(b, 'g1', tut=True)
        T.check('الشرح يطلع أول مرة', await pg.locator('.coach').count(), 1)
        T.check('الشرح ما يكشف جواب (علامة استفهام)', await pg.locator('#x00 .qm').count(), 0)
        await pg.click('#tNx'); await pg.click('#tNx')
        T.check('الخطوة 3 فيها «؟» بدل لاعب', await pg.locator('#x00 .qm').count(), 1)
        await pg.click('#tNx'); await pg.click('#tNx')
        T.check('الشرح يسكر بعد «ابدأ اللعب»', await pg.locator('.coach').count(), 0)
        T.check('الشبكة من السيرفر: الأندية', await pg.locator('.hd.cl').count(), 3)
        T.check('رقم الشبكة', (await pg.inner_text('.corner b')).strip(), '#' + str(G3['n']))
        T.check('اختيار صح', await play(pg, '00', right['00']), True)
        T.check('اختيار غلط', await play(pg, wrong_k, wrong_p), True)
        toast = await pg.inner_text('#t')
        T.check('الغلط يقول السبب', '❌' in toast and ':' in toast, True)
        await play(pg, '22', right['22'])
        await pg.wait_for_timeout(800)
        r = srv('gp/3/g1')
        T.check('السيرفر: 3 محاولات بالترتيب', (r or {}).get('n'), 3)
        T.check('السيرفر: الغلط محفوظ', ((r or {}).get('a') or [None, None, {}])[2].get('p') if isinstance((r or {}).get('a'), list) else (r or {}).get('a', {}).get('2', {}).get('p'), wrong_p)
        T.check('السيرفر: النادي', (r or {}).get('c'), 'wahda')
        T.check('عداد الخانة 00', srv(f'gc/3/00/{right["00"]}'), 1)
        T.check('عداد الحلول 00 (والغلط ما ينعد)', (srv('gn/3/00'), srv('gn/3/11')), (1, None))
        T.check('المحاولات الباقية 6', (await pg.inner_text('#sA')).strip(), '6')
        T.check('بدون أخطاء في الصفحة', errs, [])
        await ctx.close()
        # جهاز مسح بياناته: نفس الحساب، بدون localStorage ⇒ يرجع المحاولات من السيرفر
        ctx, pg, errs = await page(b, 'g1')
        T.check('الاسترجاع من السيرفر بعد مسح المتصفح', (await pg.inner_text('#sA')).strip(), '6')
        T.check('الخانات الصح ترجع', await pg.locator('.cell.ok').count(), 2)
        # نكمل لين تخلص التسع
        ks = [k for k in sorted(right) if k not in ('00', '22')]
        used = 3
        for k in ks:
            if used >= 9:
                break
            await play(pg, k, right[k]); used += 1
        await pg.wait_for_timeout(800)
        T.check('بعد 9 محاولات: بطاقة النتيجة', await pg.locator('.end').count(), 1)
        n_srv = (srv('gp/3/g1') or {}).get('n')
        T.check('السيرفر: 9 محاولات', n_srv, 9)
        T.check('زر الوقت الإضافي يطلع (باقي خانة)', await pg.locator('#xB').count(), 1)
        await pg.click('#xB'); await pg.wait_for_timeout(300)
        last = [k for k in sorted(right) if k not in ('00', '22') + tuple(ks[:6])]
        await play(pg, last[0], right[last[0]])
        T.check('الوقت الإضافي: الخانة تتعبى «إضافي»', await pg.locator('.cell.xt').count(), 1)
        T.check('الوقت الإضافي ما يوصل السيرفر', (srv('gp/3/g1') or {}).get('n'), 9)
        T.check('الثواني انكتبت', isinstance((srv('gp/3/g1') or {}).get('s'), int), True)
        T.check('بدون أخطاء في الصفحة', errs, [])
        await ctx.close()
        # الرد ضاع بعد ما انكتب: ما تتكرر المحاولة، والعداد يكمل صح
        ctx, pg, errs = await page(b, 'g2', lose=True)
        await play(pg, '00', right['00']); await pg.wait_for_timeout(1500)
        await ctx.close()
        ctx, pg, errs = await page(b, 'g2', seed={'el3azy_grid_3': {'att': [{'k': '00', 'p': right['00'], 'ok': True}], 'ex': {}, 't0': 1, 'sent': 0, 'sec': 0}})
        await pg.wait_for_timeout(1500)
        T.check('بعد ضياع الرد: محاولة وحدة بس في السيرفر', (srv('gp/3/g2') or {}).get('n'), 1)
        T.check('بعد ضياع الرد: العداد ما تضاعف', srv(f'gc/3/00/{right["00"]}'), 2)
        await ctx.close()
        # قبل الإطلاق: ما في شبكة
        T.reset({})
        ctx, pg, errs = await page(b, 'g3')
        T.check('بدون شبكة: رسالة «تنزل قريب»', 'قريب' in await pg.inner_text('#main'), True)
        T.check('بدون أخطاء في الصفحة', errs, [])
        await ctx.close()
        await b.close()
    print(f'\nالنتيجة: {T.ok} نجح · {T.fail} فشل')
    sys.exit(1 if T.fail else 0)


if __name__ == '__main__':
    asyncio.run(main())
