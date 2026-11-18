"""«باص الفريق» في دوري الجماهير («تحدي الجولة»: يوم مباراة نادي المشجع، محاولة وحدة): قواعد b على المحاكي +
المُعيد (verify.py) يطلع نفس نتيجة السباق من الحركات، ويرفض غير ملعب المباراة أو يوم بدون مباراة + النقاط (★3 ★★6 ★★★9).
يحتاج المحاكي + Chrome.   python3 _tools/tests/test_bus.py"""
import json, os, shutil, subprocess, sys, time
import requests
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bus'))
import test_rules as T
import verify as V
from playwright.sync_api import sync_playwright

DAY = 86400000
now = int(time.time() * 1000)
mid = (now + 4 * 3600000) // DAY * DAY - 4 * 3600000
L = mid - 2 * DAY          # اليوم 3 شغال (في القواعد)
TS = {'.sv': 'timestamp'}


# المُعيد في الاختبار: نفس verify.py، بس صفحته ما تطلع برا الجهاز (قاعدة 11: الاختبارات ما تلمس Firebase الحقيقي)
_BLOCK = """import runpy, sys
from playwright.sync_api._generated import Browser
_np = Browser.new_page
def _h(r):
    return r.continue_() if r.request.url.startswith(('http://127.0.0.1', 'http://localhost', 'data:', 'blob:')) else r.abort()
def _new(self, *a, **k):
    pg = _np(self, *a, **k); pg.route('**/*', _h); return pg
Browser.new_page = _new
runpy.run_path(sys.argv[1], run_name='__main__')"""
VERIFY = [sys.executable, '-c', _BLOCK, os.path.join(T.ROOT, '_tools', 'bus', 'verify.py')]


def body(d, k='0:10', s='ain', r='ain_A', c='ain', m='777'):
    return {'m': m, 's': s, 'r': r, 'k': k, 'c': c, 'd': d, 't': TS}


def recording(dnum):
    """سباق حقيقي بالسواق الآلي على مرحلة يوم dnum ⇒ (الطريق، الحركات، النتيجة)."""
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8798', '--bind', '127.0.0.1'], cwd=T.ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path='/usr/bin/google-chrome'); pg = b.new_page()
            pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') and not r.request.url.endswith('.mp3') else r.abort())
            pg.goto('http://127.0.0.1:8798/bus/#qa'); pg.wait_for_function('window.__bus && __bus.routes().length > 0')
            if not pg.evaluate("'STAR3' in __bus"):
                b.close(); return None
            o = pg.evaluate("""([day, dnum]) => {const B=__bus;const st='ain';
              B.day=day;B.setRoute(st+'_A');const a=B.autosim(true);const rec=B.rec.slice();const s=B.sim(rec);return {r:st+'_A',rec,a,nP:s.np,other:'wasl',enc:B.encK?B.encK(rec):null}}""", [V.ymd(dnum), dnum])
            b.close()
        return o
    finally:
        srv.terminate()


