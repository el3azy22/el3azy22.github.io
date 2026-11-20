"""«رمز النقل»: تلفون A (مشجع الوصل وعنده بيانات لعب) يسوي رمز، وتلفون B (متصفح ثاني فاضي) يكتبه وترجع له نفس البطاقة.
مع المحاكي (قواعد السيرفر الحقيقية) — ما في أي كتابة في Firebase الحقيقي. يحفظ لقطات mv_* في /tmp/el3azy-shots.
  python3 _tools/tests/ui_move.py"""
import asyncio, json, os, sys
import requests
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
import test_rules as T
from ui_mano import to_emu, PROD

OUT = '/tmp/el3azy-shots'
ok = fail = 0


def chk(c, m):
    global ok, fail
    if c:
        ok += 1
    else:
        fail += 1
        print('❌', m)


def auth_routes(uid, refresh):
    async def signup(route):
        await route.fulfill(content_type='application/json', body=json.dumps({'idToken': T.tok(uid), 'refreshToken': refresh, 'localId': uid, 'expiresIn': '3600'}))

    async def secure(route):   # تجديد التوكن: refresh token الصح يرجع صاحبه
        body = route.request.post_data or ''
        who = 'mvA' if 'rt-mvA' in body else None
        if not who:
            return await route.fulfill(status=400, body='{}')
        await route.fulfill(content_type='application/json', body=json.dumps({'id_token': T.tok(who), 'refresh_token': 'rt-mvA', 'user_id': who, 'expires_in': '3600'}))
    return signup, secure


async def device(b, uid, refresh, seed=None, url='http://localhost:8765/'):
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    js = ";".join(f"localStorage.setItem({json.dumps(k)},{json.dumps(json.dumps(v))})" for k, v in (seed or {}).items())
    await ctx.add_init_script(js)
    pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    su, se = auth_routes(uid, refresh)
    await pg.route('**/identitytoolkit.googleapis.com/**', su)
    await pg.route('**/securetoken.googleapis.com/**', se)
    await pg.route('**/gc.zgo.at/**', lambda r: r.abort())
    await pg.route(PROD + '/**', to_emu())
    await pg.goto(url); await pg.wait_for_timeout(2500)
    return ctx, pg, errs


