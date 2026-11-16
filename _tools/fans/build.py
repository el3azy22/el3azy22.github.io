"""«دوري الجماهير»: يجمع ترتيب جماهير الأندية من كل التحديات في جولات أسبوعية، ويطلع fans/data.json.

التشغيل من جذر المستودع: python3 _tools/fans/build.py   (في GitHub Actions مع rate-data، وفي fans-week)
القوانين (معتمدة 16 نوفمبر 2026):
  الجولة = أسبوع «منو اللاعب؟»: من الثلاثاء 00:00 لين نهاية الإثنين (توقيت الإمارات). الجولة 1 = 17–23 نوفمبر.
  كل تحدي يرتب الأندية بمعدل المشجع، والنادي اللي وصل الحد الأدنى ياخذ 15 − مركزه (الأول 14 … الـ14 = 1)، واللي ما وصل 0.
    🕵️ منو اللاعب؟: من c/<يوم> (نفس حساب صفحة التحدي): مجموع النقاط ÷ عدد لعبات لاعب اليوم، الحد 3.
    🔮 دوري التوقعات: من predict/table.json → clubs[الجولة]: المعدل لكل مشجع، الحد 10. الجولة تنحسب في أسبوع آخر مباراة فيها.
  جدول الموسم = مجموع الجولات المنتهية. التعادل: أكثر مرات مركز أول في التحديات، بعدها عدد المشجعين.
  نجوم الجولة: أعلى 3 مشجعين (نقاط منو اللاعب + نقاط التوقعات في الجولة)، بس اللي كاتبين أساميهم. fans/hide.json يخفي أي اسم.
  الأسماء الخاصة (f و p) تنقرا بمفتاح FIREBASE_SA بس. بدونه النجوم من دوري التوقعات بس.
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
MIN_MANO, MIN_PRED = 3, 10
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
                print('::warning::Firebase', path, e)
                return None
            time.sleep(3)


def day_of(ms):
    return (ms - START) // DAYMS + 1


def week_of_day(d):
    return (d - 1) // WEEK + 1


def dlabel(ms):
    t = datetime.fromtimestamp(ms / 1000, UAE)
    return f'{t.day} {MONTHS[t.month - 1]}'


def rank_points(rows, minimum):
    """rows: [(club, avg, n)] → {club: [points, avg, n]} (اللي ما وصل الحد 0)."""
    ok = sorted([r for r in rows if r[2] >= minimum], key=lambda r: (-r[1], -r[2], CLUBS.index(r[0])))
    out = {c: [0, 0, 0] for c in CLUBS}
    for c, avg, n in rows:
        out[c] = [0, round(avg, 2), n]
    for i, (c, avg, n) in enumerate(ok):
        out[c] = [15 - (i + 1), round(avg, 2), n]
    return out


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
    # جولات التوقعات → أسبوع آخر مباراة فيها
    last_t = defaultdict(int)
    for m in pred_d.get('matches', pred_d if isinstance(pred_d, list) else []):
        if m.get('t', 0) >= START:
            last_t[m['wk']] = max(last_t[m['wk']], m['t'])
    round_week = {str(r): week_of_day(day_of(t)) for r, t in last_t.items()}
    # الجولات المنتهية ما تتغير: ناخذها من الملف السابق، ونحسب من أول جولة ما خلصت (أخف على Firebase)
    path = os.path.join(ROOT, 'fans/data.json')
    prev_out = {}
    try:
        prev_out = json.load(open(path, encoding='utf8'))
    except Exception:
        pass
    kept = [w for w in prev_out.get('weeks', []) if not w.get('live') and w['w'] < cur and (w.get('stars') or not H) and all(len(x) > 3 for x in w.get('stars', []))] if not os.environ.get('FULL') else []
    kept = [w for i, w in enumerate(kept) if w['w'] == i + 1]
    first = len(kept) + 1
    q = lambda: {'orderBy': '"$key"', 'startAt': '"' + str((first - 1) * WEEK + 1) + '"', 'endAt': '"' + str(cur * WEEK) + '"'}
    c_all = fb('c', q()) if cur else {}
    if isinstance(c_all, list):
        c_all = {str(i): v for i, v in enumerate(c_all) if v}
    p_all = (fb('p', q(), H) or {}) if H and cur else {}
    fc = fb('fc') or {}
    if isinstance(p_all, list):
        p_all = {str(i): v for i, v in enumerate(p_all) if v}
    f_all = (fb('f', None, H) or {}) if H else {}
    weeks = list(kept)
    for w in range(first, cur + 1):
        d0, d1 = (w - 1) * WEEK + 1, w * WEEK
        # 🕵️ منو اللاعب؟
        T = {c: [0, 0] for c in CLUBS}
        for d, v in (c_all or {}).items():
            if not v or not (d0 <= int(d) <= d1):
                continue
            for m in ('easy', 'pro'):
                for c, x in (v.get(m) or {}).items():
                    if c in T and x:
                        if m == 'easy':
                            T[c][0] += x.get('n', 0)
                        T[c][1] += x.get('t', 0)
        mano = rank_points([(c, t / n if n else 0, n) for c, (n, t) in T.items()], MIN_MANO)
        # 🔮 دوري التوقعات
        rds = [r for r, wk in round_week.items() if wk == w]   # الأسبوع فيه جولة دوري حتى لو ما في توقعات محسوبة بعد
        pred = None
        if rds:
            rows = []
            for r in rds:
                rows += [(c, avg, n) for c, avg, n in pred_t.get('clubs', {}).get(r, []) if c in NAME]
            pred = rank_points(rows, MIN_PRED)
        rows = []
        for c in CLUBS:
            pts = mano[c][0] + (pred[c][0] if pred else 0)
            rows.append({'c': c, 'pts': pts, 'm': mano[c], 'p': pred[c] if pred else None})
        rows.sort(key=lambda r: (-r['pts'], -(r['m'][2] + (r['p'][2] if r['p'] else 0)), -(fc.get(r['c'], 0) or 0), CLUBS.index(r['c'])))
        # ⭐ النجوم
        ind = defaultdict(lambda: {'pts': 0, 'pro': 0, 'c': 'none', 'nm': ''})
        for d, v in (p_all or {}).items():
            if not v or not (d0 <= int(d) <= d1):
                continue
            for m in ('easy', 'pro'):
                for u, x in (v.get(m) or {}).items():
                    g = (x or {}).get('g') or 0
                    if g:
                        ind[u[:12]]['pts'] += 7 - g
                        if m == 'pro':
                            ind[u[:12]]['pro'] += 7 - g
                    ind[u[:12]]['c'] = (x or {}).get('c') or ind[u[:12]]['c']
        for u, x in (f_all or {}).items():
            if u[:12] in ind:
                ind[u[:12]]['nm'] = ((x or {}).get('n') or '')[:16]
                ind[u[:12]]['c'] = (x or {}).get('c') or ind[u[:12]]['c']
        for r in rds:
            for u, nm, c, p, e, n in pred_t.get('rounds', {}).get(r, []):
                s = ind[u]
                s['pts'] += p
                s['nm'] = s['nm'] or nm
                if s['c'] in ('none', None):
                    s['c'] = c
        # الترتيب: النقاط، وبعدها نقاط تحدي الخبير. إذا ظل التعادل يتشاركون نفس المركز
        cand = sorted([[s['nm'].strip(), s['c'], s['pts'], s['pro']] for u, s in ind.items()
                       if s['nm'].strip() and s['pts'] > 0 and u not in hide and s['c'] in NAME],
                      key=lambda x: (-x[2], -x[3], x[0]))
        stars, more, rk = [], 0, 0
        for i, x in enumerate(cand):
            if i == 0 or (x[2], x[3]) != (cand[i - 1][2], cand[i - 1][3]):
                rk = i + 1
            if rk > 3:
                break
            if len(stars) < 6:
                stars.append([x[0], x[1], x[2], rk, x[3]])
            else:
                more += 1
        weeks.append({'w': w, 'from': dlabel(START + (d0 - 1) * DAYMS), 'to': dlabel(START + (d1 - 1) * DAYMS),
                      'live': w == cur, 'pred': bool(pred), 'rows': rows, 'stars': stars, 'more': more,
                      'max': 14 * (1 + (1 if pred else 0))})
    # جدول الموسم بعد الجولات المنتهية
    done = [x for x in weeks if not x['live']]
    def standings(ws):
        tot = {c: {'c': c, 'tot': 0, 'firsts': 0, 'fans': fc.get(c, 0) or 0} for c in CLUBS}
        for x in ws:
            for r in x['rows']:
                tot[r['c']]['tot'] += r['pts']
                tot[r['c']]['firsts'] += (r['m'][0] == 14) + (1 if r['p'] and r['p'][0] == 14 else 0)
        return sorted(tot.values(), key=lambda t: (-t['tot'], -t['firsts'], -t['fans'], CLUBS.index(t['c'])))
    season, prev = [], {}
    if done:
        now_s = standings(done)
        if len(done) > 1:
            prev = {t['c']: i + 1 for i, t in enumerate(standings(done[:-1]))}
        lastw = {r['c']: r['pts'] for r in done[-1]['rows']}
        for i, t in enumerate(now_s):
            season.append({'c': t['c'], 'tot': t['tot'], 'wk': lastw[t['c']], 'rank': i + 1, 'prev': prev.get(t['c'], i + 1),
                           'firsts': t['firsts']})
    story = ''
    if done and season and season[0]['tot'] > 0:
        L = done[-1]
        top = max(L['rows'], key=lambda r: r['pts'])
        lead = season[0]
        if len(done) == 1:
            story = f"جمهور {NAME[lead['c']]} يفتتح دوري الجماهير في الصدارة بـ{lead['tot']} نقطة"
            if top['c'] != lead['c']:
                story += f"، و{NAME[top['c']]} أخذ أعلى نقاط في الأسبوع ({top['pts']})"
        else:
            ups = sorted(season, key=lambda s: -(s['prev'] - s['rank']))
            parts = []
            if ups and ups[0]['prev'] - ups[0]['rank'] >= 1:
                k = ups[0]['prev'] - ups[0]['rank']
                parts.append(f"{NAME[ups[0]['c']]} صعد {'مركز' if k == 1 else ('مركزين' if k == 2 else str(k) + ' مراكز')}")
            parts.append(f"{NAME[top['c']]} أخذ أعلى نقاط في الأسبوع ({top['pts']})" if top['c'] != (ups[0]['c'] if parts else None)
                         else f"وأخذ أعلى نقاط في الأسبوع ({top['pts']})")
            lead_prev = [c for c, r in prev.items() if r == 1]
            if lead_prev and lead_prev[0] != lead['c']:
                parts.append(f"و{NAME[lead['c']]} خطف الصدارة من {NAME[lead_prev[0]]}")
            else:
                parts.append(f"و{NAME[lead['c']]} محافظ على الصدارة")
            story = '، '.join(p for p in parts[:-1]).replace('، وأخذ', ' وأخذ') + '، ' + parts[-1]
    out = {'updated': datetime.fromtimestamp(now / 1000, UAE).strftime('%Y-%m-%d %H:%M'), 'cur': cur, 'done': len(done),
           'fc': {c: fc.get(c, 0) or 0 for c in CLUBS}, 'min': {'mano': MIN_MANO, 'pred': MIN_PRED},
           'ends': START + cur * WEEK * DAYMS if cur else START, 'weeks': weeks, 'season': season, 'story': story,
           'names': bool(H)}
    os.makedirs(os.path.join(ROOT, 'fans'), exist_ok=True)
    new = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    old = open(path, encoding='utf8').read() if os.path.exists(path) else ''
    strip = lambda s: s.split(',"weeks"', 1)[-1] if s else ''
    if strip(old) != strip(new):   # ما نكتب الملف لو تغير وقت التحديث بس
        open(path, 'w', encoding='utf8').write(new)
        print('fans/data.json ✓', 'الجولة', cur, 'منتهية', len(done))
    else:
        print('fans/data.json ما تغير')


if __name__ == '__main__':
    main()
