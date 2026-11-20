"""اختبارات قواعد Firebase (الحماية على السيرفر) على المحاكي — مستقلة عن كود الصفحات.
التشغيل: firebase emulators:start --only database --project demo-el3 (منفذ 9000) ثم:
  python3 _tools/tests/test_rules.py
يولّد القواعد من make_rules.py بوقت بداية (L) وجدول مباريات صناعي، عشان نختبر حدود الوقت بالوقت الحقيقي."""
import base64, json, os, shutil, subprocess, sys, tempfile, time, threading
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
B = os.environ.get('EMU', 'http://localhost:9000'); NS = 'demo-el3'
OWNER = {'Authorization': 'Bearer owner'}
DAY = 86400000
ok = fail = 0
os.environ['LAUNCH5'] = '0'      # «منو بيسجل؟» و«الخماسي» شغالين في كل الجولات بالاختبار (الإطلاق الحقيقي في khamsa/config.json)


def tok(u):
    e = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b'=').decode()
    n = int(time.time())
    return e({'alg': 'none', 'typ': 'JWT'}) + '.' + e({'sub': u, 'user_id': u, 'iat': n, 'exp': n + 3600, 'aud': NS,
        'iss': 'https://securetoken.google.com/' + NS, 'auth_time': n, 'firebase': {'sign_in_provider': 'anonymous'}}) + '.'


def url(path, u=None):
    return f'{B}/{path}.json?ns={NS}' + (f'&auth={tok(u)}' if u else '')


def patch(u, body): return requests.patch(url('', u), data=json.dumps(body)).status_code
def put(u, path, body): return requests.put(url(path, u), data=json.dumps(body)).status_code
def get(path, u=None): return requests.get(url(path, u), headers={} if u else OWNER)


def check(name, got, want):
    global ok, fail
    good = got == want
    ok += good; fail += (not good)
    print(('✅' if good else '❌'), name, '→', got, '' if good else f'(المتوقع {want})')


def load_rules(L, matches):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, '_tools', 'firebase')); os.makedirs(os.path.join(d, 'predict'))
    shutil.copy(os.path.join(ROOT, '_tools', 'firebase', 'make_rules.py'), os.path.join(d, '_tools', 'firebase'))
    json.dump({'matches': matches}, open(os.path.join(d, 'predict', 'data.json'), 'w'))
    subprocess.run([sys.executable, 'make_rules.py'], cwd=os.path.join(d, '_tools', 'firebase'), env={**os.environ, 'L': str(L)}, check=True)
    r = requests.put(f'{B}/.settings/rules.json?ns={NS}', data=open(os.path.join(d, '_tools', 'firebase', 'rules.json')).read(), headers=OWNER)
    assert r.status_code == 200, r.text


def reset(data=None):
    requests.put(url(''), data=json.dumps(data or {}), headers=OWNER)


inc = lambda n=1: {'.sv': {'increment': n}}
TS = {'.sv': 'timestamp'}


def mano_body(u, d, m, g, c, t=True):
    b = {f'p/{d}/{m}/{u}': {'d': d, 'g': g, 'c': c, **({'t': TS} if t else {})}, f's/{d}/{m}/n': inc()}
    if g:
        b[f's/{d}/{m}/w'] = inc(); b[f's/{d}/{m}/g{g}'] = inc()
    if c:
        b[f'c/{d}/{m}/{c}/n'] = inc()
        if g:
            b[f'c/{d}/{m}/{c}/t'] = inc(7 - g)
    return b


