"""«خماسي الفانتازي» (قرار إبراهيم 20 نوفمبر، جدول النقاط على طريقة فانتازي الدوري الإنجليزي):
التصديات وركلات الجزاء (كسبها، ضيّعها، صدّها) وتقييم اللاعب في المباراة (لنجم المباراة) من FotMob.
لو FotMob ما رد أو المباراة مب موجودة: الحساب يكمل بالنقاط الأساسية (الأهداف والدقايق والكروت الرسمية). ما نذكر أي مصدر في الصفحات.

match_stats(h, a) → {'H': {رقم القميص: {...}}, 'A': {...}} أو None.
"""
import json, urllib.request

LEAGUE = 538      # دوري أدنوك للمحترفين في FotMob
TEAM = {'102101': 'jazira', '102111': 'wasl', '102113': 'hatta', '102117': 'ain', '102118': 'dhafra', '102119': 'shababahli',
        '102122': 'wahda', '102123': 'nasr', '102124': 'sharjah', '149993': 'khorfakkan', '149994': 'ajman', '1552577': 'united',
        '182933': 'baniyas', '209190': 'kalba'}
_ids = None


def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 el3azy'}), timeout=40) as r:
        return json.loads(r.read().decode('utf8'))


def match_id(h, a):
    global _ids
    if _ids is None:
        d = get(f'https://www.fotmob.com/api/data/leagues?id={LEAGUE}')
        _ids = {}
        for m in (d.get('fixtures') or {}).get('allMatches') or []:
            _ids[(TEAM.get(str(m['home']['id'])), TEAM.get(str(m['away']['id'])))] = (m['id'], bool((m.get('status') or {}).get('finished')))
    return _ids.get((h, a))


def _val(p, name):
    for st in p.get('stats') or []:
        v = (st.get('stats') or {}).get(name)
        if v is not None:
            return (v.get('stat') or {}).get('value') or 0
    return 0


def match_stats(h, a):
    mid = match_id(h, a)
    if not mid or not mid[1]:
        return None
    d = get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid[0]}')
    teams = (d.get('header') or {}).get('teams') or []
    ps = (d.get('content') or {}).get('playerStats') or {}
    if len(teams) < 2 or not ps:
        return None
    home = str(teams[0]['id'])
    out = {'H': {}, 'A': {}}
    for p in ps.values():
        side = 'H' if str(p.get('teamId')) == home else 'A'
        out[side][str(p.get('shirtNumber'))] = {
            'name': p.get('name') or '',
            'sv': int(_val(p, 'Saves') or 0), 'pw': int(_val(p, 'Penalties won') or 0), 'pm': int(_val(p, 'Missed penalty') or 0),
            'ps': int(_val(p, 'Saved penalties') or 0), 'rt': float(_val(p, 'FotMob rating') or 0)}
    return out
