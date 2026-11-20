"""صناعة الأهداف لـ«خماسي الفانتازي» (قرار إبراهيم 20 نوفمبر).
بيانات الاتحاد ما فيها صانع الهدف، فناخذه من صفحة المباراة في موقع رابطة المحترفين (بيانات Opta الرسمية).
قارنّاها بـ FotMob في الجولات 1-9: نفس الصانع في 133 من 135 هدف. ما نذكر أي مصدر في الصفحات.

assists(wk, h, a, players_h, players_a) → {'H': {key: عدد}, 'A': {...}} أو None لو الصفحة مب جاهزة.
players_* = لاعبين الفريق اللي لعبوا: [{'k': مفتاحنا، 'f': الاسم الكامل بالعربي، 'en': الاسم الإنجليزي}].
"""
import json, re, unicodedata, urllib.request

SEASON_COMP = 'b8785e20-745f-11f1-82d0-f556dfffd44c'   # دوري أدنوك 2026/2027 في موقع الرابطة
BASE = 'https://www.uaepl.ae/en/'
SLUG = {'ajman': 'ajman', 'al-ain': 'ain', 'al-dhafra': 'dhafra', 'al-jazira': 'jazira', 'al-nasr': 'nasr', 'al-wahda': 'wahda',
        'al-wasl': 'wasl', 'bani-yas': 'baniyas', 'hatta': 'hatta', 'kalba': 'kalba', 'khorfakkan': 'khorfakkan',
        'shabab-alahli': 'shababahli', 'sharjah': 'sharjah', 'united': 'united'}
_week = {}


def get(u, xhr=False):
    h = {'User-Agent': 'Mozilla/5.0 el3azy'}
    if xhr:
        h['X-Requested-With'] = 'XMLHttpRequest'
    with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=40) as r:
        return r.read().decode('utf8')


def fixture_url(wk, h, a):
    if wk not in _week:
        d = json.loads(get(f'{BASE}fixtures/matches?seasonCompetitionId={SEASON_COMP}&weekNumber={wk}&teamId=', True))
        out, cl = {}, []
        for c, f in re.findall(r'clubs/([a-z-]+)"|fixtures/([0-9a-f-]{36})', d.get('html', '')):
            if c:
                cl.append(SLUG.get(c, c))
            elif f and len(cl) >= 2:
                out[(cl[-2], cl[-1])] = BASE + 'fixtures/' + f
                cl = []
        _week[wk] = out
    return _week[wk].get((h, a))


def find_url(wk, h, a):
    """المباراة في جولتها، ولو انتقلت (تأجيل أو ترقيم ثاني) ندوّرها في الجولات الثانية"""
    u = fixture_url(wk, h, a)
    for w in [x for x in range(1, 27) if x != wk] if not u else []:
        try:
            u = fixture_url(w, h, a)
        except Exception:
            u = None
        if u:
            break
    return u


def _arr(s, key):
    i = s.find(f'"{key}":[')
    if i < 0:
        return None
    j = i + len(key) + 3; dep = 0
    for k in range(j, len(s)):
        if s[k] == '[':
            dep += 1
        elif s[k] == ']':
            dep -= 1
            if dep == 0:
                return json.loads(s[j:k + 1])
    return None


def _obj(s, var):
    m = re.search(r'var ' + var + r'\s*=\s*(\{.*?\});', s, re.S)
    try:
        return json.loads(m.group(1)) if m else {}
    except Exception:
        return {}


def toks(x):
    x = str(x or '').translate(str.maketrans({'ø': 'o', 'Ø': 'O', 'æ': 'ae', 'Æ': 'AE', 'ß': 'ss', 'ð': 'd', 'þ': 'th', 'ł': 'l', 'đ': 'd'}))
    x = unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode().lower()
    return {t for t in re.split(r'[^a-z]+', x) if len(t) >= 3 and t not in ('al', 'bin', 'ben', 'abdulla', 'abdullah', 'mohamed', 'mohammed', 'ahmed', 'ali')}


def match_player(name, slug, cands):
    """أحسن لاعب من اللي لعبوا بنفس الفريق (بالإنجليزي ومفتاحنا). لو في تعادل أو ما في تطابق: None (ما نخمّن)."""
    q = toks(name) | toks(slug.replace('-', ' ') if slug else '')
    if not q:
        return None
    sc = sorted(((len(q & (toks(p.get('en')) | toks((p.get('k') or '').replace('-', ' ')))), p['k']) for p in cands if p.get('k')), reverse=True)
    if not sc or sc[0][0] == 0 or (len(sc) > 1 and sc[1][0] == sc[0][0]):
        return None
    return sc[0][1]


def assists(wk, h, a, players_h, players_a):
    u = find_url(wk, h, a)
    if not u:
        return None
    s = get(u)
    goals = _arr(s, 'goal')
    cont = _arr(s, 'contestant') or []
    if goals is None or not cont:
        return None
    home = next((c['id'] for c in cont if c.get('position') == 'home'), None)
    pd = {**_obj(s, 'homeTeamPlayerData'), **_obj(s, 'awayTeamPlayerData')}
    out = {'H': {}, 'A': {}}
    for g in goals:
        if g.get('type') != 'G' or not g.get('assistPlayerId'):     # الجزاء: الصناعة لكاسبها لو انسجلت (من fotmob.py)
            continue
        side = 'H' if g.get('contestantId') == home else 'A'
        info = pd.get(g['assistPlayerId']) or {}
        k = match_player(info.get('name') or g.get('assistPlayerName'), info.get('slug'), players_h if side == 'H' else players_a)
        if k:
            out[side][k] = out[side].get(k, 0) + 1
        else:
            out.setdefault('miss', []).append(g.get('assistPlayerName'))
    return out
