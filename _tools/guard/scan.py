"""رصد «الكشّاف» في «منو اللاعب؟» — مرحلة أولى: رصد بس، بدون عقوبة.

النمط: حساب يخسر اللعبة كاملة (ينكشف له الاسم)، وبعدها بوقت قصير حساب ثاني من نفس التلفون
(نفس البصمة dv) يفوز من أول محاولة أو ثاني محاولة.

المصدر: r/<اليوم>/<التحدي>/<uid> = {g, dv, t} (القراءة لحساب المدير بس).
التقرير يطلع هني في الطرفية بس — ما ينكتب في المستودع ولا في سجلات GitHub (المستودع عام).

تشغيل:  python3 _tools/guard/scan.py [من_يوم] [لين_يوم]
المفتاح: /home/claude/.el3azy/admin.json (برا المستودع)، أو TOKEN في البيئة.
"""
import json, os, sys, time, urllib.request, urllib.parse
from collections import defaultdict

DB = 'https://el3azy-3b64e-default-rtdb.europe-west1.firebasedatabase.app'
KEY = 'AIzaSyCJVYgLTqvj2k1KnvLYo6Z1feOS4E8fj94'      # مفتاح Firebase العام (نفس اللي في الصفحات)
P0 = 1794859200000
WIN = 60 * 60000            # الفوز لازم يكون خلال ساعة من الخسارة
MODES = {'easy': 'لاعب اليوم', 'pro': 'تحدي الخبير'}


def detect(r_all, window=WIN):
    """يرجع (cases, per_winner). cases: قائمة حالات؛ per_winner: uid → عدد الأيام المرصودة."""
    cases = []
    for d, v in sorted((r_all or {}).items(), key=lambda kv: int(kv[0])):
        if not v:
            continue
        for m in MODES:
            recs = [(u, x) for u, x in (v.get(m) or {}).items() if isinstance(x, dict) and x.get('dv') and x.get('t')]
            share = defaultdict(set)
            for u, x in recs:
                share[x['dv']].add(u)
            losses = [(u, x) for u, x in recs if x.get('g') == 0]
            wins = [(u, x) for u, x in recs if x.get('g') in (1, 2)]
            for wu, wx in wins:
                hits = [(lu, lx) for lu, lx in losses
                        if lu != wu and lx['dv'] == wx['dv'] and 0 < wx['t'] - lx['t'] <= window]
                if hits:
                    lu, lx = max(hits, key=lambda h: h[1]['t'])
                    cases.append({'d': int(d), 'm': m, 'win': wu, 'loss': lu, 'g': wx['g'],
                                  'gap': round((wx['t'] - lx['t']) / 60000, 1), 'dv': wx['dv'],
                                  'same_dv': len(share[wx['dv']])})
    per = defaultdict(set)
    for c in cases:
        per[c['win']].add(c['d'])
    return cases, {u: len(ds) for u, ds in per.items()}


def token():
    if os.environ.get('TOKEN'):
        return os.environ['TOKEN']
    a = json.load(open(os.environ.get('ADMIN_JSON', '/home/claude/.el3azy/admin.json')))
    body = urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': a['refresh']}).encode()
    with urllib.request.urlopen(f'https://securetoken.googleapis.com/v1/token?key={KEY}', body, timeout=30) as r:
        return json.loads(r.read())['id_token']


def get(path, t):
    with urllib.request.urlopen(f'{DB}/{path}.json?auth={t}', timeout=40) as r:
        return json.loads(r.read())


def main():
    today = (int(time.time() * 1000) - P0) // 86400000 + 1
    d0 = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, today - 6)
    d1 = int(sys.argv[2]) if len(sys.argv) > 2 else today
    t = token()
    r_all = {str(d): get(f'r/{d}', t) for d in range(d0, d1 + 1)}
    names = get('f', t) or {}
    n = sum(len((v or {}).get(m) or {}) for v in r_all.values() for m in MODES)
    cases, per = detect(r_all)
    print(f'الأيام {d0}–{d1} · ألعاب مسجّلة: {n} · حالات مطابقة للنمط: {len(cases)}')
    for c in cases:
        f = names.get(c['win']) or {}
        print(f"  يوم {c['d']} · {MODES[c['m']]} · فاز من محاولة {c['g']} بعد {c['gap']} دقيقة من خسارة بنفس البصمة"
              f" · الفايز: {f.get('n') or 'بدون اسم'} ({f.get('c') or '-'}) [{c['win'][:6]}…]"
              f" · حسابات بنفس البصمة اليوم: {c['same_dv']}")
    rep = sorted(((k, v) for k, v in per.items() if v >= 2), key=lambda kv: -kv[1])
    if rep:
        print('\nتكرر أكثر من يوم (أقوى دليل):')
        for u, k in rep:
            f = names.get(u) or {}
            print(f"  {f.get('n') or 'بدون اسم'} ({f.get('c') or '-'}) [{u[:6]}…] · {k} أيام")


if __name__ == '__main__':
    main()
