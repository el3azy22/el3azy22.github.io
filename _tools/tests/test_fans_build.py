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


def pts(data, w, board='mano'):
    return {r[0]: r[2] for r in wk(data, w)['clubs'][board] if r[2]}


def seed_p(day, u, g, c, mode='easy', t=None):
    requests.put(T.url(f'p/{day}/{mode}/{u}'), data=json.dumps({'d': day, 'g': g, 'c': c, **({'t': t} if t else {})}), headers=T.OWNER)


if __name__ == '__main__':
    T.load_rules(S, []); T.reset()
    print('— دوري الجماهير v2 (build.py) —')
    club_c(7, 'ain', 3, 12); club_c(7, 'wasl', 3, 11)
    seed_p(7, 'fanA00000000x', 1, 'ain'); requests.put(T.url('f/fanA00000000x'), data=json.dumps({'c': 'ain', 'n': 'سالم', 't': 1}), headers=T.OWNER)
    d = tree([], {'rounds': {}, 'clubs': {}})
    rc, data = run(d, W1_END + 5 * MIN)          # 00:05 الثلاثاء
    T.check('00:05: الأسبوع 1 مب نهائي بعد (العين 12، الوصل 11)', (rc, pts(data, 1), wk(data, 1)['final']), (0, {'ain': 12, 'wasl': 11}, False))
    club_c(7, 'wasl', 4, 17)                     # نتيجة وصلت في المهلة
    rc, data = run(d, W1_END + 13 * MIN)
    T.check('00:13: نتيجة المهلة تنحسب (الوصل 17 يتقدم)', pts(data, 1), {'wasl': 17, 'ain': 12})
    rc, data = run(d, W1_END + 41 * MIN)
    T.check('00:41: الأسبوع 1 نهائي وانضاف للموسم', (wk(data, 1)['final'], {r[0]: r[2] for r in data['season']['clubs']['all'] if r[2]}), (True, {'wasl': 17, 'ain': 12}))
    acc = json.load(open(os.path.join(d, 'fans/acc.json')))
    T.check('التراكم: الأسبوع 1 مرة وحدة + نقاط المشجع', (acc['weeks'], acc['users'].get('fanA00000000')['m']), ([1], 6))
    club_c(7, 'ain', 30, 300)                    # تغيير بعد ما صار نهائي (ما يفترض يصير)
    club_c(9, 'ain', 1, 6)                       # الأسبوع 2
    rc, data = run(d, W1_END + 2 * DAY)
    T.check('بعد التثبيت: الأسبوع 1 ما يتغير، والموسم = الأسبوع 1 + الأسبوع 2', (pts(data, 1), {r[0]: r[2] for r in data['season']['clubs']['all'] if r[2]}), ({'wasl': 17, 'ain': 12}, {'ain': 18, 'wasl': 17}))
    acc = json.load(open(os.path.join(d, 'fans/acc.json')))
    T.check('التراكم ما ينحسب مرتين', acc['weeks'], [1])
    rk = json.load(open(os.path.join(d, 'fans/ranks.json')))
    T.check('مركز المشجع في الموسم', rk['season']['fanA00000000']['all'][:2], [1, 6])
    # فشل القراءة: ما يكتب شي
    d2 = tree([], {'rounds': {}, 'clubs': {}})
    rc, data = run(d2, W1_END + 5 * MIN, db='http://localhost:9')
    T.check('فشل قراءة Firebase: التشغيل يفشل وما ينكتب ملف', (rc != 0, data), (True, None))
    # جولة تغير موعدها بعد ما انحسبت: ما تنحسب مرة ثانية
    T.reset()
    m = lambda i, r, t: {'id': i, 'wk': r, 't': t, 'h': 'ain', 'a': 'wasl', 'st': 6}
    tb = {'rounds': {'9': [['fanB00000000', 'علي', 'ain', 20, 1, 1, S + 4 * DAY]]}, 'clubs': {'9': [['ain', 20.0, 1, 20, 1], ['wasl', 6.0, 1, 6, 0]]}}
    d3 = tree([m('a', 9, S + 4 * DAY)], tb)
    run(d3, W1_END + 41 * MIN)
    json.dump({'matches': [m('a', 9, S + 15 * DAY)]}, open(os.path.join(d3, 'predict/data.json'), 'w'))   # تأجلت للأسبوع 3
    rc, data = run(d3, S + 16 * DAY)
    T.check('جولة 9 انحسبت في الأسبوع 1 وما تنعاد في الأسبوع 3', (wk(data, 1)['rds'], wk(data, 3)['rds'], pts(data, 1, 'pred')), (['9'], [], {'ain': 20, 'wasl': 6}))
    T.check('الموسم: التوقعات مرة وحدة', {r[0]: r[2] for r in data['season']['clubs']['pred'] if r[2]}, {'ain': 20, 'wasl': 6})
    # أسبوع فيه جولتين: المجموع من الجولتين
    tb = {'rounds': {}, 'clubs': {'7': [['ain', 5.0, 10, 50, 2], ['wasl', 3.0, 10, 30, 1]], '13': [['ain', 1.0, 10, 10, 0], ['wasl', 8.0, 10, 80, 4]]}}
    d4 = tree([m('a', 7, S + 2 * DAY), m('b', 13, S + 5 * DAY)], tb)
    rc, data = run(d4, S + 6 * DAY)
    T.check('أسبوع فيه جولتين: مجموع الجولتين لكل نادي', pts(data, 1, 'pred'), {'wasl': 110, 'ain': 60})
    # مباراة وحدة مؤجلة ما تأخر الجولة
    d5 = tree([m('a', 11, S + 2 * DAY), m('b', 11, S + 3 * DAY), m('c', 11, S + 4 * DAY), m('d', 11, S + 24 * DAY)], {'rounds': {}, 'clubs': {}})
    rc, data = run(d5, S + 6 * DAY)
    T.check('جولة فيها مباراة مؤجلة تنحسب في أسبوع أغلب مبارياتها', wk(data, 1)['rds'], ['11'])
    print(f'\nالنتيجة: {T.ok} نجح · {T.fail} فشل')
    sys.exit(1 if T.fail else 0)