def mano_tests():
    now = int(time.time() * 1000)
    # اليوم 3 بدأ قبل ساعتين (يعني اليوم 2 خلص قبل ساعتين = برا مهلة الـ15 دقيقة)
    L = now - 2 * DAY - 2 * 3600000
    load_rules(L, []); reset()
    print('\n— منو اللاعب؟ —')
    check('نتيجة لاعب اليوم صحيحة تنقبل', patch('u1', mano_body('u1', 3, 'easy', 2, 'wahda')), 200)
    check('نفس المشجع مرة ثانية (ضغطتين) ترفض', patch('u1', mano_body('u1', 3, 'easy', 1, 'wahda')), 401)
    check('نتيجة يوم أمس بعد ما خلصت المهلة ترفض', patch('u2', mano_body('u2', 2, 'easy', 1, 'wahda')), 401)
    check('نتيجة يوم باجر ترفض', patch('u2', mano_body('u2', 4, 'easy', 1, 'wahda')), 401)
    check('الخبير قبل لاعب اليوم يرفض', patch('u3', mano_body('u3', 3, 'pro', 1, 'ain')), 401)
    check('الخبير بنادي غير نادي لاعب اليوم يرفض', patch('u1', mano_body('u1', 3, 'pro', 1, 'ain')), 401)
    check('الخبير بنفس النادي ينقبل', patch('u1', mano_body('u1', 3, 'pro', 1, 'wahda')), 200)
    bad = mano_body('u4', 3, 'easy', 2, 'ain'); bad['c/3/easy/ain/t'] = inc(6)
    check('غش: نقاط النادي أكثر من 7 − المحاولات ترفض', patch('u4', bad), 401)
    bad = mano_body('u4', 3, 'easy', 7, 'ain')
    check('محاولات 7 (أكثر من المسموح) ترفض', patch('u4', bad), 401)
    bad = mano_body('u4', 3, 'easy', 2, 'ain'); bad['p/3/easy/u4']['t'] = 1
    check('وقت حل مزور ترفض', patch('u4', bad), 401)
    bad = mano_body('u4', 3, 'easy', 2, 'ain'); bad['p/3/easy/u4'] = {'d': 3, 'g': 2, 'c': 'ain', 't': TS}
    del bad['s/3/easy/n']
    check('بدون زيادة عداد اللاعبين ترفض', patch('u4', bad), 401)
    bad = mano_body('u4', 3, 'easy', 1, 'ain'); del bad['c/3/easy/ain/n']
    check('غش: نقاط النادي بدون عداد اللعبة ترفض', patch('u4', bad), 401)
    bad = mano_body('u4', 3, 'easy', 0, 'ain'); del bad['c/3/easy/ain/n']
    check('غش: خسارة بدون ما تنحسب للنادي ترفض', patch('u4', bad), 401)
    bad = mano_body('u4', 3, 'easy', 1, 'ain'); del bad['c/3/easy/ain/t']
    check('فوز بدون نقاط النادي يرفض', patch('u4', bad), 401)
    bad = mano_body('u4', 3, 'easy', 1, 'ain'); bad['p/3/easy/u4']['g'] = 0.001; bad['c/3/easy/ain/t'] = inc(6.999)
    check('غش: محاولات بكسور (0.001) ترفض', patch('u4', bad), 401)
    bad = mano_body('u4', 3, 'easy', 1, 'ain'); bad['p/3/easy/u4']['sec'] = -5
    check('وقت الحل بالسالب يرفض', patch('u4', bad), 401)
    bad = mano_body('u4', 3, 'easy', 1, 'ain'); bad['p/3/easy/u4']['sec'] = 12.5
    check('وقت الحل بكسور يرفض', patch('u4', bad), 401)
    bad = mano_body('u4', 3, 'easy', 1, 'ain'); bad['p/3/easy/u4']['sec'] = 'x'
    check('وقت الحل نص يرفض', patch('u4', bad), 401)
    ok = mano_body('u9', 3, 'easy', 2, 'ain'); ok['p/3/easy/u9']['sec'] = 95
    check('نتيجة مع وقت الحل (95 ثانية) تنقبل', patch('u9', ok), 200)
    check('مشجع يكتب نتيجة باسم مشجع ثاني ترفض', patch('u5', mano_body('u6', 3, 'easy', 2, 'ain')), 401)
    check('نتيجة بدون نادي تنقبل (ما تنحسب لنادي)', patch('u7', mano_body('u7', 3, 'easy', 0, '')), 200)
    check('المشجع يقرا نتيجته', get('p/3/easy/u1', 'u1').status_code, 200)
    check('المشجع ما يقرا نتيجة غيره', get('p/3/easy/u1', 'u7').status_code, 401)
    # تزامن: 8 مشجعين مع بعض
    res = []
    th = [threading.Thread(target=lambda i=i: res.append(patch(f'z{i}', mano_body(f'z{i}', 3, 'easy', 3, 'sharjah')))) for i in range(8)]
    [t.start() for t in th]; [t.join() for t in th]
    s = get('s/3/easy').json(); c = get('c/3/easy/sharjah').json()
    n_ok = res.count(200)
    check('تزامن: العدادات = عدد المقبولين', (s['n'] - 3, c['n'], c['t']), (n_ok, n_ok, n_ok * 4))
    # جواب لاعب اليوم: يتقرى من يومه بس، وما أحد يكتبه
    requests.put(url('q'), data=json.dumps({str(d): f'pl{d}' for d in range(1, 6)}), headers=OWNER)
    check('جواب اليوم (3) يتقرى للكل', requests.get(url('q/3')).json(), 'pl3')
    check('جواب أمس (2) يتقرى', requests.get(url('q/2')).json(), 'pl2')
    check('جواب باجر (4) ما يتقرى', requests.get(url('q/4')).status_code, 401)
    check('الجدول كامل ما يتقرى', requests.get(url('q')).status_code, 401)
    check('مشجع يكتب جواب يرفض', put('u1', 'q/4', 'x'), 401)
    # مهلة 15 دقيقة بعد 12 بالليل
    L2 = now - DAY - 5 * 60000   # اليوم 2 بدأ قبل 5 دقايق
    load_rules(L2, []); reset()
    check('نتيجة أمس خلال أول 15 دقيقة تنقبل', patch('u8', mano_body('u8', 1, 'easy', 2, 'ain')), 200)


