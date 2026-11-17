"""«دوري الجماهير» v2 — الترتيبات الأربعة بمجموع النقاط (قوانين v2، 17 نوفمبر 2026، _tools/rules/README.md).

التشغيل من جذر المستودع: python3 _tools/fans/build.py   (rate.yml كل 8 دقايق وقت المباريات، fans-live.yml كل ساعة، fans-week.yml)
  الأسبوع: الثلاثاء 00:00 لين نهاية الإثنين (الإمارات). يصير نهائي بعد نهايته بـ40 دقيقة ويتثبت.
  النقاط: 🕵️ منو اللاعب؟ 7 − المحاولة لكل تحدي (لاعب اليوم + الخبير) · 🔮 دوري التوقعات من predict/table.json (10/6/4/0 ×2).
  الترتيبات: المشجعين والأندية، في كل تحدي وفي كل التحديات، كل أسبوع وفي الموسم = مجموع النقاط. عدد المسجلين ما يدخل أبداً.
  التعادل: مشجعين ← (الخبير/بالضبط) ← مرات «من أول محاولة» ← الأسبق ← نفس المركز. أندية ← (الخبير/بالضبط) ← نفس المركز.
  الموسم = fans/acc.json (مجموع الأسابيع النهائية، يتحدث مرة وحدة لكل أسبوع) + الأسابيع اللي ما صارت نهائية.
  fans/ranks.json: مركز كل مشجع (uid12) عشان يشوف مركزه حتى لو ما كتب اسمه.
  الأسماء (f) ونتايج المشجعين (p) تنقرا بمفتاح FIREBASE_SA بس. fans/hide.json يخفي أي اسم.
"""
import json, os, sys, time, urllib.request, urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB = os.environ.get('FBDB', 'https://el3azy-3b64e-default-rtdb.europe-west1.firebasedatabase.app')
NS = os.environ.get('FBNS', '')
UAE = timezone(timedelta(hours=4))
START = 1794859200000          # يوم 1 = الثلاثاء 17 نوفمبر 2026 00:00 الإمارات
DAYMS, WEEK = 86400000, 7
CLUBS = ['ain', 'wahda', 'jazira', 'shababahli', 'sharjah', 'wasl', 'nasr', 'baniyas', 'ajman', 'kalba', 'khorfakkan', 'dhafra', 'hatta', 'united']
NAME = {'ain': 'العين', 'wahda': 'الوحدة', 'jazira': 'الجزيرة', 'shababahli': 'شباب الأهلي', 'sharjah': 'الشارقة', 'wasl': 'الوصل', 'nasr': 'النصر',
        'baniyas': 'بني ياس', 'ajman': 'عجمان', 'kalba': 'كلباء', 'khorfakkan': 'خورفكان', 'dhafra': 'الظفرة', 'hatta': 'حتا', 'united': 'يونايتد'}
MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']


def hdrs():
    if os.environ.get('TOKEN'):
        return {'Authorization': 'Bearer ' + os.environ['TOKEN']}
    sa = os.environ.get('FIREBASE_SA', '').strip()
    if not sa:
        return None
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    cr = service_account.Credentials.from_service_account_info(json.loads(sa), scopes=[
        'https://www.googleapis.com/auth/firebase.database', 'https://www.googleapis.com/auth/userinfo.email'])
    cr.refresh(Request())
    return {'Authorization': 'Bearer ' + cr.token}


def fb(path, q=None, h=None):
    qs = dict(q or {})
    if NS:
        qs['ns'] = NS
    u = f'{DB}/{path}.json' + ('?' + urllib.parse.urlencode(qs) if qs else '')
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=h or {}), timeout=40) as r:
                return json.loads(r.read().decode('utf8'))
        except Exception as e:
            if k == 2:
                # ما نكمل ببيانات ناقصة: لو انحسب الأسبوع على أصفار وانقفل، يظل غلط للأبد
                raise RuntimeError(f'Firebase {path}: {e}')
            time.sleep(3)


def day_of(ms):
    return (ms - START) // DAYMS + 1


def week_of_day(d):
    return (d - 1) // WEEK + 1


def dlabel(ms):
    t = datetime.fromtimestamp(ms / 1000, UAE)
    return f'{t.day} {MONTHS[t.month - 1]}'


def avg2(t, n):
    """المعدل لخانتين بتقريب نص لفوق، بحساب أعداد صحيحة (نفس الصفحات: Math.floor((200t+n)/(2n))/100)"""
    return (200 * t + n) // (2 * n) / 100 if n else 0


