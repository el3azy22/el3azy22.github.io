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


def run(d, now, db=None, approve='1'):
    # approve='1': الاختبارات القديمة تفحص الحسبة بدون شرط الأيام · None: الشرط الحقيقي (3 أيام)
    env = {**os.environ, 'NOW': str(now), 'FBDB': db or T.B, 'FBNS': T.NS, 'TOKEN': 'owner', 'APPROVE': approve or ''}
    r = subprocess.run([sys.executable, os.path.join(d, '_tools/fans/build.py')], env=env, capture_output=True, text=True)
    data = json.load(open(os.path.join(d, 'fans/data.json'))) if os.path.exists(os.path.join(d, 'fans/data.json')) else None
    return r.returncode, data


def wk(data, w):
    return next(x for x in data['weeks'] if x['w'] == w)


def pts(B, board='mano'):
    return {r[0]: r[2] for r in B[board]['clubs'] if r[2]}


def seed_p(day, u, g, c, mode='easy', t=None, sec=None):
    requests.put(T.url(f'p/{day}/{mode}/{u}'), data=json.dumps({'d': day, 'g': g, 'c': c, **({'t': t} if t else {}), **({'sec': sec} if sec else {})}), headers=T.OWNER)


if __name__ == '__main__':
    T.load_rules(S, []); T.reset()
    print('— دوري الجماهير: الآلية الموحدة (build.py) —')
    seed_p(7, 'fanA00000000x', 1, 'ain'); seed_p(7, 'fanB00000000x', 2, 'ain'); seed_p(7, 'fanC00000000x', 1, 'wasl')
    requests.put(T.url('f/fanA00000000x'), data=json.dumps({'c': 'ain', 'n': 'سالم', 't': 1}), headers=T.OWNER)
    d = tree([], {'rounds': {}, 'clubs': {}})
    rc, data = run(d, W1_END + 5 * MIN)          # 00:05 الثلاثاء
    T.check('00:05: الأسبوع 1 مب نهائي بعد (العين 6+5، الوصل 6)', (rc, pts(wk(data, 1)['boards']), wk(data, 1)['final']), (0, {'ain': 11, 'wasl': 6}, False))
    seed_p(7, 'fanD00000000x', 1, 'wasl'); seed_p(7, 'fanE00000000x', 1, 'wasl')     # وصلت في المهلة
    rc, data = run(d, W1_END + 13 * MIN)
    T.check('00:13: نتايج المهلة تنحسب (الوصل 18 يتقدم)', pts(wk(data, 1)['boards']), {'wasl': 18, 'ain': 11})
    rc, data = run(d, W1_END + 41 * MIN)
    T.check('00:41: الأسبوع 1 نهائي وانضاف للموسم', (wk(data, 1)['final'], pts(data['season'], 'all')), (True, {'wasl': 18, 'ain': 11}))
    acc = json.load(open(os.path.join(d, 'fans/acc.json')))
    T.check('التراكم: الأسبوع 1 مرة وحدة + نقاط المشجع', (acc['weeks'], acc['users']['mano']['fanA00000000']['pts']), ([1], 6))
    seed_p(7, 'fanF00000000x', 1, 'ain')         # بعد التثبيت (ما يفترض يتغير)
    seed_p(9, 'fanA00000000x', 3, 'ain')         # الأسبوع 2
    rc, data = run(d, W1_END + 2 * DAY)
    T.check('بعد التثبيت: الأسبوع 1 ما يتغير، والموسم = تشكيلة الأسبوع 1 + 2', (pts(wk(data, 1)['boards']), pts(data['season'], 'all')), ({'wasl': 18, 'ain': 11}, {'wasl': 18, 'ain': 15}))
    acc = json.load(open(os.path.join(d, 'fans/acc.json')))
    T.check('التراكم ما ينحسب مرتين', acc['weeks'], [1])
    rk = json.load(open(os.path.join(d, 'fans/ranks.json')))
    T.check('مركز سالم في الموسم (6 + 4 = 10)', rk['season']['fanA00000000']['all'][1], 10)
    T.check('اسم سالم يطلع في أعلى المشجعين', [x[0] for x in data['season']['all']['fans']], ['سالم'])
    d2 = tree([], {'rounds': {}, 'clubs': {}})
    rc, data = run(d2, W1_END + 5 * MIN, db='http://localhost:9')
    T.check('فشل قراءة Firebase: التشغيل يفشل وما ينكتب ملف', (rc != 0, data), (True, None))
    # جولة تغير موعدها بعد ما انحسبت: ما تنحسب مرة ثانية
    T.reset()
    m = lambda i, r, t: {'id': i, 'wk': r, 't': t, 'h': 'ain', 'a': 'wasl', 'st': 6}
    tb = {'rounds': {'9': [['fanB00000000', 'علي', 'ain', 20, 1, 2, S + 4 * DAY, 0], ['fanG00000000', 'حمد', 'wasl', 6, 0, 2, S + 4 * DAY, 1]]}, 'clubs': {}}
    d3 = tree([m('a', 9, S + 4 * DAY)], tb)
    run(d3, W1_END + 41 * MIN)
    json.dump({'matches': [m('a', 9, S + 15 * DAY)]}, open(os.path.join(d3, 'predict/data.json'), 'w'))
    rc, data = run(d3, S + 16 * DAY)
    T.check('جولة 9 انحسبت في الأسبوع 1 وما تنعاد في الأسبوع 3', (wk(data, 1)['rds'], wk(data, 3)['rds'], pts(wk(data, 1)['boards'], 'pred')), (['9'], [], {'ain': 20, 'wasl': 6}))
    T.check('الموسم: التوقعات مرة وحدة', pts(data['season'], 'pred'), {'ain': 20, 'wasl': 6})
    # أسبوع فيه جولتين: نقاط المشجع من الجولتين
    tb = {'rounds': {'7': [['fanH00000000', 'راشد', 'ain', 10, 1, 1, S + 2 * DAY, 0]], '13': [['fanH00000000', 'راشد', 'ain', 4, 0, 1, S + 5 * DAY, 0]]}, 'clubs': {}}
    d4 = tree([m('a', 7, S + 2 * DAY), m('b', 13, S + 5 * DAY)], tb)
    rc, data = run(d4, S + 6 * DAY)
    T.check('أسبوع فيه جولتين: نقاط الجولتين مع بعض', pts(wk(data, 1)['boards'], 'pred'), {'ain': 14})
    d5 = tree([m('a', 11, S + 2 * DAY), m('b', 11, S + 3 * DAY), m('c', 11, S + 4 * DAY), m('d', 11, S + 24 * DAY)], {'rounds': {}, 'clubs': {}})
    rc, data = run(d5, S + 6 * DAY)
    T.check('جولة فيها مباراة مؤجلة تنحسب في أسبوع أغلب مبارياتها', wk(data, 1)['rds'], ['11'])
    # التشكيلة المعروضة: 13 مشجع للعين ⇒ أفضل 11 بالضبط ومجموعهم = نقاط النادي، والاسم المخفي ما يطلع
    T.reset()
    for i in range(13):
        seed_p(3, f'xi{i:02d}000000x', 1 + i % 6, 'ain', sec=10 + i)
    requests.put(T.url('f/xi00000000x'), data=json.dumps({'c': 'ain', 'n': 'خليفة', 't': 1}), headers=T.OWNER)
    d6 = tree([], {'rounds': {}, 'clubs': {}})
    rc, data = run(d6, S + 5 * DAY)
    B = wk(data, 1)['boards']['mano']; row = next(r for r in B['clubs'] if r[0] == 'ain'); L = B['xi']['ain']
    T.check('التشكيلة 11 ومجموعها = نقاط النادي', (len(L), sum(x[1] for x in L), row[2], row[3], row[4]), (11, row[2], sum(sorted([7 - (1 + i % 6) for i in range(13)], reverse=True)[:11]), 11, 13))
    T.check('اسم المشجع يطلع في التشكيلة واللي بدون اسم فاضي', (L[0][0], L[1][0], L[0][3]), ('خليفة', '', 1))
    T.check('الموسم ما فيه تشكيلة (مجموع الأسابيع)', 'xi' in data['season']['mano'], False)
    rk = json.load(open(os.path.join(d6, 'fans/ranks.json')))
    T.check('مركز المشجع فيه ناديه', rk['week']['xi00000000x'[:12]]['mano'][3], 'ain')
    # تعادل كامل على آخر مكان: 13 مشجع بنفس كل شي ⇒ 11 تنحسب، و13 تطلع «متعادل» بنفس المركز، ونقاط النادي ما تتغير
    T.reset()
    for i in range(13):
        seed_p(3, f'tt{i:02d}000000x', 2, 'wasl', sec=50)
    rc, data = run(tree([], {'rounds': {}, 'clubs': {}}), S + 5 * DAY)
    B = wk(data, 1)['boards']['mano']; row = next(r for r in B['clubs'] if r[0] == 'wasl'); L = B['xi']['wasl']
    T.check('تعادل كامل: النادي 11×5، القائمة 11 متعادلين بمركز 1، و2 متعادلين برا القائمة', (row[2], row[3], len(L), {x[3] for x in L}, all(x[4] for x in L), len(B['xt']['wasl'])), (55, 11, 11, {1}, True, 2))
    # المشجع المعتمد (v3.1): يدخل التشكيلة بعد 3 أيام لعب مختلفة، وأول يومين من الموسم يكفي يوم/يومين
    T.reset()
    seed_p(1, 'ap0000000001x', 1, 'ain')
    rc, data = run(tree([], {'rounds': {}, 'clubs': {}}), S + 2 * 3600000, approve=None)          # اليوم 1: يكفي يوم
    T.check('اليوم 1: اللي لعب يدخل التشكيلة على طول', next(r for r in wk(data, 1)['boards']['mano']['clubs'] if r[0] == 'ain')[2], 6)
    for d in (1, 2, 3):
        seed_p(d, 'ap0000000001x', 1, 'ain')
    seed_p(5, 'ap0000000002x', 1, 'ain'); seed_p(5, 'ap0000000003x', 1, 'ain')       # حسابين يدد يوم 5
    d7 = tree([], {'rounds': {}, 'clubs': {}})
    rc, data = run(d7, S + 4 * DAY + 3600000, approve=None)                                        # اليوم 5
    B = wk(data, 1)['boards']['mano']; row = next(r for r in B['clubs'] if r[0] == 'ain')
    T.check('اليوم 5: المعتمد بس في التشكيلة (3 أيام × 6 = 18)، والحسابين اليدد ينتظرون', (row[2], row[3], B['pend'].get('ain')), (18, 1, 2))
    rk = json.load(open(os.path.join(d7, 'fans/ranks.json')))['week']
    T.check('المشجع يشوف أيامه: المعتمد 3 من 3، واليديد 1 من 3', (rk['ap0000000001']['act'], rk['ap0000000002']['act']), ([3, 3], [1, 3]))
    T.check('نقاطه الشخصية تنحسب حتى لو مب معتمد', rk['ap0000000002']['mano'][1], 6)
    for d in (6, 7):
        seed_p(d, 'ap0000000002x', 1, 'ain')
    rc, data = run(d7, S + 6 * DAY + 3600000, approve=None)                                        # اليوم 7: اليديد كمّل 3 أيام
    row = next(r for r in wk(data, 1)['boards']['mano']['clubs'] if r[0] == 'ain')
    T.check('أول ما يكمل 3 أيام: كل نقاطه في الأسبوع تدخل (18 + 18)', (row[2], row[3]), (36, 2))
    rc, data = run(d7, S + 7 * DAY + 41 * MIN, approve=None)                                       # الأسبوع 1 نهائي
    acc = json.load(open(os.path.join(d7, 'fans/acc.json')))
    T.check('الأسبوع النهائي يحفظ أيام اللعب للاعتماد', sorted(acc['act'].get('ap0000000001', [])), [1, 2, 3])
    print(f'\nالنتيجة: {T.ok} نجح · {T.fail} فشل')
    sys.exit(1 if T.fail else 0)