def predict_tests():
    now = int(time.time() * 1000)
    ms = [{'id': '9001', 'wk': 1, 't': now + 3600000, 'h': 'ain', 'a': 'wahda', 'st': 1},
          {'id': '9002', 'wk': 1, 't': now - 60000, 'h': 'wasl', 'a': 'nasr', 'st': 2},
          {'id': '9003', 'wk': 2, 't': now + 2 * DAY, 'h': 'ain', 'a': 'nasr', 'st': 1}]     # الجولة الجاية: تفتح بعد نهاية الجولة 1
    load_rules(now - DAY, ms); reset({'f': {'p1': {'c': 'ain', 'n': 'سالم', 't': 1}}})
    print('\n— دوري التوقعات —')
    rec = {'h': 2, 'a': 1, 'c': 'ain', 'n': 'سالم', 'w': TS}
    check('توقع قبل الصافرة ينقبل', put('p1', 'pr/9001/p1', rec), 200)
    check('تعديل التوقع قبل الصافرة ينقبل', put('p1', 'pr/9001/p1', {**rec, 'h': 3}), 200)
    check('توقع بعد الصافرة يرفض', put('p1', 'pr/9002/p1', rec), 401)
    check('نادي غير نادي بطاقة المشجع يرفض', put('p1', 'pr/9001/p1', {**rec, 'c': 'wahda'}), 401)
    check('اسم غير اسم البطاقة يرفض', put('p1', 'pr/9001/p1', {**rec, 'n': 'غيره'}), 401)
    check('وقت كتابة مزور يرفض', put('p1', 'pr/9001/p1', {**rec, 'w': now - 999999}), 401)
    check('أهداف 21 ترفض', put('p1', 'pr/9001/p1', {**rec, 'h': 21}), 401)
    check('أهداف بكسور ترفض', put('p1', 'pr/9001/p1', {**rec, 'h': 1.5}), 401)
    check('مشجع بدون بطاقة: نادي none واسم فاضي ينقبل', put('p2', 'pr/9001/p2', {'h': 0, 'a': 0, 'c': 'none', 'n': '', 'w': TS}), 200)
    check('توقعات مباراة ما بدت ما تنقرا للكل', get('pr/9001', 'p2').status_code, 401)
    check('توقعات مباراة بدت تنقرا', requests.get(url('pr/9002')).status_code, 200)
    check('الجولة الجاية مقفولة لين تخلص الجولة الحالية', put('p1', 'pr/9003/p1', rec), 401)