if __name__ == '__main__':
    T.load_rules(L, []); T.reset({'f': {'u1': {'c': 'ain', 't': 1}, 'u2': {'c': 'wasl', 't': 1}, 'u4': {'c': 'none', 't': 1}}})
    print('— باص الفريق: القواعد —')
    T.check('سباق التحدي ينقبل', T.put('u1', 'b/3/u1', body(3)), 200)
    T.check('محاولة ثانية ترفض (محاولة وحدة)', T.put('u1', 'b/3/u1', body(3)), 401)
    T.check('سباق يوم أمس يرفض', T.put('u2', 'b/2/u2', body(2, c='wasl')), 401)
    T.check('نادي غير نادي بطاقة المشجع يرفض', T.put('u2', 'b/3/u2', body(3, c='ain')), 401)
    T.check('اللي ما اختار نادي ما يدخل التحدي', T.put('u4', 'b/3/u4', body(3, c='')), 401)
    T.check('سباق في سجل غيرك يرفض', T.put('u3', 'b/3/u2', body(3, c='wasl')), 401)
    T.check('المشجع ما يكتب النتيجة بنفسه', T.put('u1', 'bv/3/u1', {'ok': 1, 'rt': 3}), 401)
    T.check('حركات بصيغة غلط ترفض', T.put('u2', 'b/3/u2', body(3, k='<script>', c='wasl')), 401)

    print('\n— باص الفريق: المُعيد —')
    o = recording(3)
    T.check('اللعبة فيها اللي يحتاجه المُعيد (STAR3 و np في sim)', o is not None, True)
    if o: T.check('الصفحة تضغط الحركات بنفس صيغة المُعيد', o['enc'], V.encode(o['rec']))
    fix = os.path.join(T.ROOT, '_tools', 'tests', '_bus_fix.json')
    json.dump({'matches': [{'id': '777', 'wk': 9, 't': V.START + 2 * DAY + 20 * 3600000, 'h': 'ain', 'a': 'wasl'}]}, open(fix, 'w'))
    rk = lambda: V.encode(o['rec'])
    if o: T.reset({'b': {'3': {'ua': {**body(3, k=rk()), 't': 5000},                                   # العين في ملعبه ✓
                               'ub': {**body(3, k=rk(), c='wasl'), 't': 5000},                         # الوصل الضيف: ملعب العين ✓
                               'uc': {**body(3, k=rk(), s='wasl', r='wasl_A', c='wasl'), 't': 5000},   # ملعب غلط ✗
                               'ud': {**body(3, k=rk(), c='nasr', s='nasr', r='nasr_A'), 't': 5000}}}})   # نادي ما عنده مباراة ✗
    if o:
        env = {**os.environ, 'FBDB': T.B, 'FBNS': T.NS, 'TOKEN': 'owner', 'NOW': str(V.START + 2 * DAY + 3600000), 'BUS_FIX': fix}
        r = subprocess.run(VERIFY, env=env, capture_output=True, text=True)
        T.check('المُعيد اشتغل', r.returncode, 0)
        bv = requests.get(T.url('bv/3'), headers=T.OWNER).json() or {}
        a = bv.get('ua')
        T.check('الإعادة تطلع نفس الاصطدامات والكور والمخالفات', (a or {}).get('cr'), o['a']['crashes'])
        T.check('الإعادة: نفس الكور الذهبية', (a or {}).get('st'), o['a']['stars'])
        T.check('الإعادة: نفس اللاعبين اللي ركبوا', (a or {}).get('np'), o['nP'])
        T.check('مشجع الضيف يسوق لنفس الملعب وينقبل', (bv.get('ub') or {}).get('ok'), 1)
        T.check('ملعب غير ملعب المباراة يرفض', (bv.get('uc') or {}).get('ok'), 0)
        T.check('نادي ما عنده مباراة هاليوم يرفض', (bv.get('ud') or {}).get('ok'), 0)
        r2 = subprocess.run(VERIFY, env=env, capture_output=True, text=True)
        T.check('مرة ثانية: ما يعيد اللي انعاد', 'ما في سباقات' in r2.stdout, True)

    if os.path.exists(fix):
        os.remove(fix)
    print('\n— باص الفريق: النقاط في الدوري —')
    sys.path.insert(0, os.path.join(T.ROOT, '_tools', 'fans'))
    os.environ['BUS_START'] = '1'
    import importlib, build as FB
    importlib.reload(FB)
    bv_all = {'3': {'uX': {'ok': 1, 'rt': 3, 'sc': 2100, 'cr': 1, 'sec': 62, 'c': 'ain', 't': 2},
                    'uZ': {'ok': 0, 'rt': 3, 'sc': 9999, 'c': 'ain'},
                    'uY': {'ok': 1, 'rt': 0, 'sc': 0, 'cr': 9, 'sec': 80, 'c': 'wasl', 't': 1}}}
    U = FB.collect_bus(bv_all, 1, 7)
    T.check('★★★ = 9 نقاط، والأخطاء = الاصطدامات', (U['uX']['pts'], U['uX']['mis'], U['uX']['plays']), (9, 1, 1))
    T.check('السباق المرفوض في الإعادة ما ينحسب', 'uZ' in U, False)
    T.check('ما وصل قبل الصافرة = 0 نقاط بس يوم لعب', (U['uY']['pts'], U['uY']['plays']), (0, 1))
    T.check('اللوحة تنضاف للدوري', [c['id'] for c in FB.CHALLENGES][-1], 'bus')
    print(f'\nالنتيجة: {T.ok} نجح · {T.fail} فشل')
    sys.exit(1 if T.fail else 0)
