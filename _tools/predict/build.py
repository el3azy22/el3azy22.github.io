"""«دوري التوقعات»: يسحب مباريات الموسم من واجهة اتحاد الكرة، ويقرا توقعات الجماهير من Firebase
بعد صافرة كل مباراة (القواعد تفتح القراية مع الصافرة)، ويحسب النقاط والترتيبات.

التشغيل من جذر المستودع: python3 _tools/predict/build.py
يشتغل في GitHub Actions مع «قيّم اللاعبين» (نفس الحلقة كل 8 دقايق وقت المباريات + مرة الصبح).

الناتج:
  predict/data.json   المباريات كلها (الجولة، الموعد، الفريقين، الحالة، النتيجة) + رأي الجماهير بعد الصافرة
  predict/table.json  ترتيب كل جولة، وترتيب الموسم، وترتيب جماهير الأندية

القوانين (معتمدة 14 نوفمبر 2026):
  النتيجة بالضبط 5 · الفائز مع الفارق 3 (والتعادل الصح بنتيجة ثانية 3) · الفائز بس 2 · غير جذي 0
  ⭐ مضاعفة مباراة وحدة في كل جولة (لو انحطت على أكثر من وحدة، تنحسب أول وحدة بالموعد بس)
  التوقع ينحسب بس لو انكتب قبل الصافرة الرسمية (w = وقت السيرفر < موعد المباراة)
  ترتيب الموسم: اللي شارك في 3 جولات أو أكثر · ترتيب الأندية: المعدل لكل مشجع، وحد أدنى 10 مشجعين
  كسر التعادل: أكثر نتايج بالضبط، بعدها أقل عدد توقعات (الأدق)، بعدها الأقدم في التوقع
"""
import json, os, re, sys, time, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT_DIR = os.environ.get('OUT') or os.path.join(ROOT, 'predict')
API = 'https://www.uaefa.ae/api/'
COMP = os.environ.get('COMP', '2571')
DB = os.environ.get('FBDB', 'https://el3azy-3b64e-default-rtdb.europe-west1.firebasedatabase.app')
NS = os.environ.get('FBNS', '')  # للمحاكي: ?ns=...
UAE = timezone(timedelta(hours=4))
CLUB = {'4': 'nasr', '12': 'kalba', '8': 'wahda', '21': 'ajman', '31': 'dhafra', '3': 'sharjah', '2': 'wasl',
        '464': 'united', '11': 'khorfakkan', '6': 'shababahli', '20': 'hatta', '9': 'jazira', '5': 'baniyas', '1': 'ain'}
CLUBS = set(CLUB.values())
MIN_ROUNDS, MIN_FANS = 3, 10
FINISHED = 6
START = int(os.environ.get('START', '1794772800000'))  # 16 نوفمبر 2026 00:00 الإمارات: المباريات قبلها مب داخلة في اللعبة
CACHE = os.environ.get('CACHE') or os.path.join(ROOT, '_tools', 'predict', 'cache')   # توقعات المباريات المقفولة (ما تتغير بعد الصافرة)