def rate_tests():
    now = int(time.time() * 1000)
    load_rules(now - DAY, []); reset()
    print('\n— قيّم اللاعبين —')
    H = 3600000
    def body(u, kick, r, st=None):
        k = f'5001_{kick}'
        b = {f'rv/{k}/{u}': {'t': kick, 'r': r, **({'st': st} if st else {})}, f'rn/{k}': inc()}
        for p, v in r.items():
            b[f'ra/{k}/{p}/n'] = inc(); b[f'ra/{k}/{p}/s'] = inc(v)
        if st:
            b[f'rs/{k}/{st}'] = inc()
        return b
    k_open, k_early, k_late = now - 3 * H, now - 60 * 60000, now - 51 * H
    check('تقييم بعد المباراة ينقبل', patch('r1', body('r1', k_open, {'101': 7, '102': 9}, '102')), 200)
    check('نفس الجهاز مرة ثانية يرفض', patch('r1', body('r1', k_open, {'101': 8})), 401)
    check('قبل ما تخلص المباراة (أقل من 100 دقيقة) يرفض', patch('r2', body('r2', k_early, {'101': 7})), 401)
    check('بعد 50 ساعة يرفض', patch('r2', body('r2', k_late, {'101': 7})), 401)
    check('تقييم 11 يرفض', patch('r3', body('r3', k_open, {'101': 11})), 401)
    check('تقييم 0 يرفض', patch('r3', body('r3', k_open, {'101': 0})), 401)
    b = body('r4', k_open, {'101': 6}); b[f'ra/5001_{k_open}/101/s'] = inc(10)
    check('غش: مجموع غير التقييم يرفض', patch('r4', b), 401)
    b = body('r5', k_open, {'101': 10}); del b[f'ra/5001_{k_open}/101/n']
    check('غش: مجموع التقييم بدون العدد يرفض', patch('r5', b), 401)
    b = body('r6', k_open, {'101': 1}); del b[f'ra/5001_{k_open}/101/s']
    check('غش: عدد بدون المجموع يرفض', patch('r6', b), 401)
    a = get(f'ra/5001_{k_open}/101').json()
    check('مجموع لاعب 101 بعد التقييمات المقبولة', a, {'n': 1, 's': 7})


def fan_tests():
    now = int(time.time() * 1000)
    load_rules(now - DAY, []); reset()
    print('\n— بطاقة المشجع —')
    check('اختيار نادي أول مرة مع +1 لعدد مشجعينه ينقبل', patch('f1', {'f/f1': {'c': 'ain', 'n': 'سالم', 't': TS}, 'fc/ain': inc()}), 200)
    check('اختيار نادي بدون زيادة العدد يرفض', patch('f2', {'f/f2': {'c': 'ain', 't': TS}}), 401)
    check('زيادة العدد بـ2 يرفض', patch('f3', {'f/f3': {'c': 'ain', 't': TS}, 'fc/ain': inc(2)}), 401)
    t1 = get('f/f1').json()['t']
    check('تغيير النادي خلال 24 ساعة ينقبل (+1 للجديد −1 للقديم)', patch('f1', {'f/f1': {'c': 'wasl', 'n': 'سالم', 't': t1}, 'fc/wasl': inc(), 'fc/ain': inc(-1)}), 200)
    check('عدد المشجعين بعد التغيير', (get('fc/ain').json(), get('fc/wasl').json()), (0, 1))
    t2 = get('f/f1').json()['t']
    check('غش: تغيير النادي بزيادة الجديد بدون نقص القديم يرفض', patch('f1', {'f/f1': {'c': 'ain', 'n': 'سالم', 't': t2}, 'fc/ain': inc()}), 401)
    check('المشجع ما يقدر يمسح بطاقته (عشان يتخطى حد تغيير النادي)', requests.delete(url('f/f1', 'f1')).status_code, 401)
    check('اسم أطول من 16 حرف يرفض', patch('f1', {'f/f1': {'c': 'wasl', 'n': 'س' * 17, 't': t1}}), 401)
    check('مشجع يقرا بطاقة غيره يرفض', get('f/f1', 'f9').status_code, 401)


def grid_body(u, d, n, k, p, ok=True, club='wahda'):
    b = {f'gp/{d}/{u}/n': n, f'gp/{d}/{u}/a/{n}': {'k': k, 'p': p, 'd': d, 't': TS}}
    if n == 1:
        b[f'gp/{d}/{u}/c'] = club
    if ok:
        b[f'gc/{d}/{k}/{p}'] = inc(); b[f'gn/{d}/{k}'] = inc()
    return b


