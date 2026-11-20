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


def run(d, now, db=None, approve='1', grid=''):
    # approve='1': الاختبارات القديمة تفحص الحسبة بدون شرط الأيام · None: الشرط الحقيقي (3 أيام)
    env = {**os.environ, 'NOW': str(now), 'FBDB': db or T.B, 'FBNS': T.NS, 'TOKEN': 'owner', 'APPROVE': approve or '', 'GRID_START': grid}
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
    T.check('اسم سالم يطلع في أعلى المشجعين', 'سالم' in [x[0] for x in data['season']['all']['fans']], True)
    fl = data['season']['all']['fans']
    T.check('أعلى المشجعين بالترتيب بدون فراغات (اللي بدون اسم = «»)', [x[3] for x in fl] == sorted(x[3] for x in fl) and fl[0][3] == 1 and '' in [x[0] for x in fl], True)
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

    # ── شبكة الدوري (v3.2): صح نقطة، نادر نقطتين (حلها 30+ واختاره أقل من 10%)، الغلط والخانة المكررة أخطاء ──
    T.reset()
    requests.put(T.url(''), headers=T.OWNER, data=json.dumps({
        'gq': {'2': {'r': ['ain', 'wasl', 'nasr'], 'n': 1, 'a': {'00': ['p1', 'p2'], '01': ['p3', 'p4']}}},
        'gp': {'2': {'gridA0000000x': {'c': 'ain', 'n': 3, 's': 50, 'a': {'1': {'k': '00', 'p': 'p1', 'd': 2, 't': S + DAY + 1000},
                                                                         '2': {'k': '01', 'p': 'bad', 'd': 2, 't': S + DAY + 2000},
                                                                         '3': {'k': '01', 'p': 'p3', 'd': 2, 't': S + DAY + 3000}}},
                     'gridB0000000x': {'c': 'wasl', 'n': 2, 'a': {'1': {'k': '00', 'p': 'p2', 'd': 2, 't': S + DAY + 1000},
                                                                  '2': {'k': '00', 'p': 'p1', 'd': 2, 't': S + DAY + 2000}}}}},
        'gc': {'2': {'00': {'p1': 2, 'p2': 38}, '01': {'p3': 10}}}, 'gn': {'2': {'00': 40, '01': 10}}}))
    dg = tree([], {'rounds': {}, 'clubs': {}})
    os.makedirs(os.path.join(dg, 'grid'))
    rc, data = run(dg, S + DAY + 12 * 3600000, grid='1')
    T.check('الشبكة: لوحة جديدة في الدوري', [c['id'] for c in data['challenges']], ['mano', 'pred', 'grid'])
    T.check('الشبكة: نادر 2 + صح 1 (العين) · صح 1 والمكرر خطأ (الوصل)', pts(wk(data, 1)['boards'], 'grid'), {'ain': 3, 'wasl': 1})
    T.check('الشبكة تدخل «الكل»', pts(wk(data, 1)['boards'], 'all'), {'ain': 3, 'wasl': 1})
    rc, data = run(dg, S + DAY + 12 * 3600000)
    T.check('قبل الانطلاق: الشبكة ما تدخل الدوري', [c['id'] for c in data['challenges']], ['mano', 'pred'])

    # ── توقّع تشكيلة ناديك: كل لاعب صح من التشكيلة الأساسية = نقطة ──
    sys.path.insert(0, os.path.join(T.ROOT, '_tools', 'fans'))
    os.environ['TP_START'] = '1'
    os.environ['LAUNCH5'] = '0'
    import importlib, build as FB
    importlib.reload(FB)
    L = {'501': {'t': S + DAY + 3600000, 'wk': 9, 'h': 'ain', 'a': 'wasl', 'hs': [f'a{i}' for i in range(11)], 'as': [f'w{i}' for i in range(11)]}}
    tp = {'501': {'tA': {'c': 'ain', 'x': '~'.join([f'a{i}' for i in range(8)] + ['x1', 'x2', 'x3']), 'w': 5},
                  'tB': {'c': 'wasl', 'x': '~'.join([f'w{i}' for i in range(11)]), 'w': 5},
                  'tC': {'c': 'nasr', 'x': '~'.join([f'a{i}' for i in range(11)]), 'w': 5},
                  'tD': {'c': 'ain', 'x': '~'.join(['a0'] * 11), 'w': 5}}}
    U = FB.collect_tp(tp, L, 1, 7)
    T.check('التوقع: 8 من 11 = 8 نقاط و3 أخطاء', (U['tA']['pts'], U['tA']['mis'], U['tA']['plays']), (8, 3, 1))
    T.check('التوقع: 11 من 11 لجمهور الضيف من تشكيلته هو', U['tB']['pts'], 11)
    T.check('نادي مب طرف في المباراة ما ينحسب', 'tC' in U, False)
    T.check('لاعب مكرر ينحسب مرة وحدة', U['tD']['pts'], 1)
    # ── «منو بيسجل؟»: توقع مستقل · سجّل = 3 · كل هدف زيادة +1 · أول هدف في المباراة +2 · بعد ما تخلص بس ──
    L2 = {'601': {**L['501'], 'hg': {'a9': 2, 'b1': 1}, 'ag': {'w3': 1}, 'fg': 'a9', 'fin': 1}}
    x11 = '~'.join(f'a{i}' for i in range(11))
    tps = {'601': {'s1': {'c': 'ain', 'x': x11, 's': 'a9', 'w': 5},            # أساسي سجّل 2 وأول هدف: 3+1+2
                   's2': {'c': 'ain', 'x': x11, 's': 'b1', 'w': 5},            # بديل (جوكر) دخل وسجّل: 3
                   's3': {'c': 'ain', 'x': x11, 's': 'a2', 'w': 5},            # ما سجّل: 0
                   's4': {'c': 'ain', 'x': x11, 's': 'w3', 'w': 5},            # لاعب الخصم: ما ينحسب
                   's5': {'c': 'wasl', 'x': '~'.join(f'w{i}' for i in range(11)), 's': 'w3', 'w': 5},
                   's6': {'c': 'ain', 'x': x11, 'w': 5}}}
    U = FB.collect_tp(tps, L2, 1, 7)
    T.check('الهداف: سجّل هدفين وأول هدف = 11 + 6', U['s1']['pts'], 17)
    T.check('الهداف: البديل اللي سجّل ينحسب (3)', U['s2']['pts'], 14)
    T.check('الهداف: ما سجّل = 0 وما يزيد الأخطاء', (U['s3']['pts'], U['s3']['mis']), (11, 0))
    T.check('الهداف: لاعب من الفريق الثاني ما ينحسب', U['s4']['pts'], 11)
    T.check('الهداف: جمهور الضيف من أهداف فريقه', U['s5']['pts'], 14)
    T.check('بدون هداف: نفس النقاط', U['s6']['pts'], 11)
    U = FB.collect_tp(tps, {'601': {k: v for k, v in L2['601'].items() if k != 'fin'}}, 1, 7)
    T.check('الهداف ما ينحسب قبل ما تخلص المباراة', U['s1']['pts'], 11)
    FB.LAUNCH5 = 10 ** 15
    T.check('الهداف ما ينحسب في جولة انفتحت قبل الإطلاق', FB.collect_tp(tps, L2, 1, 7)['s1']['pts'], 11)
    FB.LAUNCH5 = 0
    # ── «خماسي الجولة»: النقاط في يوم مباراة كل لاعب، القائد ×2، والخانة الغلط صفر ──
    sqi = {'gk': ('ain', 'GK'), 'd1': ('ain', 'DEF'), 'm1': ('wasl', 'MID'), 'f1': ('wasl', 'FWD'), 'f2': ('nasr', 'FWD'),
           'f3': ('ain', 'FWD'), 'd2': ('hatta', 'DEF')}
    st = {'701': {'t': S + DAY + 3600000, 'wk': 7, 'h': 'ain', 'a': 'wasl', 'sc': [2, 0], 'ast': 1,
                  'p': {'gk': {'s': 'H', 'm': 90, 'sv': 4}, 'd1': {'s': 'H', 'm': 70, 'g': 1, 'y': 1}, 'f3': {'s': 'H', 'm': 90, 'g': 1, 'a': 1, 'b': 3},
                        'm1': {'s': 'A', 'm': 45, 'og': 1, 'r': 1, 'gc': 2}, 'f1': {'s': 'A', 'm': 20, 'gc': 1}}},
          '702': {'t': S + 9 * DAY, 'wk': 7, 'h': 'nasr', 'a': 'hatta', 'sc': [0, 0], 'p': {'f2': {'s': 'H', 'm': 90, 'pm': 1}}}}
    P = lambda *a: {str(i): {'c': c, 'k': k} for i, (c, k) in enumerate(a)}
    k5 = {'7': {'u1': {'c': 'ain', 'p': P(('ain', 'gk'), ('ain', 'd1'), ('wasl', 'm1'), ('wasl', 'f1'), ('nasr', 'f2')), 'cap': 1, 'w': 5},
                'u2': {'c': 'wasl', 'p': P(('ain', 'gk'), ('hatta', 'd2'), ('wasl', 'm1'), ('ain', 'f3'), ('nasr', 'f2')), 'cap': 3, 'w': 5},
                'u3': {'c': 'none', 'p': P(('ain', 'd1'), ('ain', 'gk'), ('wasl', 'm1'), ('wasl', 'f1'), ('hatta', 'f2')), 'cap': 0, 'w': 5}}}
    T.check('نقاط اللاعب: مدافع 70 دقيقة سجّل وإنذار وشباك نظيفة = 2+6+4−1', FB.k5_points({'m': 70, 'g': 1, 'y': 1}, 'DEF'), 11)
    T.check('نقاط اللاعب: وسط 45 دقيقة عكسي وطرد = 1−2−3', FB.k5_points({'m': 45, 'og': 1, 'r': 1, 'gc': 2}, 'MID'), -4)
    T.check('نقاط اللاعب: هدف المهاجم 4 والوسط 5', (FB.k5_points({'m': 90, 'g': 1}, 'FWD'), FB.k5_points({'m': 90, 'g': 1, 'gc': 1}, 'MID')), (6, 7))
    T.check('نقاط الحارس: 7 تصديات + صد جزاء + 3 أهداف دخلت + نجم 1 = 2+2+5−1+1', FB.k5_points({'m': 90, 'sv': 7, 'ps': 1, 'gc': 3, 'b': 1}, 'GK'), 9)
    T.check('الجزاء: كسبه وانسجل صناعة +3، وضيّع جزاء −2', FB.k5_points({'m': 90, 'g': 1, 'pw': 1, 'pm': 1, 'gc': 1}, 'FWD'), 7)
    T.check('الشباك النظيفة للوسط +1، والمهاجم بدون', (FB.k5_points({'m': 90}, 'MID'), FB.k5_points({'m': 90}, 'FWD')), (3, 2))
    U = FB.collect_k5(k5, st, 1, 7, sqi=sqi)
    # u1: حارس 2+4+1=7 · مدافع 11×2 (قائد)=22 · وسط −4 · مهاجم 1 · النصر بعدين (الأسبوع 2)
    T.check('الخماسي: الأسبوع 1 (القائد ×2)', (U['u1']['pts'], U['u1']['plays']), (26, 1))
    # u2: حارس 7 + وسط −4 + مهاجم (2+4+3+3 نجم)=12×2 ⇒ 27 · مدافع حتا مباراته الأسبوع الياي · ونادي اللي يحسب له = الوصل
    T.check('الخماسي: الصناعة ونجم المباراة وقائد مهاجم', (U['u2']['pts'], U['u2']['c']), (27, 'wasl'))
    # u3: الحارس في خانة المدافع والعكس = صفر لهم · لاعب النصر بنادي حتا = صفر
    T.check('الخماسي: المركز الغلط ونادي غلط ما ينحسبون', (U['u3']['pts'], U['u3']['c']), (-3, ''))
    U2 = FB.collect_k5(k5, st, 8, 14, sqi=sqi)
    T.check('الخماسي: لاعب مباراته في أسبوع ثاني ينحسب في أسبوعه (مهاجم 90 دقيقة وضيّع جزاء = 0)', (U2['u1']['pts'], U2['u1']['plays']), (0, 0))
    k5b = {'7': {'u4': {'c': 'ain', 'p': P(('ain', 'gk'), ('ain', 'd1'), ('wasl', 'm1'), ('ain', 'f3'), ('ain', 'd1')), 'cap': 0, 'w': 5}}}
    T.check('الخماسي: ثالث لاعب من نفس النادي واللاعب المكرر صفر', FB.collect_k5(k5b, st, 1, 7, sqi=sqi)['u4']['pts'], 14 + 11 - 4)
    # ملخص اللوحة (fans/tp.json): أعداد بس، والتوزيع بعد التشكيلة الرسمية
    pdm = {'matches': [{'id': 501, 't': S + DAY + 3600000, 'wk': 9, 'h': 'ain', 'a': 'wasl'},
                       {'id': 502, 't': S + 3 * DAY, 'wk': 9, 'h': 'nasr', 'a': 'hatta'}]}
    sm = FB.tp_summary(pdm, L, tp, S + DAY + 5 * 3600000, None, read=lambda mid: {'z': {'c': 'nasr', 'x': 'q'}} if mid == '502' else None)
    T.check('الملخص: عدد التوقعات ولكل جمهور (اللي مب طرف ما ينعد)', (sm['501']['n'], sm['501']['ain'], sm['501']['wasl']), (3, 2, 1))
    T.check('الملخص: توزيع الصح بعد التشكيلة', (sm['501']['d'][8], sm['501']['d'][11], sm['501']['d'][1]), (1, 1, 1))
    T.check('الملخص: مباراة ياية بدون توزيع', (sm['502']['n'], 'd' in sm['502']), (1, False))
    T.check('الملخص ما فيه توقعات أحد', '"x"' in json.dumps(sm) or 'q' in json.dumps(sm), False)
    os.environ.pop('TP_START', None)
    # داخل الإمارات أو برا (fans/geo.json): أرقام مجمعة بس
    gf = {'u1': {'c': 'ain', 'n': 'سالم'}, 'u2': {'c': 'ain', 'n': ''}, 'u3': {'c': 'wasl', 'n': 'x'}, 'u4': {'c': 'none', 'n': ''}, 'u5': {'c': 'wasl'}, 'u6': {'n': 'بدون نادي'}}
    gg = {'u1': 'Asia/Dubai', 'u2': 'Asia/Riyadh', 'u3': 'Asia/Dubai', 'u4': 'Europe/Paris', 'u6': 'Asia/Dubai'}
    geo = FB.geo_summary(gf, gg, 1)
    T.check('المناطق: داخل/برا/ما نعرف', geo['all'], {'ae': 2, 'out': 2, 'unk': 1})
    T.check('المناطق: اللي كاتبين أساميهم', geo['named'], {'ae': 2, 'out': 0, 'unk': 0})
    T.check('المناطق: لكل نادي (المحايد ما ينحسب لنادي)', geo['clubs'], {'ain': {'ae': 1, 'out': 1, 'unk': 0}, 'wasl': {'ae': 1, 'out': 0, 'unk': 1}})
    T.check('المناطق: الدول برا', geo['out'], {'SA': 1, 'Z:Europe': 1})
    T.check('المناطق: ما فيها أسماء ولا معرفات', any(x in json.dumps(geo, ensure_ascii=False) for x in ('سالم', 'u1', 'Asia/')), False)
    print(f'\nالنتيجة: {T.ok} نجح · {T.fail} فشل')
    sys.exit(1 if T.fail else 0)
