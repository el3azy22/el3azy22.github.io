"""جدول «تحدي الخبير» في «منو اللاعب؟» (schedule_pro في mano/data.json).
لاعب ثاني أصعب من لاعب اليوم: من اللاعبين اللي شاركوا 1–4 مباريات (لاعب اليوم 5 وفوق)، وله صورة وجنسية وعمر ورقم.
ما يتكرر مع جدول لاعب اليوم، وما يكون من نفس نادي لاعب اليوم في نفس اليوم ولا من نادي آخر 3 أيام في الخبير.
أول 4 أسابيع من اللي شاركوا 3–4 مباريات (أسهل شوي)، وبعدها الباقين.
تشغيله يعيد بناء الأيام الجاية بس (من باجر)، واليوم واللي قبله يظلون مثل ما هم."""
import json, os, random, sys
from datetime import datetime, timedelta, timezone
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F = os.path.join(R, 'mano', 'data.json')
md = json.load(open(F, encoding='utf8'))
P = {p['id']: p for p in md['players']}
E = md['schedule']
UAE = timezone(timedelta(hours=4))
start = datetime.fromisoformat(md['start']).replace(tzinfo=UAE)
today = (datetime.now(UAE) - start).days
keep = max(0, today + 1) if os.environ.get('FULL') != '1' else 0
old = md.get('schedule_pro', [])[:keep]
ok = lambda p: p.get('ph') and p.get('nat') and p.get('a') and p.get('no') and 1 <= p.get('ap', 0) <= 4 and p['id'] not in set(E)
pool = [p for p in md['players'] if ok(p) and p['id'] not in old]
rnd = random.Random(17)
rnd.shuffle(pool)
pool.sort(key=lambda p: 0 if p['ap'] >= 3 else 1)  # 3–4 مباريات أول
first, rest = [p for p in pool if p['ap'] >= 3][:28], None
rest = [p for p in pool if p not in first]
seq = first + rest
out = list(old)
while seq:
    d = len(out)
    easy_c = P[E[d % len(E)]]['c'] if E else None
    recent = [P[x]['c'] for x in out[-3:]]
    rp = [P[x]['p'] for x in out[-2:]]
    for i, p in enumerate(seq):
        if p['c'] != easy_c and p['c'] not in recent and not (len(rp) == 2 and rp[0] == rp[1] == p['p']):
            out.append(seq.pop(i)['id']); break
    else:
        out.append(seq.pop(0)['id'])
md['schedule_pro'] = out
json.dump(md, open(F, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
print(len(out), 'days · first 7:', [(P[x]['n'], P[x]['c'], P[x]['ap']) for x in out[:7]])
