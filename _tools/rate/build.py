"""«قيّم اللاعبين»: يسحب مباريات دوري أدنوك من واجهة اتحاد الكرة ويكتب rate/data.json.
التشغيل من جذر المستودع: python3 _tools/rate/build.py   (يشتغل في GitHub Actions كل 10 دقايق وقت المباريات)
لكل مباراة: الأساسيين، البدلاء اللي نزلوا (مع الدقيقة)، المدرب، الأهداف والكروت.
الأسماء المعروفة والصور من tashkila/squads.json (نفس النادي + نفس الرقم)، والناقص صورته من fanet.ae.
"""
import io, json, os, re, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

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
            g = sum(1 for x in e if x['type'] == 'goal' and x.get('player_id') == pid and x.get('goal_type') != '3')
            og = sum(1 for x in e if x['type'] == 'goal' and x.get('player_id') == pid and x.get('goal_type') == '3')
            cards = [x['type'][0] for x in e if x.get('player_id') == pid and x['type'] in ('ycard', 'rcard', 'y2card')]
            players.append({k: v for k, v in {
                'i': pid, 'n': fix_ya(re.sub(r'\s+', ' ', known).strip()), 'f': fix_ya(re.sub(r'\s+', ' ', pa['shortname_ar']).strip()),
                'no': int(pa['j_no']) if (pa.get('j_no') or '').isdigit() else None,
                'p': POS.get(pa.get('position'), 'M'), 'fp': pa.get('formation_pos', ''),
                's': 1 if starter else 0, 'in': sub_in, 'out': sub_out,
                'cap': 1 if pa.get('captain') == '1' else None,
                'g': g or None, 'og': og or None, 'cd': cards or None,
                'ph': photo(pid, m[5] if m and len(m) > 5 else ''),
            }.items() if v is not None})
    coach = next((o for o in tm.get('official') or [] if o.get('title_name_en') == 'Coach'), None)
    form = (a.get('formation') or '').split(':')[-1].strip()
    return {'c': slug, 'cid': a['id'], 'name': a['name_ar'], 'sc': int(a['score']) if (a.get('score') or '').isdigit() else None,
            'fm': form, 'coach': {'i': 'c' + coach['person_id'], 'n': fix_ya(coach['shortname_ar'].strip())} if coach else None,
            'pl': players}


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
            except Exception as e:
                print('report fail', mid, e, file=sys.stderr)
                if o:
                    m['h'], m['a'] = o['h'], o['a']
        elif o:
            m['h'], m['a'] = o['h'], o['a']
        if m['st'] == 6 and not m['h'].get('pl'):
            m['st'] = 5  # خلصت بس التشكيلة مب جاهزة: لا تفتح التقييم
        if it.get('team1_score', '') != '' and m['h'].get('sc') is None:
            m['h']['sc'], m['a']['sc'] = int(it['team1_score'] or 0), int(it['team2_score'] or 0)
        out.append(m)
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
