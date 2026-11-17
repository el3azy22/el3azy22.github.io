"""«دوري الجماهير» — آلية الترتيب الموحدة لكل تحديات المنصة (القوانين v2، _tools/rules/README.md).

التشغيل من جذر المستودع: python3 _tools/fans/build.py   (rate.yml وقت المباريات، fans-live.yml، fans-week.yml)

الآلية (نفسها لكل تحدي، الحالي والياي):
  المشجع: النقاط ← الأقل أخطاء ← الأكثر لعب ← الأسرع (ثواني) ← نفس المركز.
  النادي: نقاط أفضل 11 مشجع عنده (التشكيلة) ← الأقل أخطاء في التشكيلة ← الأسرع ← نفس المركز.
  اللوحات: «كل التحديات» + لوحة لكل تحدي، كل أسبوع (الثلاثاء–الإثنين، يتثبت الثلاثاء 00:40) وفي الموسم.
  الموسم: المشجع = مجموع نقاطه · النادي = مجموع نقاط تشكيلته في كل أسبوع (مثل جدول الدوري).
  عدد المسجلين في النادي ما يدخل في أي حسبة.

إضافة تحدي يديد: دالة تجمع لكل مشجع {pts, mis, plays, sec, c, ct} وتنضاف لـ CHALLENGES — اللوحات والصفحة تطلع بروحها.
البيانات: fans/data.json (اللوحات) · fans/acc.json (تراكم الأسابيع النهائية) · fans/ranks.json (مركز كل مشجع uid12).
نتايج المشجعين (p) والأسماء (f) تنقرا بمفتاح FIREBASE_SA بس. fans/hide.json يخفي أي اسم.
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



TOP = 10      # أول 10 مراكز تطلع أسماءهم
XI = 11       # تشكيلة النادي
CHALLENGES = [{'id': 'mano', 'name': 'منو اللاعب؟', 'icon': '🕵️'},
              {'id': 'pred', 'name': 'دوري التوقعات', 'icon': '🔮'}]
BOARDS = ['all'] + [c['id'] for c in CHALLENGES]
FAIL_MIS = 6  # منو اللاعب: ما عرفه = 6 أخطاء


def stat():
    return {'pts': 0, 'mis': 0, 'plays': 0, 'sec': 0, 'c': '', 'ct': 0, 'nm': ''}


def add_stat(a, b):
    for k in ('pts', 'mis', 'plays', 'sec'):
        a[k] += b.get(k, 0)
    if b.get('ct', 0) >= a.get('ct', 0) and b.get('c'):
        a['c'], a['ct'] = b['c'], b['ct']
    a['nm'] = b.get('nm') or a.get('nm', '')


def ukey(x):
    """ترتيب المشجعين: النقاط ← الأقل أخطاء ← الأكثر لعب ← الأسرع."""
    return (-x['pts'], x['mis'], -x['plays'], x['sec'])


def ckey(x):
    """ترتيب الأندية: نقاط التشكيلة ← الأقل أخطاء ← الأسرع."""
    return (-x['pts'], x['mis'], x['sec'])


def rank(rows, key):
    """رتّب، والمتساويين بالكامل ياخذون نفس المركز. يرجع [(مركز، صف)]."""
    rows = sorted(rows, key=lambda r: (key(r), r.get('nm', ''), r.get('c', ''), r.get('u', '')))
    out, rk = [], 0
    for i, r in enumerate(rows):
        if i == 0 or key(r) != key(rows[i - 1]):
            rk = i + 1
        out.append((rk, r))
    return out


# ── جامعين النقاط لكل تحدي: {uid12: stat} ──
def collect_mano(p_all, d0, d1):
    users = defaultdict(stat)
    for d, v in (p_all or {}).items():
        if not v or not (d0 <= int(d) <= d1):
            continue
        for m in ('easy', 'pro'):
            for u, x in (v.get(m) or {}).items():
                x = x or {}
                g = x.get('g') or 0
                s = users[u[:12]]
                s['plays'] += 1
                s['pts'] += 7 - g if g else 0
                s['mis'] += g - 1 if g else FAIL_MIS
                s['sec'] += min(int(x.get('sec') or 0), 3600)        # حد ساعة للتحدي الواحد
                t = x.get('t') or START + (int(d) - 1) * DAYMS
                if t >= s['ct']:
                    s['c'], s['ct'] = x.get('c') or s['c'], t
    return users


def collect_pred(rds, pred_t, last_t):
    users = defaultdict(stat)
    for r in rds:
        for row in pred_t.get('rounds', {}).get(r, []):
            u, nm, c, pt = row[:4]
            s = users[u]
            s['pts'] += pt
            s['plays'] += row[5] if len(row) > 5 else 0
            s['mis'] += row[7] if len(row) > 7 else 0
            s['nm'] = s['nm'] or nm
            t = last_t.get(int(r), 0)
            if t >= s['ct'] and c in NAME:
                s['c'], s['ct'] = c, t
    return users


def boards(per, names, hide):
    """per = {challenge: {uid12: stat}} ⇒ اللوحات (أندية + أول 10 مشجعين) + مراكز الكل + تشكيلة كل نادي."""
    allu = defaultdict(stat)
    for ch in per.values():
        for u, s in ch.items():
            add_stat(allu[u], s)
    src = {'all': allu, **per}
    out, ranks = {}, {}
    for b in BOARDS:
        users = src.get(b, {})
        pool = [dict(s, u=u) for u, s in users.items() if s['plays'] > 0]
        full = rank(pool, ukey)
        for rk, x in full:
            if x['pts'] > 0:
                ranks.setdefault(x['u'], {})[b] = [rk, x['pts'], len(full), x['c'] if x['c'] in NAME else '']
        # الأندية: تشكيلة كل نادي = أفضل 11 مشجع لعبوا له
        byc = defaultdict(list)
        for rk, x in full:
            if x['c'] in NAME:
                byc[x['c']].append(x)
        crow = []
        for c in CLUBS:
            xi = byc.get(c, [])[:XI]
            crow.append({'c': c, 'pts': sum(x['pts'] for x in xi), 'mis': sum(x['mis'] for x in xi), 'sec': sum(x['sec'] for x in xi),
                         'xi': len(xi), 'n': len(byc.get(c, []))})
        clubs = [[x['c'], rk, x['pts'], x['xi'], x['n'], x['mis'], x['sec']] for rk, x in rank(crow, ckey)]
        # التشكيلة نفسها (عشان المشجع يشوف من وين جا رقم ناديه): [الاسم أو ''، النقاط، معرف مختصر]
        def nm_of(x):
            if x['u'] in hide:
                return ''
            n = ((names.get(x['u']) or {}).get('n') or '') if names else x['nm']
            return n.strip()[:16]
        def xi_list(L):
            # أفضل 11 + أي مشجع متعادل تماماً مع رقم 11 (يطلع «متعادل»، والنادي ياخذ نفس النقاط أياً منهم انحسب)
            k = min(XI, len(L))
            while 0 < k < len(L) and ukey(L[k]) == ukey(L[XI - 1]):
                k += 1
            out, pos = [], 0
            for i, x in enumerate(L[:k]):
                if i == 0 or ukey(x) != ukey(L[i - 1]):
                    pos = i + 1
                tie = (i > 0 and ukey(x) == ukey(L[i - 1])) or (i + 1 < k and ukey(x) == ukey(L[i + 1]))
                out.append([nm_of(x), x['pts'], x['u'], pos, 1 if tie else 0])
            return out
        xi_out = {c: xi_list(byc[c]) for c in CLUBS if byc.get(c)}
        named = []
        for rk, x in full:
            if x['pts'] <= 0:
                continue
            nm = ((names.get(x['u']) or {}).get('n') or '') if names else x['nm']
            if nm.strip() and x['c'] in NAME and x['u'] not in hide:
                named.append([nm.strip()[:16], x['c'], x['pts'], rk, x['u']])
        top = [r for r in named if r[3] <= named[min(TOP, len(named)) - 1][3]] if named else []
        out[b] = {'clubs': clubs, 'fans': top[:TOP], 'more': max(0, len(top) - TOP), 'xi': xi_out}
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

    path, acc_path = os.path.join(ROOT, 'fans/data.json'), os.path.join(ROOT, 'fans/acc.json')
    empty_acc = lambda: {'v': 3, 'weeks': [], 'rds': [], 'users': {}, 'clubs': {}}
    prev_out, acc = {}, empty_acc()
    try:
        prev_out = json.load(open(path, encoding='utf8'))
    except Exception:
        pass
    try:
        acc = json.load(open(acc_path, encoding='utf8')) if not os.environ.get('FULL') else acc
    except Exception:
        pass
    if prev_out.get('v') != 3 or acc.get('v') != 3:      # أول تشغيل بالآلية الموحدة: نبدا من الصفر
        prev_out, acc = {}, empty_acc()
    kept = [w for w in prev_out.get('weeks', []) if w['w'] in acc['weeks']]
    first = max(acc['weeks'] or [0]) + 1
    counted = set(acc.get('rds', []))
    q = {'orderBy': '"$key"', 'startAt': '"' + str((first - 1) * WEEK + 1) + '"', 'endAt': '"' + str(max(first, cur) * WEEK) + '"'}
    p_all = (fb('p', q, H) or {}) if H and cur else {}
    if isinstance(p_all, list):
        p_all = {str(i): v for i, v in enumerate(p_all) if v}
    names = (fb('f', None, H) or {}) if H else {}
    names = {u[:12]: v for u, v in names.items() if isinstance(v, dict)}

    weeks = list(kept)
    live = {ch['id']: defaultdict(stat) for ch in CHALLENGES}           # الأسابيع اللي ما صارت نهائية (للموسم)
    live_clubs = {b: {} for b in BOARDS}
    week_ranks = {}
    for w in range(first, cur + 1):
        d0, d1 = (w - 1) * WEEK + 1, w * WEEK
        rds = sorted(r for r, wk in round_week.items() if wk == w and r not in counted)
        per = {'mano': collect_mano(p_all, d0, d1), 'pred': collect_pred(rds, pred_t, last_t)}
        bd, ranks = boards(per, names, hide)
        final = now >= final_at(w) and w < cur
        weeks.append({'w': w, 'from': dlabel(START + (d0 - 1) * DAYMS), 'to': dlabel(START + (d1 - 1) * DAYMS),
                      'live': w == cur, 'final': final, 'pred': bool(rds), 'rds': rds, 'boards': bd})
        target_u = acc['users'] if (final and H) else None
        for ch, users in per.items():
            for u, s in users.items():
                if target_u is not None:
                    add_stat(target_u.setdefault(ch, {}).setdefault(u, stat()), s)
                else:
                    add_stat(live[ch][u], s)
        for b in BOARDS:   # الموسم للأندية = مجموع نقاط التشكيلة في كل أسبوع
            for c, rk, pts, xi, n, mis, sec in bd[b]['clubs']:
                dst = acc['clubs'].setdefault(b, {}) if (final and H) else live_clubs[b]
                x = dst.setdefault(c, {'pts': 0, 'mis': 0, 'sec': 0, 'wk': 0})
                x['pts'] += pts; x['mis'] += mis; x['sec'] += sec; x['wk'] += 1 if pts else 0
        if final and H:
            acc['weeks'].append(w); acc['rds'] = sorted(set(acc['rds']) | set(rds))
        if w == cur:
            week_ranks = ranks
    # الموسم: المشجعين = مجموع نقاطهم · الأندية = مجموع نقاط تشكيلتهم كل أسبوع
    s_per = {}
    for ch in CHALLENGES:
        d = defaultdict(stat)
        for src in (acc['users'].get(ch['id'], {}), live[ch['id']]):
            for u, s in src.items():
                add_stat(d[u], s)
        s_per[ch['id']] = d
    season, s_ranks = boards(s_per, names, hide)
    for b in BOARDS:
        tot = {c: {'c': c, 'pts': 0, 'mis': 0, 'sec': 0, 'wk': 0} for c in CLUBS}
        for src in (acc['clubs'].get(b, {}), live_clubs[b]):
            for c, x in src.items():
                if c in tot:
                    for k in ('pts', 'mis', 'sec', 'wk'):
                        tot[c][k] += x[k]
        season[b]['clubs'] = [[x['c'], rk, x['pts'], x['wk'], 0, x['mis'], x['sec']] for rk, x in rank(list(tot.values()), ckey)]
        season[b].pop('xi', None)
    # القصة (لصورة الأسبوع): من آخر أسبوع نهائي
    story = ''
    done = [x for x in weeks if x.get('final')]
    if done:
        L = done[-1]
        # الموسم لين آخر أسبوع نهائي بس (بدون الأسبوع الشغال) عشان يطابق جدول الصورة
        fin = acc['clubs'].get('all', {}) if H else {}
        ranked = rank([{'c': c, **x} for c, x in fin.items()], ckey) if fin else []
        lead = [ranked[0][1]['c'], 1, ranked[0][1]['pts']] if ranked else ['', 0, 0]
        wl = L['boards']['all']['clubs'][0]
        if lead[2] > 0:
            story = f"جمهور {NAME[lead[0]]} يتصدر الموسم بـ{lead[2]:,} نقطة"
            if wl[0] != lead[0] and wl[2] > 0:
                story += f"، و{NAME[wl[0]]} أقوى تشكيلة في الأسبوع {L['w']} ({wl[2]:,})"
    out = {'v': 3, 'challenges': CHALLENGES, 'xi': XI, 'updated': datetime.fromtimestamp(now / 1000, UAE).strftime('%Y-%m-%d %H:%M'),
           'cur': cur, 'done': len(done), 'ends': START + cur * WEEK * DAYMS if cur else START,
           'weeks': weeks, 'season': season, 'story': story, 'names': bool(H)}
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
        json.dump({'w': cur, 'week': week_ranks, 'season': s_ranks}, open(os.path.join(ROOT, 'fans/ranks.json'), 'w', encoding='utf8'),
                  ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
