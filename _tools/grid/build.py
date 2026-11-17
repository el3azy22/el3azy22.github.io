"""«شبكة الدوري» — مولّد الشبكات اليومية وجدولها المخفي.

كل يوم شبكة 3 أندية × 3 شروط. الجدول ينحفظ في Firebase (gq/<يوم>) مع الأجوبة الصحيحة لكل خانة،
والقواعد تخلي كل يوم يتقرى بس من 12 بالليل حقه (مثل q في «منو اللاعب؟»)، والكتابة لحساب الخدمة بس.

قوانين المولّد (قرار إبراهيم 17 نوفمبر، _tools/rules/DECISIONS.md):
  - 3 أندية مختلفة · 3 شروط مختلفة · عمود مركّب واحد بالكثير · شرط عمر بروحه واحد بالكثير · مركز بروحه (غير الحارس) واحد بالكثير
  - كل خانة فيها من 2 إلى 12 جواب من اللاعبين اللي شاركوا في مباريات هالموسم (عشان ما تكون الخانة كلها لاعبين
    ما حد يعرفهم)، والبدلاء اللي ما شاركوا ينقبلون بعد، بس كل الأجوبة 20 بالكثير
  - ما تتكرر نفس الشبكة، والأندية تتوزع بالتساوي تقريباً
  - اليوم الحالي ما يتغير أبداً (لو انتقل لاعب، الأجوبة المحفوظة مع الشبكة هي المرجع)، والأيام الجاية تنبني من يديد
    كل ليلة 11:17 من آخر بيانات (الأهداف والانتقالات)

  python3 _tools/grid/build.py preview [أيام]   # يطبع شبكات تجريبية بدون ما يكتب شي
  python3 _tools/grid/build.py push [أيام]      # يكمّل الجدول لين اليوم+أيام (يحتاج FIREBASE_SA أو TOKEN للمحاكي)
"""
import json, os, random, sys, time, urllib.request
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB = os.environ.get('FBDB', 'https://el3azy-3b64e-default-rtdb.europe-west1.firebasedatabase.app')
NS = os.environ.get('FBNS', '')
START = 1794859200000          # اليوم 1 = الثلاثاء 17 نوفمبر 2026 00:00 الإمارات
DAYMS = 86400000
try:     # أول يوم للشبكة (رقم يوم المنصة). 0 = ما انطلقت. المصدر الوحيد: grid/config.json
    GRID_START = int(json.load(open(os.path.join(ROOT, 'grid', 'config.json'), encoding='utf8')).get('start') or 0)
except Exception:
    GRID_START = 0
GRID_START = int(os.environ.get('GRID_START') or GRID_START)
MIN_ANS, MAX_ANS, MAX_ALL = 2, 12, 20   # المشاركين هالموسم 2–12، وكل الأجوبة (مع البدلاء) 20 بالكثير
WT = {'nat': 4, 'mix': 3, 'gl': 2, 'st': 2, 'num': 0.6, 'age': 0.7, 'pos': 1}
POS = {'GK': 'حارس', 'DF': 'دفاع', 'MD': 'وسط', 'FW': 'هجوم'}


def flag(code):
    code = (code or '').upper()
    return ''.join(chr(0x1F1E6 + ord(ch) - 65) for ch in code) if len(code) == 2 and code.isalpha() else '🏳️'


