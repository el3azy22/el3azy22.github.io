"""«قيّم اللاعبين»: يسحب مباريات دوري أدنوك من واجهة اتحاد الكرة ويكتب rate/data.json.
التشغيل من جذر المستودع: python3 _tools/rate/build.py   (يشتغل في GitHub Actions كل 10 دقايق وقت المباريات)
لكل مباراة: الأساسيين، البدلاء اللي نزلوا (مع الدقيقة)، المدرب، الأهداف والكروت.
الأسماء المعروفة والصور من tashkila/squads.json (نفس النادي + نفس الرقم)، والناقص صورته من fanet.ae.
"""
import io, json, os, re, sys, time, urllib.request
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'khamsa'))   # صناعة الأهداف («خماسي الفانتازي»)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'rate', 'data.json')
PH_DIR = os.path.join(ROOT, 'rate', 'p')
API = 'https://www.uaefa.ae/api/'
COMP = os.environ.get('COMP', '2571')  # دوري أدنوك للمحترفين 2026/2027
UAE = timezone(timedelta(hours=4))
BACK, AHEAD = 7, 5  # أيام: نعرض المباريات اللي طافت (للنتائج) واللي ياية
CLUB = {'4': 'nasr', '12': 'kalba', '8': 'wahda', '21': 'ajman', '31': 'dhafra', '3': 'sharjah', '2': 'wasl',
        '464': 'united', '11': 'khorfakkan', '6': 'shababahli', '20': 'hatta', '9': 'jazira', '5': 'baniyas', '1': 'ain'}
SQ_ID = {'shababahli': 'shabab'}  # اسم النادي في squads.json لو يختلف
POS = {'GK': 'GK', 'D': 'D', 'M': 'M', 'A': 'F'}
OG = ('3', '4')   # نوع الهدف في أحداث المباراة: 1 عادي · 2 جزاء · 4 عكسي (تأكدنا من النتايج: 5-1 = 4 + عكسي) · 3 احتياط


