"""اختبار «دوري الجماهير» كامل (build.py) على المحاكي، بنسخة معزولة من المستودع:
مهلة نهاية الأسبوع، الأسبوع النهائي ما يتغير، فشل القراءة ما يكتب أصفار، جولة ما تنحسب مرتين، أسبوع فيه جولتين.
  python3 _tools/tests/test_fans_build.py   (يحتاج المحاكي على 9000)"""
import json, os, shutil, subprocess, sys, tempfile
import requests
sys.path.insert(0, os.path.dirname(__file__))
import test_rules as T

S, DAY, MIN = 1794859200000, 86400000, 60000
W1_END = S + 7 * DAY


def tree(pred_matches, pred_table, data=None):
    d = tempfile.mkdtemp()
    for x in ('_tools/fans', 'fans', 'predict'):
        os.makedirs(os.path.join(d, x))
    shutil.copy(os.path.join(T.ROOT, '_tools/fans/build.py'), os.path.join(d, '_tools/fans'))
    json.dump({'matches': pred_matches}, open(os.path.join(d, 'predict/data.json'), 'w'))
    json.dump(pred_table, open(os.path.join(d, 'predict/table.json'), 'w'))
    if data:
        json.dump(data, open(os.path.join(d, 'fans/data.json'), 'w'))
    return d


def run(d, now, db=None):
    env = {**os.environ, 'NOW': str(now), 'FBDB': db or T.B, 'FBNS': T.NS, 'TOKEN': 'owner'}
    r = subprocess.run([sys.executable, os.path.join(d, '_tools/fans/build.py')], env=env, capture_output=True, text=True)
    data = json.load(open(os.path.join(d, 'fans/data.json'))) if os.path.exists(os.path.join(d, 'fans/data.json')) else None
    return r.returncode, data


def club_c(day, club, n, t):
    requests.put(T.url(f'c/{day}/easy/{club}'), data=json.dumps({'n': n, 't': t}), headers=T.OWNER)


def wk(data, w):
    return next(x for x in data['weeks'] if x['w'] == w)


def pts(data, w):
    return {r['c']: r['pts'] for r in wk(data, w)['rows'] if r['pts']}


if __name__ == '__main__':
    T.load_rules(S, []); T.reset({'fc': {'ain': 5, 'wasl': 5}})
    print('— دوري الجماهير (build.py) —')
    club_c(7, 'ain', 3, 12); club_c(7, 'wasl', 3, 11)
    d = tree([], {'rounds': {}, 'clubs': {}})
    rc, data = run(d, W1_END + 5 * MIN)          # 00:05 الثلاثاء
    T.check('00:05: الأسبوع 1 مب نهائي بعد، العين 14 والوصل 13', (rc, pts(data, 1)), (0, {'ain': 14, 'wasl': 13}))
    club_c(7, 'wasl', 4, 17)                     # نتيجة وصلت في المهلة (00:10): الوصل 4.25 > العين 4.00
    rc, data = run(d, W1_END + 13 * MIN)
    T.check('00:13: نتيجة المهلة تنحسب (الوصل يتقدم)', pts(data, 1), {'wasl': 14, 'ain': 13})
    rc, data = run(d, W1_END + 41 * MIN)
    club_c(7, 'ain', 30, 300)                    # تغيير بعد ما صار نهائي (ما يفترض يصير)
    rc, data = run(d, W1_END + 60 * MIN)
    T.check('بعد 00:40: الأسبوع 1 نهائي وما يتغير', pts(data, 1), {'wasl': 14, 'ain': 13})
    # فشل القراءة: ما يكتب شي
    d2 = tree([], {'rounds': {}, 'clubs': {}})
    rc, data = run(d2, W1_END + 5 * MIN, db='http://localhost:9')
    T.check('فشل قراءة Firebase: التشغيل يفشل وما ينكتب ملف', (rc != 0, data), (True, None))
    # جولة تغير موعدها بعد ما انحسبت: ما تنحسب مرة ثانية
    T.reset({'fc': {}})
    m = lambda i, r, t: {'id': i, 'wk': r, 't': t, 'h': 'ain', 'a': 'wasl', 'st': 6}
    tb = {'rounds': {}, 'clubs': {'9': [['ain', 5.0, 10, 50], ['wasl', 3.0, 10, 30]]}}
    d3 = tree([m('a', 9, S + 4 * DAY)], tb)
    run(d3, W1_END + 41 * MIN)
    json.dump({'matches': [m('a', 9, S + 15 * DAY)]}, open(os.path.join(d3, 'predict/data.json'), 'w'))   # تأجلت للأسبوع 3
    rc, data = run(d3, S + 16 * DAY)
    T.check('جولة 9 انحسبت في الأسبوع 1 وما تنعاد في الأسبوع 3', (wk(data, 1)['rds'], wk(data, 3)['rds'], wk(data, 3)['pred']), (['9'], [], False))
    # أسبوع فيه جولتين: المعدل من مجموع الجولتين (العين 50+10=60 ÷ 20 = 3.0، الوصل 30+80=110 ÷ 20 = 5.5)
    tb = {'rounds': {}, 'clubs': {'7': [['ain', 5.0, 10, 50], ['wasl', 3.0, 10, 30]], '13': [['ain', 1.0, 10, 10], ['wasl', 8.0, 10, 80]]}}
    d4 = tree([m('a', 7, S + 2 * DAY), m('b', 13, S + 5 * DAY)], tb)
    rc, data = run(d4, S + 6 * DAY)
    p = {r['c']: r['p'] for r in wk(data, 1)['rows'] if r['p'] and r['p'][0]}
    T.check('أسبوع فيه جولتين: كل نادي مرة وحدة بمعدل الجولتين', p, {'wasl': [14, 5.5, 20], 'ain': [13, 3.0, 20]})
    print(f'\nالنتيجة: {T.ok} نجح · {T.fail} فشل')
    sys.exit(1 if T.fail else 0)
