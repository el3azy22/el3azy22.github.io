"""اختبار قواعد «علم الاتحاد» (alam/) على المحاكي (منفذ 9000).
التشغيل: المحاكي شغال ثم  python3 _tools/tests/test_alam.py"""
import base64, json, os, subprocess, sys, tempfile, shutil, time, threading
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
B = os.environ.get('EMU', 'http://127.0.0.1:9000'); NS = 'demo-el3'
OWNER = {'Authorization': 'Bearer owner'}
S = requests.Session(); S.trust_env = False
ok = fail = 0


def tok(u):
    e = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b'=').decode()
    n = int(time.time())
    return e({'alg': 'none', 'typ': 'JWT'}) + '.' + e({'sub': u, 'user_id': u, 'iat': n, 'exp': n + 3600, 'aud': NS,
        'iss': 'https://securetoken.google.com/' + NS, 'auth_time': n, 'firebase': {'sign_in_provider': 'anonymous'}}) + '.'


def url(path, u=None): return f'{B}/{path}.json?ns={NS}' + (f'&auth={tok(u)}' if u else '')
def check(name, got, want):
    global ok, fail
    g = got == want; ok += g; fail += (not g)
    print(('✅' if g else '❌'), name, '→', got, '' if g else f'(المتوقع {want})')


inc = {'.sv': {'increment': 1}}; TS = {'.sv': 'timestamp'}
def body(u, e='ad', m=0, c=None, extra=None):
    b = {f'alam/g/{u}': {'e': e, 'm': m, 't': TS, **({'c': c} if c else {})}, 'alam/t/n': inc, f'alam/t/e/{e}': inc}
    if c: b[f'alam/t/c/{c}'] = inc
    if extra: b.update(extra)
    return b
def patch(u, b): return S.patch(url('', u), data=json.dumps(b))
def get(p): return S.get(url(p), headers=OWNER).json()

# القواعد
d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, '_tools', 'firebase')); os.makedirs(os.path.join(d, 'predict'))
shutil.copy(os.path.join(ROOT, '_tools', 'firebase', 'make_rules.py'), os.path.join(d, '_tools', 'firebase'))
json.dump({'matches': []}, open(os.path.join(d, 'predict', 'data.json'), 'w'))
subprocess.run([sys.executable, 'make_rules.py'], cwd=os.path.join(d, '_tools', 'firebase'), check=True)
r = S.put(f'{B}/.settings/rules.json?ns={NS}', data=open(os.path.join(d, '_tools', 'firebase', 'rules.json')).read(), headers=OWNER)
assert r.status_code == 200, r.text
S.put(url(''), data='{}', headers=OWNER)

r = patch('u1', body('u1', 'ad', 3, 'ain')); check('بصمة صحيحة مع نادي', r.status_code, 200)
check('بصمة ثانية من نفس الجهاز مرفوضة', patch('u1', body('u1', 'dxb', 1)).status_code, 401)
check('بصمة بدون نادي', patch('u2', body('u2', 'rak', 5)).status_code, 200)
check('إمارة غلط', patch('u3', body('u3', 'xx', 1)).status_code, 401)
check('رسالة برا القائمة', patch('u3', body('u3', 'ad', 12)).status_code, 401)
check('نص حر بدل رقم الرسالة', patch('u3', body('u3', 'ad', 'كلام')).status_code, 401)
check('نادي غلط', patch('u3', body('u3', 'ad', 1, 'barca')).status_code, 401)
b = body('u3', 'ad', 1); del b['alam/t/n']; check('بدون زيادة العدد الكلي', patch('u3', b).status_code, 401)
b = body('u3', 'ad', 1); b['alam/t/e/dxb'] = inc; check('زيادة إمارة ثانية', patch('u3', b).status_code, 401)
b = body('u3', 'ad', 1); b['alam/t/n'] = 50; check('العدد قفز', patch('u3', b).status_code, 401)
b = body('u3', 'ad', 1, 'wasl'); del b['alam/t/c/wasl']; check('نادي بدون عداده', patch('u3', b).status_code, 401)
check('بصمة باسم جهاز ثاني', patch('u3', {**body('u4', 'ad', 1)}).status_code, 401)
check('عداد بروحه بدون بصمة', patch('u5', {'alam/t/n': inc}).status_code, 401)
check('حقل زايد (اسم)', patch('u3', {**body('u3'), 'alam/g/u3': {'e': 'ad', 'm': 1, 't': TS, 'n': 'x'}}).status_code, 401)
check('مسح بصمة', S.delete(url('alam/g/u1', 'u1')).status_code, 401)
check('قراءة العدادات بدون تسجيل', S.get(url('alam/t')).status_code, 200)
check('قراءة البصمات بالترتيب', S.get(url('alam/g') + '&orderBy="t"&limitToLast=2').status_code, 200)
check('ما يقدر يقرا باقي المنصة', S.get(url('f')).status_code, 401)

# 20 بصمة مع بعض: كلها تنحفظ والعداد مضبوط
res = []
def go(i):
    for _ in range(8):
        r = patch(f'p{i}', body(f'p{i}', ['ad', 'dxb', 'shj'][i % 3], i % 12))
        if r.ok: res.append(1); return
        time.sleep(0.05)
ts = [threading.Thread(target=go, args=(i,)) for i in range(20)]; [t.start() for t in ts]; [t.join() for t in ts]
t = get('alam/t'); g = get('alam/g')
check('20 بصمة متزامنة انحفظت', len(res), 20)
check('العدد الكلي = عدد البصمات', t['n'], len(g))
check('مجموع الإمارات = العدد الكلي', sum(t['e'].values()), t['n'])

# الاسم (اختياري)
check('بصمة مع اسم عربي', patch('n1', {**body('n1', 'ad', 1), 'alam/g/n1': {'e': 'ad', 'm': 1, 't': TS, 'n': 'العازي'}}).status_code, 200)
check('اسم فيه أرقام أو رابط', patch('n2', {**body('n2', 'ad', 1), 'alam/g/n2': {'e': 'ad', 'm': 1, 't': TS, 'n': 'www.x.com'}}).status_code, 401)
check('اسم طويل', patch('n2', {**body('n2', 'ad', 1), 'alam/g/n2': {'e': 'ad', 'm': 1, 't': TS, 'n': 'ا' * 19}}).status_code, 401)
check('إضافة الاسم بعدين لبصمة بدون اسم', S.put(url('alam/g/u2/n', 'u2'), data=json.dumps('بوخالد')).status_code, 200)
check('تغيير الاسم بعد ما انكتب', S.put(url('alam/g/u2/n', 'u2'), data=json.dumps('ثاني')).status_code, 401)
check('اسم على بصمة غيري', S.put(url('alam/g/p1/n', 'u2'), data=json.dumps('ثاني')).status_code, 401)
check('تغيير الإمارة بعدين', S.put(url('alam/g/u2/e', 'u2'), data=json.dumps('dxb')).status_code, 401)
ADMIN = 'Vt7pBIwn9jhQCI2LSORFpnU3aCa2'
check('المدير يمسح اسم', S.delete(url('alam/g/n1/n', ADMIN)).status_code, 200)
check('العدد ما تغير بعد الأسماء', get('alam/t')['n'], len(get('alam/g')))
print(f'النتيجة: {ok} نجح · {fail} فشل')
