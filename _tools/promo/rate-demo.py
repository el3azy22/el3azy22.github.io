# بيانات عرض لفيديو «قيّم اللاعبين»: مباريات الجولة 8 الحقيقية (التشكيلات والتبديلات) بأوقات مزاحة،
# وأرقام جماهير تجريبية للنصر × يونايتد. ما نلمس Firebase الحقيقي.
#   python3 rate-demo.py   ← يكتب rate-demo.json (يستخدمه record.py مع TL=rate-timeline.json)
import json, os, random
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, '..', '..', 'rate', 'data.json'), encoding='utf-8'))
TL = json.load(open(os.path.join(HERE, 'rate-timeline.json'), encoding='utf-8'))
NOW = int(TL['demo']['nowMs'].split('/*')[0]) if TL['demo']['nowMs'].isdigit() else None
NOW = NOW or 1795113000000  # 2026-11-19 22:30 بتوقيت الإمارات
H = 3600000
plan = {'84529': (-2.5, 6), '84534': (-5, 6), '84532': (0.5, 2), '84530': (20, 2), '84531': (44, 2), '84533': (-60, 6), '84535': (-62, 6)}
ms = []
for m in D['matches']:
    if m['id'] not in plan:
        continue
    dh, st = plan[m['id']]
    m = json.loads(json.dumps(m))
    m['t'] = int(NOW + dh * H)
    m['st'] = st
    if st != 6:
        m['h'].pop('sc', None); m['a'].pop('sc', None)
        if dh > 2:
            m['h'] = {k: m['h'][k] for k in ('c', 'name')}; m['a'] = {k: m['a'][k] for k in ('c', 'name')}
    ms.append(m)
m = next(x for x in ms if x['id'] == '84529')
key = f"{m['id']}_{m['t']}"
random.seed(9)
avg = {'98552': 8.6, '104249': 7.9, '135017': 7.7, '98651': 7.3, '86725': 7.1, '16625': 6.9, '27741': 6.8, '78549': 6.6, '136043': 6.5, '104220': 6.4,
       '76406': 6.7, '134873': 6.2, '134878': 6.1, 'c98686': 7.4, '137662': 7.0, '104268': 4.9, '85765': 5.6, '41263': 5.4, 'c112393': 5.2}
ra = {}
for s in 'ha':
    for p in m[s]['pl'] + [m[s]['coach']]:
        a = avg.get(p['i'], round(random.uniform(5.0, 6.3), 1))
        n = random.randint(1150, 1360) if p.get('s', 1) else random.randint(380, 760)
        ra[p['i']] = {'n': n, 's': round(a * n)}
rs = {'98552': 571, '104249': 228, '135017': 196, '98651': 88, '137662': 61, '86725': 54}
out = {'key': key, 'data': {'updated': '', 'matches': sorted(ms, key=lambda x: x['t'])}, 'fb': {'ra': ra, 'rs': rs, 'rn': 1384}}
json.dump(out, open(os.path.join(HERE, 'rate-demo.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('ok', key)