def final_at(w):
    """الأسبوع w يصير نهائي بعد نهايته بـ40 دقيقة (مهلة الـ15 دقيقة للنتايج + مباريات الإثنين المتأخرة)"""
    return START + w * WEEK * DAYMS + 40 * 60000



TOP = 10


def rank(rows, key, top=None):
    """رتّب بالمفتاح، والمتساويين بالكامل ياخذون نفس المركز. يرجع [(مركز، صف)]."""
    rows = sorted(rows, key=lambda r: (key(r), r.get('nm', ''), r.get('c', '')))
    out, rk = [], 0
    for i, r in enumerate(rows):
        if i == 0 or key(r) != key(rows[i - 1]):
            rk = i + 1
        if top and rk > top:
            break
        out.append((rk, r))
    return out


KEYS = {   # مفاتيح الترتيب لكل لوحة (أصغر = أحسن)
    'all': lambda x: (-(x['m'] + x['p']), -(x['pro'] + x['e']), -x['one'], x['at'] or 9e15),
    'mano': lambda x: (-x['m'], -x['pro'], -x['one'], x['atm'] or 9e15),
    'pred': lambda x: (-x['p'], -x['e'], x['atp'] or 9e15),
}
CKEYS = {
    'all': lambda c: (-(c['m'] + c['p']), -(c['mpro'] + c['pe'])),
    'mano': lambda c: (-c['m'], -c['mpro']),
    'pred': lambda c: (-c['p'], -c['pe']),
}
PTS = {'all': lambda x: x['m'] + x['p'], 'mano': lambda x: x['m'], 'pred': lambda x: x['p']}


def new_user():
    return {'m': 0, 'p': 0, 'pro': 0, 'one': 0, 'e': 0, 'at': 0, 'atm': 0, 'atp': 0, 'c': '', 'nm': ''}


def new_club():
    return {'m': 0, 'mn': 0, 'mpro': 0, 'p': 0, 'pn': 0, 'pe': 0}


def add_user(a, b):
    for k in ('m', 'p', 'pro', 'one', 'e'):
        a[k] += b[k]
    for k in ('at', 'atm', 'atp'):
        a[k] = max(a[k], b[k])
    a['c'] = b['c'] or a['c']; a['nm'] = b['nm'] or a['nm']


def add_club(a, b):
    for k in a:
        a[k] += b.get(k, 0)


def week_data(d0, d1, c_all, p_all, rds, pred_t, last_t):
    """نقاط الأندية والمشجعين في أيام [d0..d1] + جولات التوقعات rds."""
    clubs = {c: new_club() for c in CLUBS}
    for d, v in (c_all or {}).items():
        if not v or not (d0 <= int(d) <= d1):
            continue
        for m in ('easy', 'pro'):
            for c, x in (v.get(m) or {}).items():
                if c in clubs and x:
                    clubs[c]['m'] += x.get('t', 0) or 0
                    if m == 'easy':
                        clubs[c]['mn'] += x.get('n', 0) or 0
                    else:
                        clubs[c]['mpro'] += x.get('t', 0) or 0
    users = defaultdict(new_user)
    for d, v in (p_all or {}).items():
        if not v or not (d0 <= int(d) <= d1):
            continue
        for m in ('easy', 'pro'):
            for u, x in (v.get(m) or {}).items():
                x = x or {}
                g = x.get('g') or 0
                s = users[u[:12]]
                s['c'] = x.get('c') or s['c']
                if g:
                    s['m'] += 7 - g
                    if m == 'pro':
                        s['pro'] += 7 - g
                    if g == 1:
                        s['one'] += 1
                    t = x.get('t') or START + (int(d) - 1) * DAYMS   # قبل حفظ الوقت (17 نوفمبر 02:30): بداية يومه
                    s['atm'] = max(s['atm'], t); s['at'] = max(s['at'], t)
    for r in rds:
        for row in pred_t.get('clubs', {}).get(r, []):
            c = row[0]
            if c in clubs:
                clubs[c]['p'] += row[3] if len(row) > 3 else round(row[1] * row[2])
                clubs[c]['pn'] += row[2]
                clubs[c]['pe'] += row[4] if len(row) > 4 else 0
        for row in pred_t.get('rounds', {}).get(r, []):
            u, nm, c, pt = row[:4]
            s = users[u]
            s['p'] += pt; s['e'] += row[4] if len(row) > 4 else 0
            s['nm'] = s['nm'] or nm
            if not s['c'] or s['c'] == 'none':
                s['c'] = c
            if pt:
                t = row[6] if len(row) > 6 and row[6] else last_t.get(int(r), 0)
                s['atp'] = max(s['atp'], t); s['at'] = max(s['at'], t)
    return clubs, users


