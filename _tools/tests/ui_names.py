"""أسماء اللاعبين في كل التحديات (assets/players.js): البحث بالإنجليزي وبالأسماء المعروفة، والاسم المعروف بين قوسين.
  python3 _tools/tests/ui_names.py   (يحتاج http.server على 8765؛ ما يكتب شي في Firebase)"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
B = 'http://localhost:8765'
ok = fail = 0


def chk(c, m):
    global ok, fail
    ok += bool(c); fail += (not c)
    if not c:
        print('❌', m)


AL = json.load(open(os.path.join(ROOT, 'mano/aliases.json'), encoding='utf8'))
MD = {p['id']: p for p in json.load(open(os.path.join(ROOT, 'mano/data.json'), encoding='utf8'))['players']}
SQ = json.load(open(os.path.join(ROOT, 'tashkila/squads.json'), encoding='utf8'))
TC = {'shababahli': 'shabab'}
# لاعب معروف بلقب (من aliases.json) وموجود في قوائم «تشكيلتي»
pid = next(k for k in AL if k != '_' and k in MD and any(p[5] == k for c in SQ['clubs'] for p in c['p']))
P = MD[pid]; ar = next(x for x in AL[pid] if any('؀' <= ch <= 'ۿ' for ch in x)); en = next((x for x in AL[pid] if x.isascii()), None)
club = next(c for c in SQ['clubs'] if c['id'] == TC.get(P['c'], P['c']))


async def page(b, url, init=''):
    pg = await b.new_page(viewport={'width': 390, 'height': 844})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.add_init_script("localStorage.setItem('el3azy_club',JSON.stringify('wasl'));localStorage.setItem('el3azy_mano_seenHow','true');" + init)
    await pg.route('**/*googleapis.com/**', lambda r: r.abort())
    await pg.route('**/*firebasedatabase.app/**', lambda r: r.abort() if r.request.method != 'GET' else r.continue_())
    await pg.route('**/gc.zgo.at/**', lambda r: r.abort())
    return pg, errs


async def main():
    print(f'— أسماء اللاعبين: {P["n"]} ({ar}) —')
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        # تشكيلتي
        pg, errs = await page(b, '')
        await pg.goto(B + '/tashkila/'); await pg.wait_for_timeout(2000)
        await pg.locator('#clubs .club', has_text=club['name']).first.click(); await pg.wait_for_timeout(400)
        await pg.locator('#slots .slot').nth(10).click(); await pg.wait_for_timeout(400)
        for q in [ar] + ([en, en.lower()] if en else []) + [P['e'].split()[0]]:
            await pg.fill('#q', q); await pg.wait_for_timeout(250)
            t = await pg.text_content('#list')
            chk(f'({ar})' in t, f'تشكيلتي: البحث «{q}» ما لقى {P["n"]} ({ar}) → {t[:60]}')
        chk(not errs, f'تشكيلتي أخطاء {errs}')
        # منو اللاعب
        pg, errs = await page(b, '')
        await pg.goto(B + '/mano/'); await pg.wait_for_timeout(2500)
        for q in [ar] + ([en] if en else []):
            await pg.fill('#gIn', q); await pg.wait_for_timeout(400)
            t = await pg.text_content('#sugg')
            chk(f'({ar})' in t, f'منو اللاعب: البحث «{q}» → {t[:60]}')
        chk(not errs, f'منو اللاعب أخطاء {errs}')
        # قيّم اللاعبين: الاسم المعروف بين قوسين
        rd = {'updated': '', 'matches': [{'id': 'T1', 'wk': 9, 't': 1795092300000 - 4 * 3600e3, 'st': 6,
              'h': {'c': P['c'], 'name': 'x', 'pl': [{'i': '1', 'k': pid, 'n': P['n'].split()[0], 'f': P['n'], 'no': P['no'], 'p': 'M', 's': 1}]},
              'a': {'c': 'ajman', 'name': 'y', 'pl': []}}]}
        pg, errs = await page(b, '')
        await pg.route('**/rate/data.json*', lambda r: r.fulfill(status=200, body=json.dumps(rd), content_type='application/json'))
        await pg.goto(B + '/rate/?m=T1'); await pg.wait_for_timeout(3000)
        t = await pg.text_content('body')
        chk(f'({ar})' in t, 'قيّم اللاعبين: الاسم المعروف ما طلع بين قوسين')
        chk(not errs, f'قيّم اللاعبين أخطاء {errs}')
        await b.close()
    print(f'النتيجة: {ok} نجح · {fail} فشل')
    sys.exit(1 if fail else 0)


asyncio.run(main())
