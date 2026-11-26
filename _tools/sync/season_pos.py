"""مركز اللاعب هالموسم (قرار إبراهيم 27 نوفمبر): من تشكيلات البداية في مباريات دوري أدنوك المنتهية.
لكل لاعب: كم مرة بدا في كل خط (GK/DF/MD/FW) وفي كل دور تفصيلي (ظهير أيمن، جناح أيسر...).
المخرج: _tools/sync/season_pos.json {pid: {"n": عدد مرات البداية, "cat": {...}, "role": {...}}}
الكاش: _tools/sync/season_lineups.json (تشكيلات المباريات اللي خلصت ما تتغير، فما نعيد تحميلها).
الجناح = هجوم (قرار إبراهيم).
"""
import json, os, sys, difflib, unicodedata, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'khamsa'))
from fotmob import get, TEAM, LEAGUE

R = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = f'{R}/_tools/sync/season_lineups.json'
OUT = f'{R}/_tools/sync/season_pos.json'


def role(pid):
    """positionId من FotMob: العشرات = الخط، الآحاد = الجهة (2 يمين، 8 يسار)."""
    if pid is None:
        return None
    if pid == 11:
        return 'GK', 'gk'
    row, side = pid // 10, pid % 10
    s = 'r' if side <= 3 else ('l' if side >= 7 else 'c')
    if row <= 4:
        return 'DF', {'r': 'rb', 'l': 'lb', 'c': 'cb'}[s]
    if row == 5:
        return ('DF', 'rwb' if s == 'r' else 'lwb') if s != 'c' else ('MD', 'dm')
    if row == 6:
        return 'MD', 'dm' if s == 'c' else ('rm' if s == 'r' else 'lm')
    if row == 7:
        return ('MD', 'cm') if s == 'c' else ('FW', 'rw' if s == 'r' else 'lw')
    if row == 8:
        return ('MD', 'am') if s == 'c' else ('FW', 'rw' if s == 'r' else 'lw')
    return ('FW', 'st') if s == 'c' else ('FW', 'rw' if s == 'r' else 'lw')


def nrm(s):
    s = unicodedata.normalize('NFD', s or '').lower()
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z ]', ' ', s).split()


def sim(a, b):
    ta, tb = nrm(a), nrm(b)
    if not ta or not tb:
        return 0
    return max(difflib.SequenceMatcher(None, x, y).ratio() for x in ta for y in tb if len(x) > 2 and len(y) > 2) if any(len(x) > 2 for x in ta) and any(len(y) > 2 for y in tb) else 0


def lineups():
    cache = json.load(open(CACHE, encoding='utf8')) if os.path.exists(CACHE) else {}
    d = get(f'https://www.fotmob.com/api/data/leagues?id={LEAGUE}')
    for m in (d.get('fixtures') or {}).get('allMatches') or []:
        if not (m.get('status') or {}).get('finished') or str(m['id']) in cache:
            continue
        try:
            md = get(f'https://www.fotmob.com/api/data/matchDetails?matchId={m["id"]}')
            lu = (md.get('content') or {}).get('lineup') or {}
            rows = []
            for side in ('homeTeam', 'awayTeam'):
                t = lu.get(side) or {}
                club = TEAM.get(str(t.get('id')))
                for p in t.get('starters') or []:
                    rows.append([club, p.get('shirtNumber'), p.get('name'), p.get('id'), p.get('positionId')])
            if len(rows) >= 20:
                cache[str(m['id'])] = rows
        except Exception as e:
            print('skip', m['id'], e)
    json.dump(cache, open(CACHE, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    return cache


def main():
    data = json.load(open(f'{R}/mano/data.json', encoding='utf8'))
    alias = json.load(open(f'{R}/mano/aliases.json', encoding='utf8')) if os.path.exists(f'{R}/mano/aliases.json') else {}
    by_club = {}
    for p in data['players']:
        by_club.setdefault(p['c'], []).append(p)

    def names(p):
        out = [p.get('e') or '']
        a = alias.get(p['id'])
        if isinstance(a, list):
            out += [x for x in a if re.search('[A-Za-z]', x)]
        elif isinstance(a, str) and re.search('[A-Za-z]', a):
            out.append(a)
        return out

    def match(club, no, name):
        ps = by_club.get(club) or []
        best = max(ps, key=lambda p: max(sim(name, x) for x in names(p)), default=None)
        bs = max((sim(name, x) for x in names(best)), default=0) if best else 0
        same_no = [p for p in ps if no is not None and str(p.get('no')) == str(no)]
        if same_no and max(sim(name, x) for x in names(same_no[0])) >= 0.6:
            return same_no[0]
        return best if bs >= 0.85 else None

    out, miss = {}, 0
    for mid, rows in lineups().items():
        for club, no, name, fmid, pos in rows:
            r = role(pos)
            p = match(club, no, name) if club and r else None
            if not p:
                miss += 1
                continue
            o = out.setdefault(p['id'], {'n': 0, 'cat': {}, 'role': {}})
            o['n'] += 1
            o['cat'][r[0]] = o['cat'].get(r[0], 0) + 1
            o['role'][r[1]] = o['role'].get(r[1], 0) + 1
    print('players', len(out), 'unmatched starts', miss)
    if len(out) < 150:
        print('too few, keep old file')
        return
    json.dump(out, open(OUT, 'w', encoding='utf8'), ensure_ascii=False, indent=0, sort_keys=True)


if __name__ == '__main__':
    main()