def boards(clubs, users, names, hide):
    """اللوحات: الأندية (كل التحديات/منو اللاعب/التوقعات) + أول 10 مشجعين لكل وحدة + مراكز الكل."""
    out = {'clubs': {}, 'fans': {}, 'more': {}}
    crow = [dict(v, c=c) for c, v in clubs.items()]
    for b, k in CKEYS.items():
        val = {'all': lambda c: c['m'] + c['p'], 'mano': lambda c: c['m'], 'pred': lambda c: c['p']}[b]
        # الصف: [النادي، المركز، النقاط في هاللوحة، نقاط منو اللاعب، نقاط التوقعات، لعبات منو اللاعب، مشاركات التوقعات، نقاط الخبير، بالضبط]
        out['clubs'][b] = [[c['c'], rk, val(c), c['m'], c['p'], c['mn'], c['pn'], c['mpro'], c['pe']] for rk, c in rank(crow, k)]
    ranks = {}
    for b, k in KEYS.items():
        pool = [dict(s, u=u) for u, s in users.items() if PTS[b](s) > 0]
        full = rank(pool, k)
        for rk, x in full:
            ranks.setdefault(x['u'], {})[b] = [rk, PTS[b](x), len(full)]
        named = []
        for rk, x in full:
            nm = (names.get(x['u']) or {}).get('n', '') if names else x['nm']
            c = (names.get(x['u']) or {}).get('c') if names else x['c']
            c = c if c in NAME else (x['c'] if x['c'] in NAME else '')
            if nm.strip() and c and x['u'] not in hide:
                named.append([nm.strip()[:16], c, PTS[b](x), rk, x['u']])
        top = [r for r in named if r[3] <= named[min(TOP, len(named)) - 1][3]] if named else []
        out['fans'][b] = top[:TOP]
        out['more'][b] = max(0, len(top) - TOP)
    return out, ranks