def http_json(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 el3azy-predict'})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode('utf8'))
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(3 + 5 * k)


def kick_ms(t):  # "2026-11-08 4:55 م"
    m = re.match(r'(\d{4})-(\d\d)-(\d\d) (\d{1,2}):(\d\d)\s*([صم])?', t)
    y, mo, d, h, mi, ap = m.groups()
    h = int(h) % 12 + (12 if ap == 'م' else 0) if ap else int(h)
    return int(datetime(int(y), int(mo), int(d), h, int(mi), tzinfo=UAE).timestamp() * 1000)


def fixtures():
    comp = http_json(API + 'matches?lang=ar&competition_id=' + COMP)
    if comp.get('error'):
        raise RuntimeError(comp.get('msg'))
    out = []
    for g in comp['matches']:
        for it in g['items']:
            h, a = CLUB.get(it.get('club1_id')), CLUB.get(it.get('club2_ld') or it.get('club2_id'))
            if not h or not a:
                continue
            st = int(it.get('status_id') or 0)
            try:
                t = kick_ms(it['time'])
            except Exception:   # موعد غير محدد (تأجيل بدون موعد): المباراة ما تنعرض لين يتحدد موعدها
                print('::warning::موعد غير مفهوم', it.get('match_id'), it.get('time'))
                continue
            m = {'id': it['match_id'], 'wk': int(it['week_no']), 't': t, 'h': h, 'a': a, 'st': st}
            s1, s2 = it.get('team1_score'), it.get('team2_score')
            if st == FINISHED and str(s1).isdigit() and str(s2).isdigit():
                m['sh'], m['sa'] = int(s1), int(s2)
            out.append(m)
    out.sort(key=lambda m: (m['t'], m['id']))
    return out


def avg2(t, n):
    """المعدل لخانتين بتقريب نص لفوق، بحساب أعداد صحيحة (نفس الصفحات بالضبط: Math.floor((200t+n)/(2n))/100)"""
    return (200 * t + n) // (2 * n) / 100 if n else 0


def points(ph, pa, sh, sa):
    if ph == sh and pa == sa:
        return 5
    sg = lambda x: (x > 0) - (x < 0)
    if sg(ph - pa) != sg(sh - sa):
        return 0
    return 3 if ph - pa == sh - sa else 2


def valid_pick(p, m):
    try:
        return (isinstance(p, dict) and isinstance(p.get('h'), int) and isinstance(p.get('a'), int)
                and 0 <= p['h'] <= 20 and 0 <= p['a'] <= 20 and isinstance(p.get('w'), (int, float)) and p['w'] < m['t'])
    except Exception:
        return False


def read_picks(mid):
    d = http_json(f'{DB}/pr/{mid}.json{NS}')
    return d if isinstance(d, dict) else {}


def crowd(picks):
    n = len(picks)
    if not n:
        return None
    hw = sum(1 for p in picks if p['h'] > p['a']); dr = sum(1 for p in picks if p['h'] == p['a'])
    sc = defaultdict(int)
    for p in picks:
        sc[f"{p['h']}-{p['a']}"] += 1
    top = max(sc.items(), key=lambda kv: (kv[1], kv[0]))
    pct = lambda x: round(100 * x / n)
    return {'n': n, 'hw': pct(hw), 'd': pct(dr), 'aw': 100 - pct(hw) - pct(dr), 'top': top[0], 'topp': pct(top[1])}


def compute(ms, picks_by_match, now_ms):
    """picks_by_match: {mid: {uid: pick}} للمباريات اللي بدت. يرجع (crowd, table)."""
    crowd_out, rounds = {}, defaultdict(lambda: defaultdict(lambda: {'p': 0, 'e': 0, 'n': 0, 'w': 0, 'c': 'none', 'nm': '', 'ct': 0, 'ls': 0, 'pc': defaultdict(lambda: [0, 0])}))
    by_id = {m['id']: m for m in ms}
    # ⭐ المضاعفة: أول مباراة بالموعد عليها x في كل جولة لكل مشجع
    dbl = {}
    for m in ms:
        for u, p in picks_by_match.get(m['id'], {}).items():
            if p.get('x') is True and valid_pick(p, m) and (m['wk'], u) not in dbl:
                dbl[(m['wk'], u)] = m['id']
    for m in ms:
        raw = picks_by_match.get(m['id'])
        if raw is None:
            continue
        good = {u: p for u, p in raw.items() if valid_pick(p, m)}
        crowd_out[m['id']] = crowd(list(good.values()))
        for u, p in good.items():
            r = rounds[m['wk']][u]
            c = p.get('c') if p.get('c') in CLUBS else 'none'
            if p['w'] >= r['ct']:  # آخر نادي واسم كتبهم المشجع في هالجولة
                r['c'], r['nm'], r['ct'] = c, (p.get('n') or '')[:16], p['w']
            r['w'] = max(r['w'], p['w'])
            if m['st'] == FINISHED and 'sh' in m:
                pt = points(p['h'], p['a'], m['sh'], m['sa'])
                if dbl.get((m['wk'], u)) == m['id']:
                    pt *= 2
                r['p'] += pt; r['n'] += 1
                # نقاط كل توقع تنحسب لنادي المشجع وقت ما كتب هالتوقع
                r['pc'][c][0] += pt; r['pc'][c][1] += 1
                if pt:
                    r['ls'] = max(r['ls'], m['t'])   # موعد آخر مباراة جابت له نقاط (لفك تعادل نجوم الأسبوع)
                if pt and p['h'] == m['sh'] and p['a'] == m['sa']:
                    r['e'] += 1
    key = lambda kv: (-kv[1]['p'], -kv[1]['e'], kv[1]['w'])
    U = lambda u: u[:12]
    table = {'rounds': {}, 'season': [], 'clubs': {}, 'clubs_season': []}
    season = defaultdict(lambda: {'p': 0, 'e': 0, 'r': 0, 'c': 'none', 'nm': '', 'ct': 0, 'w': 0})
    club_season = defaultdict(lambda: {'s': 0.0, 'r': 0})
    for wk in sorted(rounds):
        rows = sorted(rounds[wk].items(), key=key)
        table['rounds'][str(wk)] = [[U(u), r['nm'], r['c'], r['p'], r['e'], r['n'], r['ls']] for u, r in rows]
        cl = defaultdict(list)
        for u, r in rows:
            for c, (pts, n) in r['pc'].items():
                if n and c != 'none':
                    cl[c].append(pts)
            s = season[u]
            s['p'] += r['p']; s['e'] += r['e']; s['r'] += 1 if r['n'] else 0; s['w'] = max(s['w'], r['w'])
            if r['ct'] >= s['ct']:
                s['c'], s['nm'], s['ct'] = r['c'], r['nm'], r['ct']
        crow = sorted(([c, avg2(sum(v), len(v)), len(v), sum(v)] for c, v in cl.items()), key=lambda x: (-(x[2] >= MIN_FANS), -x[1], -x[2]))
        table['clubs'][str(wk)] = crow
        for c, avg, n, _ in crow:
            if n >= MIN_FANS:
                club_season[c]['s'] += avg; club_season[c]['r'] += 1
    srows = sorted(((u, s) for u, s in season.items() if s['r'] >= MIN_ROUNDS), key=key)
    table['season'] = [[U(u), s['nm'], s['c'], s['p'], s['e'], s['r']] for u, s in srows]
    table['clubs_season'] = sorted(([c, round(v['s'], 2), v['r']] for c, v in club_season.items()), key=lambda x: (-x[1], -x[2]))
    table['min'] = {'rounds': MIN_ROUNDS, 'fans': MIN_FANS}
    return crowd_out, table


def main():
    now_ms = int(os.environ.get('NOW') or time.time() * 1000)  # NOW و FIX للاختبار بس
    ms = json.load(open(os.environ['FIX'], encoding='utf8')) if os.environ.get('FIX') else fixtures()
    ms = [m for m in ms if m['t'] >= START]
    os.makedirs(CACHE, exist_ok=True)
    picks = {}
    for m in ms:
        if now_ms < m['t'] + 60000:  # القراية تنفتح مع الصافرة
            continue
        cf = os.path.join(CACHE, m['id'] + '.json')
        # بعد الصافرة التوقعات ما تتغير، بس نعيد القراية أول 3 أيام احتياط (تأخير السيرفر/تعديل الموعد)
        if os.path.exists(cf) and now_ms > m['t'] + 3 * 86400000:
            picks[m['id']] = json.load(open(cf, encoding='utf8'))
            continue
        picks[m['id']] = read_picks(m['id'])  # لو فشلت القراية يوقف التشغيل كله، عشان ما ننشر ترتيب ناقص
        json.dump(picks[m['id']], open(cf, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    cr, table = compute(ms, picks, now_ms)
    for m in ms:
        if cr.get(m['id']):
            m['cr'] = cr[m['id']]
    os.makedirs(OUT_DIR, exist_ok=True)
    upd = datetime.now(UAE).strftime('%Y-%m-%d %H:%M')
    json.dump({'updated': upd, 'matches': ms}, open(os.path.join(OUT_DIR, 'data.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    table['updated'] = upd
    json.dump(table, open(os.path.join(OUT_DIR, 'table.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print('matches', len(ms), 'read', len(picks), 'rounds', len(table['rounds']))


if __name__ == '__main__':
    main()