def grid_tests():
    now = int(time.time() * 1000)
    L = now - 2 * DAY - 2 * 3600000          # اليوم 3 شغال
    load_rules(L, []); reset({'gq': {'3': {'r': ['ain'], 'n': 1}, '4': {'r': ['wasl'], 'n': 2}}})
    print('\n— شبكة الدوري —')
    check('شبكة اليوم تنقرى', requests.get(url('gq/3', 'u1')).status_code, 200)
    check('شبكة باجر ما تنقرى', requests.get(url('gq/4', 'u1')).status_code, 401)
    check('المشجع ما يكتب في الجدول', put('u1', 'gq/3/n', 5), 401)
    check('أول محاولة صح مع العدادات تنقبل', patch('u1', grid_body('u1', 3, 1, '00', 'ali-x')), 200)
    check('نفس المحاولة مرة ثانية (ضغطتين) ترفض', patch('u1', grid_body('u1', 3, 1, '00', 'ali-x')), 401)
    check('تنقيص العداد أو مسح محاولة غلط يرفض', put('u1', 'gp/3/u1/n', 0), 401)
    check('المحاولة 2 غلط بدون عدادات تنقبل', patch('u1', grid_body('u1', 3, 2, '11', 'bad-y', ok=False)), 200)
    check('مسح محاولة سابقة يرفض', put('u1', 'gp/3/u1/a/2', None), 401)
    check('القفز من 2 لـ 4 يرفض', patch('u1', grid_body('u1', 3, 4, '22', 'z', ok=False)), 401)
    b = grid_body('u1', 3, 3, '01', 'p3'); b['gc/3/01/other'] = inc()
    check('عداد لاعب غير اللي اختاره يرفض', patch('u1', b), 401)
    b = grid_body('u1', 3, 3, '01', 'p3'); b['gc/3/01/p3'] = inc(2)
    check('العداد +2 يرفض', patch('u1', b), 401)
    check('عداد بدون محاولة يرفض', patch('u1', {'gc/3/02/p9': inc()}), 401)
    for n in range(3, 10):
        patch('u1', grid_body('u1', 3, n, '0' + str(n % 3), f'p{n}', ok=False))
    check('بعد 9 محاولات: المحاولة 10 ترفض', patch('u1', grid_body('u1', 3, 10, '00', 'p10', ok=False)), 401)
    check('محاولة في يوم أمس ترفض', patch('u2', grid_body('u2', 2, 1, '00', 'p1')), 401)
    check('محاولة في يوم باجر ترفض', patch('u2', grid_body('u2', 4, 1, '00', 'p1')), 401)
    check('مشجع يكتب في سجل غيره يرفض', requests.patch(url('', 'u3'), data=json.dumps(grid_body('u2', 3, 1, '00', 'p1'))).status_code, 401)
    check('المشجع يقرا سجله', requests.get(url('gp/3/u1', 'u1')).status_code, 200)
    check('المشجع ما يقرا سجل غيره', requests.get(url('gp/3/u1', 'u2')).status_code, 401)
    check('العدادات مقروءة للكل', requests.get(url('gc/3')).status_code, 200)
    check('الثواني تنقبل', put('u1', 'gp/3/u1/s', 95), 200)
    check('نادي ثاني بعد الأول يرفض', put('u1', 'gp/3/u1/c', 'ain'), 401)

def tp_tests():
    now = int(time.time() * 1000)
    ms = [{'id': '9101', 'wk': 1, 't': now + 3 * 3600000, 'h': 'ain', 'a': 'wahda', 'st': 1},   # تقفل بعد ساعة
          {'id': '9102', 'wk': 1, 't': now + 90 * 60000, 'h': 'wasl', 'a': 'ain', 'st': 1},     # انقفلت (أقل من ساعتين)
          {'id': '9103', 'wk': 2, 't': now + 2 * DAY, 'h': 'ain', 'a': 'nasr', 'st': 1}]         # الجولة الجاية: ما انفتحت
    load_rules(now - DAY, ms); reset({'f': {'p1': {'c': 'ain', 't': 1}, 'p2': {'c': 'nasr', 't': 1}, 'p3': {'t': 1}}})
    print('\n— توقّع تشكيلة ناديك —')
    x11 = '~'.join(f'k{i}' for i in range(11))
    rec = {'c': 'ain', 'x': x11, 'w': TS}
    check('توقع 11 لاعب قبل القفل ينقبل', put('p1', 'tp/9101/p1', rec), 200)
    check('التعديل قبل القفل ينقبل', put('p1', 'tp/9101/p1', {**rec, 'x': x11.replace('k0', 'k99')}), 200)
    check('بعد القفل (ساعتين قبل البداية) يرفض', put('p1', 'tp/9102/p1', rec), 401)
    check('الجولة اللي ما انفتحت ترفض', put('p1', 'tp/9103/p1', rec), 401)
    check('الخطة تنحفظ ويا التوقع', put('p1', 'tp/9101/p1', {**rec, 'f': '4-4-2'}), 200)
    check('الهداف ينحفظ ويا التوقع', put('p1', 'tp/9101/p1', {**rec, 's': 'k3'}), 200)
    check('هداف فيه ~ يرفض', put('p1', 'tp/9101/p1', {**rec, 's': 'a~b'}), 401)
    check('هداف فاضي يرفض', put('p1', 'tp/9101/p1', {**rec, 's': ''}), 401)
    check('خطة بشكل غلط ترفض', put('p1', 'tp/9101/p1', {**rec, 'f': '<b>'}), 401)
    check('10 لاعبين بس يرفض', put('p1', 'tp/9101/p1', {**rec, 'x': '~'.join(f'k{i}' for i in range(10))}), 401)
    check('نادي غير نادي البطاقة يرفض', put('p1', 'tp/9101/p1', {**rec, 'c': 'wahda'}), 401)
    check('نادي مب طرف في المباراة يرفض', put('p2', 'tp/9101/p2', {**rec, 'c': 'nasr'}), 401)
    check('اللي ما اختار نادي يرفض', put('p3', 'tp/9101/p3', {**rec, 'c': ''}), 401)
    check('ما يقرا توقع غيره', requests.get(url('tp/9101/p1', 'p2')).status_code, 401)