def main():
    now = int(os.environ.get('NOW') or time.time() * 1000)
    today = max(1, day_of(now))
    cur = week_of_day(today) if now >= START else 0
    H = hdrs()
    pred_t = json.load(open(os.path.join(ROOT, 'predict/table.json'), encoding='utf8'))
    pred_d = json.load(open(os.path.join(ROOT, 'predict/data.json'), encoding='utf8'))
    hide = set()
    try:
        hide = set(json.load(open(os.path.join(ROOT, 'fans/hide.json'), encoding='utf8')))
    except Exception:
        pass
    # جولات التوقعات → الأسبوع اللي فيه أكثر مبارياتها (لو تساوى أسبوعين: المتأخر)
    last_t = defaultdict(int)
    per_week = defaultdict(lambda: defaultdict(int))
    for m in pred_d.get('matches', pred_d if isinstance(pred_d, list) else []):
        if m.get('t', 0) >= START:
            last_t[m['wk']] = max(last_t[m['wk']], m['t'])
            per_week[m['wk']][week_of_day(day_of(m['t']))] += 1
    round_week = {str(r): max(ws.items(), key=lambda kv: (kv[1], kv[0]))[0] for r, ws in per_week.items()}

    path = os.path.join(ROOT, 'fans/data.json')
    acc_path = os.path.join(ROOT, 'fans/acc.json')
    prev_out, acc = {}, {'weeks': [], 'rds': [], 'users': {}, 'clubs': {}}
    try:
        prev_out = json.load(open(path, encoding='utf8'))
    except Exception:
        pass
    try:
        acc = json.load(open(acc_path, encoding='utf8')) if not os.environ.get('FULL') else acc
    except Exception:
        pass
    if prev_out.get('v') != 2:      # أول تشغيل بالقوانين v2: نبدا من الصفر
        prev_out, acc = {}, {'weeks': [], 'rds': [], 'users': {}, 'clubs': {}}
    if H is None and acc['weeks']:   # بدون المفتاح ما نقدر نضيف أسابيع للتراكم: نكمل باللي عندنا ونعرض بس
        pass
    kept = [w for w in prev_out.get('weeks', []) if w['w'] in acc['weeks']]
    first = max(acc['weeks'] or [0]) + 1
    counted = set(acc.get('rds', []))
    q = {'orderBy': '"$key"', 'startAt': '"' + str((first - 1) * WEEK + 1) + '"', 'endAt': '"' + str(max(first, cur) * WEEK) + '"'}
    c_all = fb('c', q) if cur else {}
    if isinstance(c_all, list):
        c_all = {str(i): v for i, v in enumerate(c_all) if v}
    p_all = (fb('p', q, H) or {}) if H and cur else {}
    if isinstance(p_all, list):
        p_all = {str(i): v for i, v in enumerate(p_all) if v}
    names = (fb('f', None, H) or {}) if H else {}
    names = {u[:12]: v for u, v in names.items() if isinstance(v, dict)}

    weeks = list(kept)
    live_users, live_clubs = defaultdict(new_user), {c: new_club() for c in CLUBS}
    for w in range(first, cur + 1):
        d0, d1 = (w - 1) * WEEK + 1, w * WEEK
        rds = sorted(r for r, wk in round_week.items() if wk == w and r not in counted)
        clubs, users = week_data(d0, d1, c_all, p_all, rds, pred_t, last_t)
        bd, ranks = boards(clubs, users, names, hide)
        final = now >= final_at(w) and w < cur
        weeks.append({'w': w, 'from': dlabel(START + (d0 - 1) * DAYMS), 'to': dlabel(START + (d1 - 1) * DAYMS),
                      'live': w == cur, 'final': final, 'pred': bool(rds), 'rds': rds, **bd})
        if final and H:   # الأسبوع صار نهائي: نضيفه للتراكم مرة وحدة
            for u, s in users.items():
                add_user(acc['users'].setdefault(u, new_user()), s)
            for c, v in clubs.items():
                add_club(acc['clubs'].setdefault(c, new_club()), v)
            acc['weeks'].append(w); acc['rds'] = sorted(set(acc['rds']) | set(rds))
        else:
            for u, s in users.items():
                add_user(live_users[u], s)
            for c, v in clubs.items():
                add_club(live_clubs[c], v)
        if w == cur:
            week_ranks = ranks
    # الموسم = التراكم + الأسابيع اللي ما صارت نهائية
    s_users = defaultdict(new_user)
    for src in (acc['users'], live_users):
        for u, s in src.items():
            add_user(s_users[u], s)
    s_clubs = {c: new_club() for c in CLUBS}
    for src in (acc['clubs'], live_clubs):
        for c, v in src.items():
            if c in s_clubs:
                add_club(s_clubs[c], v)
    season, s_ranks = boards(s_clubs, s_users, names, hide)
    # القصة (لصورة الأسبوع): من آخر أسبوع نهائي
    story = ''
    done = [x for x in weeks if x.get('final')]
    if done:
        L = done[-1]
        lead = season['clubs']['all'][0] if season['clubs']['all'] else None
        wk_lead = L['clubs']['all'][0] if L['clubs']['all'] else None
        if lead and lead[2] > 0:
            story = f"جمهور {NAME[lead[0]]} يتصدر الموسم بـ{lead[2]:,} نقطة"
            if wk_lead and wk_lead[0] != lead[0] and wk_lead[2] > 0:
                story += f"، و{NAME[wk_lead[0]]} أقوى جمهور في الأسبوع {L['w']} ({wk_lead[2]:,})"
    out = {'v': 2, 'updated': datetime.fromtimestamp(now / 1000, UAE).strftime('%Y-%m-%d %H:%M'), 'cur': cur, 'done': len(done),
           'ends': START + cur * WEEK * DAYMS if cur else START, 'weeks': weeks, 'season': season, 'story': story, 'names': bool(H)}
    os.makedirs(os.path.join(ROOT, 'fans'), exist_ok=True)
    new = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    old = open(path, encoding='utf8').read() if os.path.exists(path) else ''
    strip = lambda s: s.split(',"cur"', 1)[-1] if s else ''
    if strip(old) != strip(new):   # ما نكتب الملف لو تغير وقت التحديث بس
        open(path, 'w', encoding='utf8').write(new)
        print('fans/data.json ✓', 'الأسبوع', cur, 'نهائي', len(done))
    else:
        print('fans/data.json ما تغير')
    if H:
        json.dump(acc, open(acc_path, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
        rk = {'w': cur, 'week': week_ranks if cur else {}, 'season': s_ranks}
        json.dump(rk, open(os.path.join(ROOT, 'fans/ranks.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