def get(path, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(API + path, headers={'User-Agent': 'Mozilla/5.0 el3azy-rate'})
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.loads(r.read().decode('utf8'))
            if d.get('error'):
                raise RuntimeError(d.get('msg'))
            return d
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(3 + 5 * k)


def kick_ms(t):  # "2026-11-08 4:55 م"
    m = re.match(r'(\d{4})-(\d\d)-(\d\d) (\d{1,2}):(\d\d)\s*([صم])?', t)
    y, mo, d, h, mi, ap = m.groups()
    h = int(h) % 12 + (12 if ap == 'م' else 0) if ap else int(h)
    return int(datetime(int(y), int(mo), int(d), h, int(mi), tzinfo=UAE).timestamp() * 1000)


ALEF_MAQ = {'مصطفى', 'عيسى', 'موسى', 'يحيى', 'مرتضى', 'مجتبى', 'مرعى', 'هدى', 'منى', 'ليلى', 'المصطفى', 'مقتدى', 'الهدى', 'ضحى'}


def fix_ya(name):
    """موقع الاتحاد يكتب الياء الأخيرة ألف مقصورة (الزعابى) والعكس (مصطفي). نصلحها كلمة كلمة."""
    out = []
    for w in name.split():
        base = w[:-1]
        if w.endswith('ى') and w not in ALEF_MAQ:
            w = base + 'ي'
        elif w.endswith('ي') and base + 'ى' in ALEF_MAQ:
            w = base + 'ى'
        out.append(w)
    return ' '.join(out)


def norm(s):
    s = re.sub('[إأآ]', 'ا', s or '').replace('ة', 'ه').replace('ى', 'ي')
    return re.sub(r'\s+', ' ', s).strip()


def load_squads():
    sq = json.load(open(os.path.join(ROOT, 'tashkila', 'squads.json'), encoding='utf8'))
    out = {}
    for c in sq['clubs']:
        out[c['id']] = c['p']  # [رقم، الاسم، المركز، المجموعة، يدوي، صورة، الاسم المعروف]
    return out


def match_squad(sq, a):
    """نفس الرقم + كلمة مشتركة في الاسم، وإلا تطابق الاسم بس."""
    full = set(norm(a['name_ar']).split()) | set(norm(a['shortname_ar']).split())
    no = int(a['j_no']) if (a.get('j_no') or '').isdigit() else None
    best = None
    for p in sq:
        words = set(norm(p[1]).split())
        common = len(words & full)
        if p[0] == no and common:
            return p
        if common >= 2 and (best is None or common > best[0]):
            best = (common, p)
    return best[1] if best else None


def photo(pid, slug):
    if slug and not slug.startswith('nt/') and os.path.exists(os.path.join(ROOT, 'mano', 'assets', 'p', slug + '.webp')):
        return '../mano/assets/p/%s.webp' % slug
    f = os.path.join(PH_DIR, pid + '.webp')
    if not os.path.exists(f) and not os.path.exists(f + '.none'):
        try:
            from PIL import Image
            req = urllib.request.Request('https://www.fanet.ae/UAEFA/img.ashx?type=player&id=' + pid, headers={'User-Agent': 'Mozilla/5.0'})
            b = urllib.request.urlopen(req, timeout=30).read()
            os.makedirs(PH_DIR, exist_ok=True)
            if len(b) < 2000:
                open(f + '.none', 'w').close()
            else:
                im = Image.open(io.BytesIO(b)).convert('RGB')
                w, h = im.size
                s = min(w, h)
                im = im.crop(((w - s) // 2, 0, (w - s) // 2 + s, s)).resize((240, 240), Image.LANCZOS)
                im.save(f, 'WEBP', quality=80)
        except Exception as e:
            print('photo fail', pid, e, file=sys.stderr)
    return 'p/%s.webp' % pid if os.path.exists(f) else ''


def minute(x):
    if not x:
        return None
    t = int(x.get('time') or 0)
    return t


def team(tm, side, ev, sq):
    a = tm['attributes']
    slug = CLUB.get(a['id'], '')
    squad = sq.get(SQ_ID.get(slug, slug), [])
    players = []
    for grp, starter in (('active', True), ('substitute', False)):
        for p in (tm.get(grp) or {}).get('player') or []:
            pa = p['attributes']
            sub_in, sub_out = minute(p.get('subs_in')), minute(p.get('subs_out'))
            if not starter and sub_in is None:
                continue  # ما نزل
            m = match_squad(squad, pa)
            known = (m[6] if m and len(m) > 6 and m[6] else None) or pa['shortname_ar'].strip()
            pid = pa['player_id']
            e = [x for x in ev if x.get('club_dir') == side]
            g = sum(1 for x in e if x['type'] == 'goal' and x.get('player_id') == pid and x.get('goal_type') not in OG)
            og = sum(1 for x in e if x['type'] == 'goal' and x.get('player_id') == pid and x.get('goal_type') in OG)
            cards = [x['type'][0] for x in e if x.get('player_id') == pid and x['type'] in ('ycard', 'rcard', 'y2card')]
            # «خماسي الفانتازي»: الدقايق والكروت (الطرد بإنذار ثاني = طرد، وما ينحسب معه الإنذار الأول)
            yc = sum(1 for x in e if x.get('player_id') == pid and x['type'] == 'ycard')
            y2 = [int(x.get('time') or 0) for x in e if x.get('player_id') == pid and x['type'] == 'y2card']
            rd = [int(x.get('time') or 0) for x in e if x.get('player_id') == pid and x['type'] == 'rcard'] + y2
            yc = max(0, yc - len(y2))
            end = sub_out if sub_out is not None else (min(rd) if rd else 90)
            mn = max(0, max(end, 0) - (0 if starter else (sub_in or 0)))
            st0 = 0 if starter else (sub_in or 0)
            stop = sub_out if sub_out is not None else (min(rd) if rd else 999)
            gc = sum(1 for x in ev if x['type'] == 'goal' and ((x.get('club_dir') != side) != (x.get('goal_type') in OG))
                     and st0 <= goal_min(x)[0] < stop)      # الأهداف اللي دخلت على فريقه وهو في الملعب
            players.append({k: v for k, v in {
                'i': pid, 'n': fix_ya(re.sub(r'\s+', ' ', known).strip()), 'f': fix_ya(re.sub(r'\s+', ' ', pa['shortname_ar']).strip()),
                'no': int(pa['j_no']) if (pa.get('j_no') or '').isdigit() else None,
                'p': POS.get(pa.get('position'), 'M'), 'fp': pa.get('formation_pos', ''),
                's': 1 if starter else 0, 'in': sub_in, 'out': sub_out,
                'cap': 1 if pa.get('captain') == '1' else None,
                'g': g or None, 'og': og or None, 'cd': cards or None,
                'mn': mn, 'gc': gc or None, 'yc': yc or None, 'rc': len(rd) or None, 'en': (pa.get('name_en') or '').strip() or None,
                'ph': photo(pid, m[5] if m and len(m) > 5 else ''),
                'k': (m[5] or f'{m[0] if m[0] is not None else ""}|{m[1]}') if m else None,   # مفتاح اللاعب في tashkila/squads.json («توقّع تشكيلة ناديك»)
            }.items() if v is not None})
    coach = next((o for o in tm.get('official') or [] if o.get('title_name_en') == 'Coach'), None)
    form = (a.get('formation') or '').split(':')[-1].strip()
    pg = sum(1 for x in ev if x['type'] == 'goal' and x.get('club_dir') == side and x.get('goal_type') == '2')
    return {'pg': pg or None, 'c': slug, 'cid': a['id'], 'name': a['name_ar'], 'sc': int(a['score']) if (a.get('score') or '').isdigit() else None,
            'fm': form, 'coach': {'i': 'c' + coach['person_id'], 'n': fix_ya(coach['shortname_ar'].strip())} if coach else None,
            'pl': players}


LINEUPS = os.path.join(ROOT, 'tashkila', 'lineups.json')


STATS = os.path.join(ROOT, 'khamsa', 'stats.json')


def save_stats(matches, now_ms):
    """«خماسي الفانتازي»: إحصائيات كل لاعب في كل مباراة خلصت (ملف يتجمع طول الموسم، القوانين v3.4).
    {مباراة: {t, wk, h, a, sc: [أهداف الأرض، الضيف]، pg: [جزاءات انسجلت لكل فريق],
              ast: 1 انحسبت الصناعة · 0 ما لقيناها في 48 ساعة · ما في = ننتظر،  fm: نفسها للتصديات والجزاءات والتقييم،
              p: {مفتاح اللاعب: {s: H/A، m: دقايق، g: أهداف، a: صناعة، og: عكسي، y: إنذار، r: طرد، gc: أهداف دخلت وهو في الملعب،
                                  sv: تصديات، pw: جزاء كسبه وانسجل، pm: جزاء ضيّعه، ps: جزاء صدّه، b: نجم المباراة 3/2/1}}}}"""
    S = json.load(open(STATS, encoding='utf8')) if os.path.exists(STATS) else {}
    late = lambda m: now_ms > m['t'] + 48 * 3600000
    ch = False
    for m in matches:
        hp, ap = m['h'].get('pl'), m['a'].get('pl')
        if m['st'] != 6 or not hp or not ap:
            continue
        o = S.get(m['id']) or {}
        x = {'t': m['t'], 'wk': m['wk'], 'h': m['h']['c'], 'a': m['a']['c'], 'sc': [m['h'].get('sc'), m['a'].get('sc')],
             'pg': [m['h'].get('pg') or 0, m['a'].get('pg') or 0], 'p': {}}
        side_pl = {'H': hp, 'A': ap}
        for sd, pl in side_pl.items():
            for p in pl:
                if p.get('k'):
                    x['p'][p['k']] = {k: v for k, v in {'s': sd, 'm': p.get('mn') or 0, 'g': p.get('g'), 'og': p.get('og'), 'y': p.get('yc'),
                                                         'r': p.get('rc'), 'gc': p.get('gc')}.items() if v or k in ('s', 'm')}
        old = o.get('p') or {}
        # ── الصناعة (الرابطة) ──
        sig = ','.join(f"{k}:{v.get('g', 0)}" for k, v in sorted(x['p'].items()) if v.get('g'))     # لو تغيّرت الأهداف نرجع نسحبها
        if not sig and not any(v.get('og') for v in x['p'].values()):
            x['ast'] = 1                      # ما في أهداف: ما في صناعة
        elif 'ast' in o and o.get('gs') == sig:
            x['ast'] = o['ast']
            for k, v in old.items():
                if k in x['p'] and isinstance(v, dict) and v.get('a'):
                    x['p'][k]['a'] = v['a']
        else:
            r = None
            try:
                import assists as AS
                cand = lambda pl: [{'k': p.get('k'), 'en': p.get('en')} for p in pl]
                r = AS.assists(m['wk'], m['h']['c'], m['a']['c'], cand(hp), cand(ap))
            except Exception as e:
                print('assists fail', m['id'], e, file=sys.stderr)
            if r is not None:
                x['ast'] = 1
                for sd in ('H', 'A'):
                    for k, n in r[sd].items():
                        if k in x['p'] and x['p'][k]['s'] == sd:
                            x['p'][k]['a'] = n
                if r.get('miss'):
                    print('assists unmatched', m['id'], r['miss'], file=sys.stderr)
            elif late(m):
                x['ast'] = 0
        x['gs'] = sig
        # ── التصديات والجزاءات والتقييم (FotMob) ──
        FK = ('sv', 'pw', 'pm', 'ps', 'b')
        if 'fm' in o:
            x['fm'] = o['fm']
            for k, v in old.items():
                if k in x['p'] and isinstance(v, dict):
                    x['p'][k].update({f: v[f] for f in FK if v.get(f)})
        else:
            r = None
            try:
                import fotmob as FM
                r = FM.match_stats(m['h']['c'], m['a']['c'])
            except Exception as e:
                print('fotmob fail', m['id'], e, file=sys.stderr)
            if r is not None:
                x['fm'] = 1
                import assists as AS
                rts = []
                for sd, pl in side_pl.items():
                    for no, f in r[sd].items():
                        p = next((q for q in pl if str(q.get('no')) == no and q.get('k')), None)
                        if not p:      # الرقم مب مطابق: بالاسم
                            k = AS.match_player(f['name'], '', [{'k': q.get('k'), 'en': q.get('en')} for q in pl])
                            p = next((q for q in pl if q.get('k') == k), None) if k else None
                        if not p:
                            continue
                        d = x['p'][p['k']]
                        if f['sv']: d['sv'] = f['sv']
                        if f['pm']: d['pm'] = f['pm']
                        if f['ps']: d['ps'] = f['ps']
                        if f['pw']: d['pw'] = f['pw']
                        if f['rt']: rts.append((f['rt'], p['k']))
                # الجزاء اللي كسبه ينحسب صناعة لو انسجل (بعدد جزاءات فريقه اللي انسجلت)
                for sd, i in (('H', 0), ('A', 1)):
                    left = x['pg'][i]
                    for k, d in x['p'].items():
                        if d['s'] == sd and d.get('pw'):
                            n = min(d['pw'], left); left -= n
                            if n: d['pw'] = n
                            else: d.pop('pw')
                # نجم المباراة: أعلى 3 تقييمات (المتساوين ياخذون نفس النقاط)
                for rt, k in rts:
                    above = sum(1 for r2, _ in rts if r2 > rt)
                    if above < 3:
                        x['p'][k]['b'] = 3 - above
            elif late(m):
                x['fm'] = 0
        if o != x:
            S[m['id']] = x; ch = True
    if ch:
        os.makedirs(os.path.dirname(STATS), exist_ok=True)
        json.dump(S, open(STATS, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def goal_min(x):
    """«45+3» ⇒ (45, 3): وقت بدل الضايع في الشوط الأول ييي قبل الدقيقة 46"""
    a, _, b = str(x.get('fulltime') or x.get('time') or '0').partition('+')
    return (int(a) if a.isdigit() else 999, int(b) if b.isdigit() else 0)


def mark_first_goal(m, ev):
    """«منو بيسجل؟»: علامة fg=1 على صاحب أول هدف في المباراة (لأي فريق). لو أول هدف عكسي: محد ياخذها."""
    goals = sorted((x for x in ev if x.get('type') == 'goal'), key=goal_min)
    if not goals or goals[0].get('goal_type') in OG:
        return
    side = {'H': m['h'], 'A': m['a']}.get(goals[0].get('club_dir'))
    for p in (side or {}).get('pl') or []:
        if p.get('i') == goals[0].get('player_id'):
            p['fg'] = 1


def save_lineups(matches):
    """«توقّع تشكيلة ناديك»: التشكيلة الأساسية الرسمية لكل مباراة (مفاتيح tashkila/squads.json)، ملف يتجمع طول الموسم.
    {رقم المباراة: {t, wk, h: نادي، a: نادي، hs: [مفاتيح أساسيين]، as: [...]}}"""
    L = json.load(open(LINEUPS, encoding='utf8')) if os.path.exists(LINEUPS) else {}
    ch = False
    for m in matches:
        hp, ap = m['h'].get('pl'), m['a'].get('pl')
        if not hp or not ap:
            continue
        x = {'t': m['t'], 'wk': m['wk'], 'h': m['h']['c'], 'a': m['a']['c'],
             'hs': [p['k'] for p in hp if p.get('s') and p.get('k')], 'as': [p['k'] for p in ap if p.get('s') and p.get('k')],
             'hn': sum(1 for p in hp if p.get('s')), 'an': sum(1 for p in ap if p.get('s'))}
        # «منو بيسجل؟»: أهداف كل لاعب (أساسي أو بديل، بدون العكسية) + صاحب أول هدف + خلصت المباراة؟
        for sd, pl in (('hg', hp), ('ag', ap)):
            g = {p['k']: p['g'] for p in pl if p.get('g') and p.get('k')}
            if g:
                x[sd] = g
        fg = next((p['k'] for p in hp + ap if p.get('fg') and p.get('k')), None)
        if fg:
            x['fg'] = fg
        if m['st'] == 6:
            x['fin'] = 1
        if L.get(m['id']) != x:
            L[m['id']] = x; ch = True
    if ch:
        json.dump(L, open(LINEUPS, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))


def main():
    now = datetime.now(UAE)
    comp = get('matches?lang=ar&competition_id=' + COMP)
    items = [i for g in comp['matches'] for i in g['items']]
    lo, hi = (now - timedelta(days=BACK)).timestamp() * 1000, (now + timedelta(days=AHEAD)).timestamp() * 1000
    old = {}
    if os.path.exists(OUT):
        old = {m['id']: m for m in json.load(open(OUT, encoding='utf8')).get('matches', [])}
    sq = load_squads()
    out = []
    for it in sorted(items, key=lambda i: kick_ms(i['time'])):
        k = kick_ms(it['time'])
        if not (lo <= k <= hi):
            continue
        mid = it['match_id']
        m = {'id': mid, 'wk': int(it['week_no']), 't': k, 'st': int(it['status_id']),
             'h': {'c': CLUB.get(it['club1_id'], ''), 'name': it['club1']}, 'a': {'c': CLUB.get(it['club2_ld'], ''), 'name': it['club2']}}
        o = old.get(mid)
        # نسحب التشكيلة من ساعة قبل البداية، ونوقف التحديث بعد ما تخلص المباراة وتثبت البيانات بـ 3 ساعات
        need = now.timestamp() * 1000 >= k - 75 * 60000 and not (o and o.get('st') == 6 and o.get('h', {}).get('pl') and now.timestamp() * 1000 > k + 5 * 3600000)
        if o and o.get('h', {}).get('pl') and 'mn' not in o['h']['pl'][0]:
            need = True      # بيانات قديمة قبل «خماسي الفانتازي» (بدون الدقايق): نسحبها مرة وحدة
        if need:
            try:
                rep = get('match_report?match_id=' + mid)['match_report']
                ev = []
                try:
                    ev = get('match_highlights2?lang=ar&match_id=' + mid)['match_highlights2'].get('event') or []
                except Exception as e:
                    print('events fail', mid, e, file=sys.stderr)
                if rep.get('team1', {}).get('active'):
                    m['h'] = team(rep['team1'], 'H', ev, sq)
                    m['a'] = team(rep['team2'], 'A', ev, sq)
                    m['st'] = int(rep['attributes'].get('status_id') or m['st'])
                    mark_first_goal(m, ev)
            except Exception as e:
                print('report fail', mid, e, file=sys.stderr)
                if o:
                    m['h'], m['a'] = o['h'], o['a']
        elif o:
            m['h'], m['a'] = o['h'], o['a']
        if m['st'] != 6 and k <= now.timestamp() * 1000 < k + 12 * 3600000:   # «نهاية الشوط الثاني» = خلصت (قرار إبراهيم 19 نوفمبر)
            try:
                u = get('matches_updates_match?lang=ar&match_id=' + mid).get('matches_updates_match') or {}
                if str(u.get('live') or '0') != '1' and re.search(r'(?:إ|ا)نتهت|نهاية الشوط الثاني', u.get('statustext') or ''):
                    m['st'] = 6
            except Exception as e:
                print('status fail', mid, e, file=sys.stderr)
        if o and o.get('st') == 6 and m['st'] != 6 and m['h'].get('pl'):
            m['st'] = 6      # خلصت قبل: ما نرجعها (التقرير أحياناً يرجع حالة 5 بعد ما خلصت)
        if m['st'] == 6 and not m['h'].get('pl'):
            m['st'] = 5  # خلصت بس التشكيلة مب جاهزة: لا تفتح التقييم
        if it.get('team1_score', '') != '' and m['h'].get('sc') is None:
            m['h']['sc'], m['a']['sc'] = int(it['team1_score'] or 0), int(it['team2_score'] or 0)
        out.append(m)
    save_lineups(out)
    save_stats(out, now.timestamp() * 1000)
    # توحيد إملاء الأسماء (_tools/name_fixes.json) حتى في المباريات القديمة، نفس «منو اللاعب؟» و«تشكيلتي»
    NF = json.load(open(os.path.join(ROOT, '_tools', 'name_fixes.json'), encoding='utf8'))
    def fixw(s):
        if not isinstance(s, str):
            return s
        for a, b in NF.get('phrases', {}).items():
            s = s.replace(a, b)
        return ' '.join(NF['words'].get(w, w) for w in s.split(' '))
    for m in out:
        for side in ('h', 'a'):
            for pl in (m.get(side) or {}).get('pl') or []:
                for k in ('n', 'f'):
                    if k in pl:
                        pl[k] = fixw(pl[k])
    data = {'updated': now.strftime('%Y-%m-%d %H:%M'), 'matches': out}
    # ما نكتب الملف لو ما تغيّر شي غير وقت التحديث (عشان ما تنعمل commits فاضية)
    if os.path.exists(OUT):
        prev = json.load(open(OUT, encoding='utf8'))
        if prev.get('matches') == out:
            print('no change')
            return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print('wrote', len(out), 'matches')


if __name__ == '__main__':
    main()