def catalog(players):
    """كل الشروط الممكنة: {id: {t: نوع, l: عنوان العمود, q: نص السؤال, ic: أيقونة, f: دالة}}."""
    C = {}
    nats = Counter(p['nat'] for p in players if p.get('nat') and p['nat'] != 'الإمارات')
    fl = {}
    for p in players:
        fl.setdefault(p.get('nat'), p.get('f'))
    for nat, n in nats.items():
        if n >= 6:   # الجنسيات اللي فيها لاعبين يكفون عشان تطلع في أكثر من نادي
            C['n:' + nat] = {'t': 'nat', 'l': nat, 'q': f'لاعب جنسيته {nat}', 'ic': flag(fl.get(nat)),
                             'f': (lambda nat: lambda p: p.get('nat') == nat)(nat)}
    for k, nm in POS.items():
        C['p:' + k] = {'t': 'pos', 'l': nm, 'q': f'لاعب مركزه {nm}', 'ic': 'pos:' + k,
                       'f': (lambda k: lambda p: p.get('p') == k)(k)}
    C['a:30'] = {'t': 'age', 'l': 'العمر 30+', 'q': 'لاعب عمره 30 سنة أو أكثر', 'ic': 'txt:30+', 'f': lambda p: (p.get('a') or 0) >= 30}
    C['a:21'] = {'t': 'age', 'l': 'العمر 21 أو أقل', 'q': 'لاعب عمره 21 سنة أو أقل', 'ic': 'txt:21-', 'f': lambda p: 0 < (p.get('a') or 0) <= 21}
    C['no:1-11'] = {'t': 'num', 'l': 'رقم القميص من 1 إلى 11', 'q': 'لاعب رقم قميصه من 1 إلى 11', 'ic': 'shirt',
                    'f': lambda p: str(p.get('no') or '').isdigit() and 1 <= int(p['no']) <= 11}
    # وضع اللاعب في قائمة الدوري (من بيانات الرابطة): مواطن · مقيم
    C['st:cit'] = {'t': 'st', 'l': 'مواطن', 'q': 'لاعب مواطن', 'ic': 'flag:AE', 'f': lambda p: p.get('st') == 'cit'}
    C['st:res'] = {'t': 'st', 'l': 'مقيم', 'q': 'لاعب مقيم', 'ic': 'txt:مقيم', 'f': lambda p: p.get('st') == 'res'}
    # الأهداف: سجّل في الدوري هالموسم (حسب آخر تحديث للبيانات قبل الشبكة)
    C['gl:1'] = {'t': 'gl', 'l': 'سجّل هدف هالموسم', 'q': 'لاعب سجّل هدف أو أكثر في الدوري هالموسم', 'ic': 'ball', 'f': lambda p: (p.get('gl') or 0) >= 1}
    # المركّبة: مركز + عمر، أو مركز + البرازيل (أكثر جنسية أجنبية)
    for k, nm in POS.items():
        if k != 'GK':
            C[f'p:{k}+a:30'] = {'t': 'mix', 'l': f'{nm} والعمر 30+', 'q': f'لاعب مركزه {nm}، وعمره 30 سنة أو أكثر', 'ic': 'pos:' + k,
                                'f': (lambda k: lambda p: p.get('p') == k and (p.get('a') or 0) >= 30)(k)}
            C[f'p:{k}+a:21'] = {'t': 'mix', 'l': f'{nm} والعمر 21 أو أقل', 'q': f'لاعب مركزه {nm}، وعمره 21 سنة أو أقل', 'ic': 'pos:' + k,
                                'f': (lambda k: lambda p: p.get('p') == k and 0 < (p.get('a') or 0) <= 21)(k)}
            C[f'p:{k}+st:res'] = {'t': 'mix', 'l': f'{nm} مقيم', 'q': f'لاعب مركزه {nm}، ومقيم', 'ic': 'pos:' + k,
                                  'f': (lambda k: lambda p: p.get('p') == k and p.get('st') == 'res')(k)}
            C[f'p:{k}+st:cit'] = {'t': 'mix', 'l': f'{nm} مواطن', 'q': f'لاعب مركزه {nm}، ومواطن', 'ic': 'pos:' + k,
                                  'f': (lambda k: lambda p: p.get('p') == k and p.get('st') == 'cit')(k)}
            C[f'p:{k}+n:البرازيل'] = {'t': 'mix', 'l': f'{nm} من البرازيل', 'q': f'لاعب مركزه {nm}، وجنسيته البرازيل', 'ic': 'pos:' + k,
                                      'f': (lambda k: lambda p: p.get('p') == k and p.get('nat') == 'البرازيل')(k)}
    return C


def answers(players, club, cond):
    return sorted(p['id'] for p in players if p['c'] == club and cond['f'](p))


def ok_cols(cols, C):
    ts = [C[c]['t'] for c in cols]
    if ts.count('mix') > 1:
        return False
    if ts.count('age') > 1:
        return False
    # «العمر 30+» مع «وسط والعمر 30+» تكرار: العمر بروحه والمركّب لازم بحدود مختلفة
    sts = [c.split('st:')[1] for c in cols if 'st:' in c]
    if len(sts) != len(set(sts)):
        return False
    ages = [c.split('a:')[1] for c in cols if 'a:' in c]
    if len(ages) != len(set(ages)):
        return False
    if ts.count('nat') > 2 or ts.count('num') > 1 or ts.count('st') > 1 or ts.count('gl') > 1:
        return False
    # ما يطلع مركز بروحه مع مركّب فيه نفس المركز (هجوم + هجوم من البرازيل)
    poss = [c.split('+')[0] for c in cols if c.startswith('p:')]
    if len(poss) != len(set(poss)):
        return False
    # مركز بروحه (دفاع/وسط/هجوم) واحد بالكثير، عشان الشبكة ما تكون كلها مراكز سهلة
    return sum(1 for c in cols if C[c]['t'] == 'pos' and c != 'p:GK') <= 1


def valid_cells(players, C):
    """{(نادي، شرط): أجوبة} للخانات الصالحة: 2–12 جواب، ومنهم 2 على الأقل شاركوا هالموسم."""
    V = {}
    for club in sorted({p['c'] for p in players}):
        for k, cond in C.items():
            a = [p for p in players if p['c'] == club and cond['f'](p)]
            kn = sum(1 for p in a if (p.get('ap') or 0) > 0)
            if MIN_ANS <= kn <= MAX_ANS and len(a) <= MAX_ALL:
                V[(club, k)] = sorted(p['id'] for p in a)
    return V


