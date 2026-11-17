"""«باص الفريق» — المُعيد: يعيد كل سباق في «مرحلة اليوم» من حركات اللاعب، ويكتب النتيجة الحقيقية في bv.

ليش؟ النتيجة تنحسب في تلفون اللاعب، فأي أحد يقدر يرسل «3 نجوم» بدون ما يلعب. اللعبة حتمية (نفس الحركات =
نفس النتيجة بالضبط)، فالمُعيد يشغّل محرك اللعبة نفسه (bus/index.html#qa) ويعيد السباق، والنتيجة اللي تنحسب
في دوري الجماهير هي اللي طلعت من الإعادة بس.

  b/<يوم>/<uid>/<1..3> = {s, r, k, c, d, t}   (يكتبها التلفون، القواعد في make_rules.py)
  bv/<يوم>/<uid>/<1..3> = {ok, w, rt, np, st, cr, fn, tl, sc, sec, c, t}   (يكتبها هالملف بحساب الخدمة)

  python3 _tools/bus/verify.py            # اليوم وأمس
  FBDB=http://127.0.0.1:9000 FBNS=demo-el3 TOKEN=owner python3 _tools/bus/verify.py   # المحاكي
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB = os.environ.get('FBDB', 'https://el3azy-3b64e-default-rtdb.europe-west1.firebasedatabase.app')
NS = os.environ.get('FBNS', '')
START = 1794859200000
DAYMS = 86400000
UAE = timezone(timedelta(hours=4))
PORT = int(os.environ.get('BUS_PORT') or 8799)


def hdrs():
    if os.environ.get('TOKEN'):
        return {'Authorization': 'Bearer ' + os.environ['TOKEN']}
    sa = os.environ.get('FIREBASE_SA', '').strip()
    if not sa:
        sys.exit('يحتاج FIREBASE_SA')
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    cr = service_account.Credentials.from_service_account_info(json.loads(sa), scopes=[
        'https://www.googleapis.com/auth/firebase.database', 'https://www.googleapis.com/auth/userinfo.email'])
    cr.refresh(Request())
    return {'Authorization': 'Bearer ' + cr.token}


def req(method, path, h, body=None):
    u = f'{DB}/{path}.json' + (f'?ns={NS}' if NS else '')
    r = urllib.request.Request(u, method=method, headers={**h, 'Content-Type': 'application/json'},
                               data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(r, timeout=40) as x:
        return json.loads(x.read().decode() or 'null')


def decode(k):
    """«b:n,b:n» (b = أزرار اليمين/اليسار/الفرامل/النيترو بالهكس، n = عدد الخطوات) ⇒ قائمة خطوات."""
    out = []
    for part in (k or '').split(','):
        if not part:
            continue
        b, n = part.split(':')
        out += [int(b, 16)] * min(int(n), 20000)
        if len(out) > 20000:
            break
    return out[:20000]


def encode(steps):
    out, prev, n = [], None, 0
    for b in steps:
        if b == prev:
            n += 1
        else:
            if prev is not None:
                out.append(f'{prev:x}:{n}')
            prev, n = b, 1
    if prev is not None:
        out.append(f'{prev:x}:{n}')
    return ','.join(out)


def ymd(d):
    t = datetime.fromtimestamp((START + (d - 1) * DAYMS) / 1000, UAE)
    return t.year * 10000 + t.month * 100 + t.day


def as_runs(v):
    if isinstance(v, list):
        return {str(i): x for i, x in enumerate(v) if x}
    return {k: x for k, x in (v or {}).items() if x}


REPLAY = """([day, dnum, r, steps]) => {
  const B = window.__bus;
  // يحتاج من اللعبة (bus/index.html → window.__bus): daily(يوم المنصة) = ملعب مرحلة اليوم، و sim() يرجّع np (اللاعبين اللي ركبوا)
  const stage = B.daily(Math.floor((START_MS + 4 * 3600e3) / 864e5) + dnum - 1);
  const st = r.split('_')[0];
  if (st !== stage) return {ok: 0, why: 'مب مرحلة اليوم (' + stage + ')'};
  if (!B.routes().includes(r)) return {ok: 0, why: 'طريق غير معروف'};
  B.day = day; B.setRoute(r);
  const s = B.sim(steps);
  const nP = s.np, w = s.state === 'finish' && s.timeLeft > 0 ? 1 : 0;
  const tl = Math.max(0, s.timeLeft);
  const rt = w ? (tl >= B.STAR3 && s.fines === 0 && nP === 3 ? 3 : nP >= 2 ? 2 : 1) : 0;
  const sc = w ? Math.max(0, Math.round(tl * 10) * 10 + s.stars * 50 + nP * 300 - s.crashes * 30) : 0;
  return {ok: 1, w, rt, np: nP, st: s.stars, cr: s.crashes, fn: s.fines, tl: Math.round(tl * 100) / 100, sc, sec: Math.round(s.steps / 60)};
}""".replace('START_MS', str(START))


def main():
    h = hdrs()
    now = int(os.environ.get('NOW') or time.time() * 1000)
    today = max(1, (now - START) // DAYMS + 1)
    days = [d for d in (today - 1, today) if d >= 1]
    todo = []
    for d in days:
        runs = req('GET', f'b/{d}', h) or {}
        done = req('GET', f'bv/{d}', h) or {}
        for u, rs in (runs or {}).items():
            for i, x in as_runs(rs).items():
                if not (as_runs((done or {}).get(u)) or {}).get(i):
                    todo.append((d, u, i, x))
    if not todo:
        print('bus verify: ما في سباقات يديدة')
        return
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            exe = os.environ.get('CHROME') or ('/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None)
            b = p.chromium.launch(**({'executable_path': exe} if exe else {}))
            pg = b.new_page(viewport={'width': 390, 'height': 800})
            pg.route('**/*.mp3', lambda r: r.abort())
            pg.goto(f'http://127.0.0.1:{PORT}/bus/#qa')
            pg.wait_for_function('window.__bus && window.__bus.routes().length > 0', timeout=60000)
            out = {}
            for d, u, i, x in todo:
                try:
                    res = pg.evaluate(REPLAY, [ymd(d), d, x.get('r', ''), decode(x.get('k', ''))])
                except Exception as e:
                    res = {'ok': 0, 'why': 'خطأ في الإعادة: ' + str(e)[:80]}
                res.update({'c': x.get('c', ''), 't': x.get('t', 0)})
                out[f'{d}/{u}/{i}'] = res
            b.close()
        req('PATCH', 'bv', h, out)
        good = sum(1 for v in out.values() if v.get('ok'))
        print(f'bus verify: {len(out)} سباق انعاد ({good} صالح)')
    finally:
        srv.terminate()


if __name__ == '__main__':
    main()