def x_tests():
    now = int(time.time() * 1000)
    load_rules(now - DAY, []); reset({'x': {'b' * 64: {'u': 'p1', 'c': 'old', 'i': 'iv', 'e': now - 1000}}})
    print('\n— رمز النقل —')
    h = 'a' * 64
    rec = {'u': 'p1', 'c': 'enc', 'i': 'iv', 'e': now + 600000}
    check('صاحب البطاقة يسوي رمز', put('p1', f'x/{h}', rec), 200)
    check('أي أحد يعرف الرمز يقراه قبل ما ينتهي', requests.get(url(f'x/{h}')).status_code, 200)
    check('ما يقدر يقرا قائمة الرموز', requests.get(url('x', 'p2')).status_code, 401)
    check('رمز منتهي ما ينقرا', requests.get(url(f'x/{"b" * 64}')).status_code, 401)
    check('غيره ما يكتب فوق رمزه', put('p2', f'x/{h}', {**rec, 'u': 'p2'}), 401)
    check('ما يسوي رمز باسم غيره', put('p2', f'x/{"c" * 64}', rec), 401)
    check('مدة أطول من 15 دقيقة ترفض', put('p1', f'x/{"d" * 64}', {**rec, 'e': now + 3600000}), 401)
    check('مسار مب hash يرفض', put('p1', 'x/abc', rec), 401)
    check('حقل زايد يرفض', put('p1', f'x/{"e" * 64}', {**rec, 'z': 1}), 401)
    check('بدون تسجيل ما يكتب', requests.put(url(f'x/{"f" * 64}'), data=json.dumps(rec)).status_code, 401)
    check('صاحب البطاقة (من التلفون اليديد) يمسحه بعد الاستخدام', requests.delete(url(f'x/{h}', 'p1')).status_code, 200)


def rk_tests():
    now = int(time.time() * 1000)
    load_rules(now - DAY, []); reset({})
    print('\n— رمز الاسترجاع —')
    h = 'a' * 64
    rec = {'u': 'p1', 'c': 'enc', 'i': 'iv'}
    check('صاحب البطاقة يسوي رمز ثابت', put('p1', f'rk/{h}', rec), 200)
    check('اللي يعرف الرمز يقراه (بدون تسجيل)', requests.get(url(f'rk/{h}')).status_code, 200)
    check('ما يقدر يقرا قائمة الرموز', requests.get(url('rk', 'p2')).status_code, 401)
    check('غيره ما يكتب فوق رمزه', put('p2', f'rk/{h}', {**rec, 'u': 'p2'}), 401)
    check('غيره ما يمسح رمزه', requests.delete(url(f'rk/{h}', 'p2')).status_code, 401)
    check('ما يسوي رمز باسم غيره', put('p2', f'rk/{"c" * 64}', rec), 401)
    check('حقل زايد يرفض', put('p1', f'rk/{"e" * 64}', {**rec, 'z': 1}), 401)
    check('مسار مب hash يرفض', put('p1', 'rk/abc', rec), 401)
    check('بدون تسجيل ما يكتب', requests.put(url(f'rk/{"f" * 64}'), data=json.dumps(rec)).status_code, 401)
    check('صاحبه يحدّثه', put('p1', f'rk/{h}', {**rec, 'c': 'enc2'}), 200)
    check('صاحبه يمسحه (غيّر الرمز)', requests.delete(url(f'rk/{h}', 'p1')).status_code, 200)