def make_grid(players, C, rng, club_use, recent, V=None, tries=20000, cond_use=None):
    cond_use = cond_use if cond_use is not None else Counter()
    V = V if V is not None else valid_cells(players, C)
    clubs = sorted({p['c'] for p in players})
    ids = sorted(C)
    for _ in range(tries):
        # الأندية أولاً: الأقل ظهوراً لها أولوية قوية (كل الأندية تطلع بالتساوي تقريباً)
        rows = []
        while len(rows) < 3:
            c = rng.choices(clubs, [1.0 / (1 + club_use[x]) ** 4 for x in clubs])[0]
            if c not in rows:
                rows.append(c)
        cand = [k for k in ids if all((r, k) in V for r in rows)]
        if len(cand) < 3:
            continue
        # بعدها الشروط اللي تصلح للثلاثة (الجنسيات والمركّبة وزنها أكبر)
        wts = [WT.get(C[k]['t'], 1) / (1 + cond_use[k] / 4) for k in cand]   # الشرط اللي تكرر وايد وزنه يقل
        for _ in range(40):
            cols = []
            while len(cols) < 3:
                k = rng.choices(cand, wts)[0]
                if k not in cols:
                    cols.append(k)
            if ok_cols(cols, C):
                break
        else:
            continue
        sig = (tuple(sorted(rows)), tuple(sorted(cols)))
        if sig in recent:
            continue
        A = {f'{i}{j}': V[(r, c)] for i, r in enumerate(rows) for j, c in enumerate(cols)}
        return {'r': rows, 'c': [{'id': c, 'l': C[c]['l'], 'q': C[c]['q'], 'ic': C[c]['ic']} for c in cols], 'a': A}, sig
    raise SystemExit('ما قدرت أبني شبكة تحقق الشروط')


def players():
    return json.load(open(os.path.join(ROOT, 'mano', 'data.json'), encoding='utf8'))['players']


def today():
    return max(1, (int(time.time() * 1000) - START) // DAYMS + 1)


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
                               data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None)
    with urllib.request.urlopen(r, timeout=40) as x:
        return json.loads(x.read().decode() or 'null')


def fill(existing, first, last, P, rng):
    """يكمّل الجدول: الأيام first..last. اليوم الحالي واللي بعده ثابتين لو موجودين."""
    C = catalog(P)
    V = valid_cells(P, C)
    out, club_use, recent, cond_use = {}, Counter(), set(), Counter()
    lock_until = today()
    for d in range(first, last + 1):
        g = existing.get(str(d))
        if g and d <= lock_until:
            out[str(d)] = g
        else:
            g, sig = make_grid(P, C, rng, club_use, recent, V, cond_use=cond_use)
            g['n'] = d - first + 1 if not GRID_START else d - GRID_START + 1
            out[str(d)] = g
        for c in out[str(d)]['r']:
            club_use[c] += 1
        for c in out[str(d)]['c']:
            cond_use[c['id']] += 1
        recent.add((tuple(sorted(out[str(d)]['r'])), tuple(sorted(x['id'] for x in out[str(d)]['c']))))
    return out


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    ahead = int(sys.argv[2]) if len(sys.argv) > 2 else 21
    P = players()
    first = GRID_START or today()
    last = max(first, today()) + ahead
    if cmd == 'preview':
        g = fill({}, first, first + ahead - 1, P, random.Random(7))
        C = catalog(P)
        for d, x in list(g.items())[:5]:
            print(d, x['r'], [c['l'] for c in x['c']], {k: len(v) for k, v in x['a'].items()})
        sizes = [len(v) for x in g.values() for v in x['a'].values()]
        print('أيام', len(g), '· أجوبة الخانة: أقل', min(sizes), 'أكثر', max(sizes), 'متوسط', round(sum(sizes) / len(sizes), 1), '· شروط', len(C))
        return
    if cmd == 'push':
        if not GRID_START:
            print('الشبكة ما انطلقت (grid/config.json start = 0) — ما سويت شي')
            return
        h = hdrs()
        ex = req('GET', 'gq', h) or {}
        if isinstance(ex, list):
            ex = {str(i): v for i, v in enumerate(ex) if v}
        new = fill(ex, first, last, P, random.SystemRandom())
        req('PATCH', 'gq', h, new)
        back = req('GET', 'gq', h) or {}
        if isinstance(back, list):
            back = {str(i): v for i, v in enumerate(back) if v}
        assert all(back.get(k) == v for k, v in new.items()), 'الجدول اللي انكتب غير اللي انقرى'
        print(f'gq ✓ الأيام {first}..{last}')


if __name__ == '__main__':
    main()