async def main():
    T.load_rules(0, []); T.reset({'f': {'mvA': {'c': 'wasl', 'n': 'محمد', 't': 1}}, 'fc': {'wasl': 1}})
    print('— رمز النقل —')
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        A = {'el3azy_club': 'wasl', 'el3azy_name': 'محمد', 'el3azy_fan_srv': {'c': 'wasl', 'n': 'محمد', 't': 1},
             'el3azy_fb': {'t': T.tok('mvA'), 'r': 'rt-mvA', 'u': 'mvA', 'exp': 9e15},
             'el3azy_pred': {'84540': {'h': 2, 'a': 1}}, 'el3azy_tp_84540': ['k1', 'k2'], 'el3azy_mano_g_2_easy': {'done': True, 'win': True}}
        ca, pa, ea = await device(b, 'mvA', 'rt-mvA', A)
        await pa.click('.fz-chip'); await pa.wait_for_timeout(400)
        chk(await pa.locator('.pf-mk').is_visible(), 'زر «انقل بطاقتك» في ملف المشجع')
        await pa.click('.pf-mk'); await pa.wait_for_timeout(1500)
        code = (await pa.text_content('.fz-code') or '').strip()
        chk(len(code) == 9 and code[4] == '-', f'الرمز {code}')
        await ca.grant_permissions(['clipboard-read', 'clipboard-write'])
        await pa.click('.fz-cc'); await pa.wait_for_timeout(200)
        chk((await pa.evaluate('navigator.clipboard.readText()')) == code, 'زر «انسخ الرمز» ينسخ نفس الرمز')
        await pa.click('.fz-cp'); await pa.wait_for_timeout(200)
        chk((await pa.evaluate('navigator.clipboard.readText()')).endswith('#nql=' + code.replace('-', '')), 'زر الرابط ينسخ رابط فيه نفس الرمز')
        await pa.screenshot(path=f'{OUT}/mv_code_390.png')
        x = requests.get(T.url('x'), headers=T.OWNER).json() or {}
        chk(len(x) == 1, 'الرمز انحفظ في السيرفر')
        rec = list(x.values())[0] if x else {}
        chk('wasl' not in json.dumps(rec) and 'rt-mvA' not in json.dumps(rec) and 'محمد' not in json.dumps(rec, ensure_ascii=False), 'البيانات في السيرفر مشفّرة')

        # تلفون B: متصفح فاضي (حساب يديد mvB)، يفتح بطاقة «تشجع أي نادي» ويضغط «عندي رمز»
        cb, pb, eb = await device(b, 'mvB', 'rt-mvB')
        await pb.click('.fz-card'); await pb.wait_for_timeout(400)
        await pb.click('.fz-gt'); await pb.wait_for_timeout(300)
        await pb.fill('.fz-in', 'ZZZZ-ZZZZ'); await pb.click('.fz-go'); await pb.wait_for_timeout(1200)
        chk('غلط' in (await pb.text_content('.fz-err') or ''), 'رمز غلط يطلع رسالة')
        await pb.fill('.fz-in', f'افتح https://el3azy.com/#nql={code.replace("-", "")} '); await pb.dispatch_event('.fz-in', 'input')
        chk((await pb.input_value('.fz-in')) == code, f'لصق الرابط كامل في الخانة يطلع الرمز ({await pb.input_value(".fz-in")})')
        await pb.fill('.fz-in', 'xx ' + code.lower() + ' yy'); await pb.dispatch_event('.fz-in', 'input')
        chk((await pb.input_value('.fz-in')) == code, 'لصق نص فيه الرمز يطلع الرمز')
        await pb.fill('.fz-in', code.lower().replace('-', ' ')); await pb.wait_for_timeout(100)
        await pb.screenshot(path=f'{OUT}/mv_enter_390.png')
        await pb.click('.fz-go'); await pb.wait_for_timeout(900)
        await pb.screenshot(path=f'{OUT}/mv_done_390.png')
        await pb.wait_for_timeout(2500)
        ls = await pb.evaluate("()=>Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))")
        chk(json.loads(ls.get('el3azy_fb', '{}')).get('u') == 'mvA', 'تلفون B صار نفس الحساب')
        chk(json.loads(ls.get('el3azy_club', 'null')) == 'wasl', 'النادي انتقل')
        chk('el3azy_tp_84540' in ls and 'el3azy_pred' in ls and 'el3azy_mano_g_2_easy' in ls, 'بيانات اللعب انتقلت')
        chk('الوصل' in (await pb.text_content('.fz-chip') or ''), 'البطاقة فوق تبين الوصل')
        chk(not (requests.get(T.url('x'), headers=T.OWNER).json() or {}), 'الرمز انمسح بعد الاستخدام')
        # نفس الرمز مرة ثانية ما يشتغل
        cc, pc, ec = await device(b, 'mvC', 'rt-mvC')
        await pc.click('.fz-card'); await pc.wait_for_timeout(300); await pc.click('.fz-gt')
        await pc.fill('.fz-in', code); await pc.click('.fz-go'); await pc.wait_for_timeout(1200)
        chk('غلط' in (await pc.text_content('.fz-err') or ''), 'الرمز ينستخدم مرة وحدة')
        # رابط النقل يفتح الرمز جاهز
        _, pa2, _ = await device(b, 'mvA', 'rt-mvA', A)
        await pa2.click('.fz-chip'); await pa2.wait_for_timeout(600); await pa2.click('.pf-mk'); await pa2.wait_for_timeout(1500)
        code2 = (await pa2.text_content('.fz-code') or '').strip()
        _, pd, _ = await device(b, 'mvD', 'rt-mvD', url=f'http://localhost:8765/#nql={code2.replace("-", "")}')
        chk((await pd.input_value('.fz-in')) == code2, 'الرابط يعبّي الرمز')
        chk('nql' not in pd.url, 'الرمز ينشال من الرابط')
        # «رمز الاسترجاع» الثابت: يطلع في ملف المشجع، ويرجّع البطاقة لو ضاعت، وينستخدم أكثر من مرة، وصاحبه يغيّره
        T.reset({'f': {'mvA': {'c': 'wasl', 'n': 'محمد', 't': 1}}, 'fc': {'wasl': 1}})
        cr, pr, er = await device(b, 'mvA', 'rt-mvA', A)
        await pr.click('.fz-chip'); await pr.wait_for_timeout(1800)
        rk = ((await pr.text_content('.pf-rkc b')) or '').strip() if await pr.locator('.pf-rkc').is_visible() else ''
        chk(len(rk) == 9 and rk[4] == '-', f'رمز الاسترجاع يطلع في ملف المشجع ({rk})')
        await pr.screenshot(path=f'{OUT}/rk_profile_390.png')
        srv = requests.get(T.url('rk'), headers=T.OWNER).json() or {}
        chk(len(srv) == 1 and 'rt-mvA' not in json.dumps(srv), 'رمز الاسترجاع انحفظ في السيرفر ومشفّر')
        await pr.click('.pf-x'); await pr.wait_for_timeout(200); await pr.click('.fz-chip'); await pr.wait_for_timeout(800)
        chk(((await pr.text_content('.pf-rkc b')) or '').strip() == rk, 'نفس الرمز كل مرة (ثابت)')
        for who in ('mvE', 'mvF'):
            ce, pe, ee = await device(b, who, 'rt-' + who)
            await pe.click('.fz-card'); await pe.wait_for_timeout(300); await pe.click('.fz-gt')
            await pe.fill('.fz-in', rk); await pe.click('.fz-go'); await pe.wait_for_timeout(3000)
            ls = await pe.evaluate("()=>Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))")
            chk(json.loads(ls.get('el3azy_fb', '{}')).get('u') == 'mvA' and json.loads(ls.get('el3azy_club', 'null')) == 'wasl', f'رمز الاسترجاع رجّع البطاقة ({who})')
            chk(json.loads(ls.get('el3azy_rk', 'null')) == rk.replace('-', ''), f'الرمز ينحفظ في التلفون اليديد ({who})')
            await ce.close()
        pr.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pr.click('.rk-sw'); await pr.wait_for_timeout(2000)
        rk2 = ((await pr.text_content('.pf-rkc b')) or '').strip()
        chk(len(rk2) == 9 and rk2 != rk, f'«غيّره» يسوي رمز يديد ({rk2})')
        chk(len(requests.get(T.url('rk'), headers=T.OWNER).json() or {}) == 1, 'القديم انمسح من السيرفر')
        cg, pg2, eg = await device(b, 'mvG', 'rt-mvG')
        await pg2.click('.fz-card'); await pg2.wait_for_timeout(300); await pg2.click('.fz-gt')
        await pg2.fill('.fz-in', rk); await pg2.click('.fz-go'); await pg2.wait_for_timeout(1500)
        chk('غلط' in (await pg2.text_content('.fz-err') or ''), 'الرمز القديم ما يشتغل بعد التغيير')
        chk(not (ea + eb + ec + er + eg), f'أخطاء {ea + eb + ec + er + eg}')
        await b.close()
    print(f'النتيجة: {ok} نجح · {fail} فشل')
    sys.exit(1 if fail else 0)


asyncio.run(main())
