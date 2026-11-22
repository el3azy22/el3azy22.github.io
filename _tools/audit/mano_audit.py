"""مراجعة نقاط «منو اللاعب؟»: يقارن سجل نهاية اللعبة (r/) بالنتيجة اللي تنحسب منها النقاط (p/).
يطبع أعداد مجمّعة بس (بدون أي معرّف أو اسم)، عشان سجلات GitHub عامة."""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'fans'))
import build as B
from collections import Counter
START = 1794859200000; DAY = 86400000
H = B.hdrs()
last = (int(time.time() * 1000) - START) // DAY + 1
P, R = {}, {}
for d in range(1, last + 1):
    for m in ('easy', 'pro'):
        P[d, m] = B.fb(f'p/{d}/{m}', h=H) or {}
        R[d, m] = B.fb(f'r/{d}/{m}', h=H) or {}
first = {}
for (d, m), p in P.items():
    for u, x in p.items():
        t = (x or {}).get('t') or START + (d - 1) * DAY
        first[u] = min(first.get(u, 9e15), t)
c = Counter()
for (d, m), r in R.items():
    for u, x in r.items():
        if u in P[d, m]:
            if ((P[d, m][u] or {}).get('g') or 0) != ((x or {}).get('g') or 0): c['g_mismatch'] += 1
            continue
        g = (x or {}).get('g') or 0
        if m == 'pro' and u not in P[d, 'easy']:
            k = 'pro_no_easy'
        elif u not in first:
            k = 'never_any_p'          # ما اختار نادي أبداً (أو ما سجّل)
        elif first[u] > ((x or {}).get('t') or 0):
            k = 'before_first_p'       # لعب قبل لا يختار ناديه
        else:
            k = 'AFTER_first_p'        # كان مسجل قبل: هذا لو موجود = خلل
        c[k] += 1
        if g: c[k + '_win'] += 1; c[k + '_pts'] += 7 - g
print(' · '.join(f'{k}={v}' for k, v in sorted(c.items())))