def r_tests():
    now = int(time.time() * 1000)
    load_rules(now - DAY, []); reset({})
    print('\n— سجل نهاية اللعبة (رصد الكشّاف) —')
    TS = {'.sv': 'timestamp'}
    rec = {'d': 2, 'g': 0, 'dv': '0123456789ab', 't': TS}
    check('اللاعب يسجل نهاية لعبته', put('p1', 'r/2/easy/p1', rec), 200)
    check('ما يكتب مرة ثانية فوقها', put('p1', 'r/2/easy/p1', {**rec, 'g': 1}), 401)
    check('ما يسجل باسم غيره', put('p2', 'r/2/easy/p1', rec), 401)
    check('اللاعب نفسه ما يقرا السجل', requests.get(url('r/2/easy/p1', 'p1')).status_code, 401)
    check('أحد ثاني ما يقرا السجل', requests.get(url('r', 'p2')).status_code, 401)
    check('بدون تسجيل ما يقرا', requests.get(url('r')).status_code, 401)
    check('المدير يقرا السجل', requests.get(url('r', 'Vt7pBIwn9jhQCI2LSORFpnU3aCa2')).status_code, 200)
    check('بصمة بشكل غلط ترفض', put('p3', 'r/2/easy/p3', {**rec, 'dv': 'XYZ'}), 401)
    check('بصمة أطول ترفض', put('p3', 'r/2/easy/p3', {**rec, 'dv': 'a' * 40}), 401)
    check('يوم غير اليوم يرفض', put('p3', 'r/3/easy/p3', {**rec, 'd': 3}), 401)
    check('وقت من التلفون (مب السيرفر) يرفض', put('p3', 'r/2/easy/p3', {**rec, 't': now}), 401)
    check('محاولات أكثر من 6 ترفض', put('p3', 'r/2/easy/p3', {**rec, 'g': 7}), 401)
    check('تحدي غير معروف يرفض', put('p3', 'r/2/zzz/p3', rec), 401)
    check('حقل زايد يرفض', put('p3', 'r/2/pro/p3', {**rec, 'z': 1}), 401)
    check('تحدي الخبير يتسجل', put('p3', 'r/2/pro/p3', {**rec, 'g': 3}), 200)


