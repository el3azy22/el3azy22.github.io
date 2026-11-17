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


if __name__ == '__main__':
    try:
        requests.get(f'{B}/.json?ns={NS}', timeout=3)
    except Exception:
        sys.exit('المحاكي مب شغال على ' + B)
    mano_tests(); predict_tests(); rate_tests(); fan_tests()
    print(f'\nالنتيجة: {ok} نجح · {fail} فشل')
    sys.exit(1 if fail else 0)
