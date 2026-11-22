"""مراجعة نقاط «منو اللاعب؟»: يقارن سجل نهاية اللعبة (r/) بالنتيجة اللي تنحسب منها النقاط (p/).
يطبع أعداد مجمّعة بس (بدون أي معرّف أو اسم)، عشان سجلات GitHub عامة."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'fans'))
import build as B
from collections import Counter
START = 1794859200000; DAY = 86400000
tot = Counter()
H = B.hdrs()
last = (int(__import__('time').time() * 1000) - START) // DAY + 1
for d in range(1, last + 1):
    for m in ('easy', 'pro'):
        p = B.fb(f'p/{d}/{m}', h=H) or {}
        r = B.fb(f'r/{d}/{m}', h=H) or {}
        c = Counter()
        c['p'] = len(p); c['r'] = len(r)
        for u, x in r.items():
            x = x or {}
            if u not in p:
                c['r_no_p'] += 1
                if (x.get('g') or 0) > 0: c['r_no_p_win'] += 1; c['lost_pts_max'] += 7 - x['g']
                late = (x.get('t') or 0) >= START + d * DAY + 15 * 60000
                if late: c['r_no_p_late'] += 1
            else:
                pg = (p[u] or {}).get('g') or 0; rg = x.get('g') or 0
                if pg != rg: c['g_mismatch'] += 1
                if not (p[u] or {}).get('c'): c['p_no_club'] += 1
        for u in p:
            if u not in r: c['p_no_r'] += 1
        tot.update(c)
        print(f'يوم {d} {m}: ' + ' · '.join(f'{k}={v}' for k, v in sorted(c.items())))
print('المجموع: ' + ' · '.join(f'{k}={v}' for k, v in sorted(tot.items())))