def k5_tests():
    now = int(time.time() * 1000)
    ms = [{'id': '9201', 'wk': 1, 't': now + 3 * 3600000, 'h': 'ain', 'a': 'wahda', 'st': 1},
          {'id': '9202', 'wk': 1, 't': now - 3600000, 'h': 'wasl', 'a': 'nasr', 'st': 1},      # بدت قبل ساعة
          {'id': '9203', 'wk': 2, 't': now + 9 * DAY, 'h': 'ain', 'a': 'nasr', 'st': 1}]       # الجولة الجاية: ما انفتحت
    load_rules(now - DAY, ms)
    reset({'f': {'p1': {'c': 'ain', 't': 1}, 'p2': {'t': 1}, 'p9': {'c': 'ain', 't': 1}},
           'k5': {'1': {'p9': {'c': 'ain', 'cap': 2, 'w': 1, 'p': {'0': {'c': 'ain', 'k': 'g1'}, '1': {'c': 'ain', 'k': 'd1'},
                  '2': {'c': 'wasl', 'k': 'm1'}, '3': {'c': 'wahda', 'k': 'f1'}, '4': {'c': 'wahda', 'k': 'x1'}}}}}})
    print('\n— خماسي الفانتازي —')
    P = lambda *a: {str(i): {'c': c, 'k': k} for i, (c, k) in enumerate(a)}
    rec = {'c': 'ain', 'cap': 0, 'w': TS, 'p': P(('ain', 'g1'), ('ain', 'd1'), ('wahda', 'm1'), ('wahda', 'f1'), ('ain', 'x1'))}
    check('خماسي كامل قبل مباريات أنديته ينقبل', put('p1', 'k5/1/p1', rec), 200)
    check('تبديل لاعب ما بدت مباراته ينقبل', put('p1', 'k5/1/p1', {**rec, 'p': P(('ain', 'g1'), ('ain', 'd1'), ('wahda', 'm2'), ('wahda', 'f1'), ('ain', 'x1'))}), 200)
    check('لاعب من نادي بدت مباراته يرفض', put('p1', 'k5/1/p1', {**rec, 'p': P(('ain', 'g1'), ('ain', 'd1'), ('wasl', 'm1'), ('wahda', 'f1'), ('ain', 'x1'))}), 401)
    check('نادي مب في الجولة يرفض', put('p1', 'k5/1/p1', {**rec, 'p': P(('ain', 'g1'), ('ain', 'd1'), ('hatta', 'm1'), ('wahda', 'f1'), ('ain', 'x1'))}), 401)
    check('4 لاعبين بس يرفض', put('p1', 'k5/1/p1', {**rec, 'p': {k: v for k, v in rec['p'].items() if k != '4'}}), 401)
    check('القائد برا 0-4 يرفض', put('p1', 'k5/1/p1', {**rec, 'cap': 5}), 401)
    check('نادي غير نادي البطاقة يرفض', put('p1', 'k5/1/p1', {**rec, 'c': 'wahda'}), 401)
    check('اللي ما اختار نادي يلعب بدون نادي', put('p2', 'k5/1/p2', {**rec, 'c': 'none'}), 200)
    check('المسح يرفض', requests.delete(url('k5/1/p1', 'p1')).status_code, 401)
    check('الجولة اللي ما انفتحت ترفض', put('p1', 'k5/2/p1', rec), 401)
    check('ما يقرا خماسي غيره', requests.get(url('k5/1/p1', 'p2')).status_code, 401)
    # p9 عنده لاعب الوصل (بدت مباراته) في الخانة 2 وهو القائد
    old = get('k5/1/p9').json()
    old['p'] = {str(i): v for i, v in enumerate(old['p'])} if isinstance(old['p'], list) else old['p']
    keep = {**old, 'w': TS, 'p': {**old['p'], '3': {'c': 'wahda', 'k': 'f2'}}}
    check('تبديل خانة ثانية والمقفول على حاله ينقبل', put('p9', 'k5/1/p9', keep), 200)
    check('تبديل لاعب مباراته بدت يرفض', put('p9', 'k5/1/p9', {**keep, 'p': {**keep['p'], '2': {'c': 'wahda', 'k': 'm9'}}}), 401)
    check('تغيير القائد من لاعب بدت مباراته يرفض', put('p9', 'k5/1/p9', {**keep, 'cap': 0}), 401)
    k2 = {**keep, 'cap': 0}
    requests.patch(url('k5/1/p9'), data=json.dumps({'cap': 0}), headers=OWNER)
    check('القائد لاعب مباراته بدت يرفض', put('p9', 'k5/1/p9', {**k2, 'w': TS, 'cap': 2}), 401)
    check('تغيير القائد بين لاعبين ما بدوا ينقبل', put('p9', 'k5/1/p9', {**k2, 'w': TS, 'cap': 1}), 200)


def launch_tests():
    now = int(time.time() * 1000)
    ms = [{'id': '9301', 'wk': 1, 't': now + 3 * 3600000, 'h': 'ain', 'a': 'wahda', 'st': 1}]
    os.environ['LAUNCH5'] = str(now + DAY)      # الإطلاق بعدين: الجولة المفتوحة الحين بدونهم
    load_rules(now - DAY, ms); reset({'f': {'p1': {'c': 'ain', 't': 1}}})
    os.environ['LAUNCH5'] = '0'
    print('\n— قبل الإطلاق —')
    rec = {'c': 'ain', 'x': '~'.join(f'k{i}' for i in range(11)), 'w': TS}
    check('التشكيلة بدون هداف تنقبل', put('p1', 'tp/9301/p1', rec), 200)
    check('الهداف في جولة انفتحت قبل الإطلاق يرفض', put('p1', 'tp/9301/p1', {**rec, 's': 'k1'}), 401)
    P = lambda *a: {str(i): {'c': c, 'k': k} for i, (c, k) in enumerate(a)}
    check('الخماسي في جولة انفتحت قبل الإطلاق يرفض', put('p1', 'k5/1/p1', {'c': 'ain', 'cap': 0, 'w': TS, 'p': P(*[('ain', f'k{i}') for i in range(5)])}), 401)


if __name__ == '__main__':
    try:
        requests.get(f'{B}/.json?ns={NS}', timeout=3)
    except Exception:
        sys.exit('المحاكي مب شغال على ' + B)
    mano_tests(); predict_tests(); rate_tests(); fan_tests(); grid_tests(); tp_tests(); k5_tests(); launch_tests(); x_tests(); rk_tests(); r_tests()
    print(f'\nالنتيجة: {ok} نجح · {fail} فشل')
    sys.exit(1 if fail else 0)
