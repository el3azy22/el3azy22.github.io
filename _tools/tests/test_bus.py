"""«باص الفريق» في دوري الجماهير: قواعد b على المحاكي + المُعيد (verify.py) يطلع نفس نتيجة السباق من الحركات،
ويرفض مرحلة غير مرحلة اليوم + حسبة النقاط في الدوري (★ 3 · ★★ 6 · ★★★ 9، أفضل سباق).
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


def body(d, k='0:10', s='ain', r='ain_A', c='ain'):
    return {'s': s, 'r': r, 'k': k, 'c': c, 'd': d, 't': TS}


def recording(dnum):
    """سباق حقيقي بالسواق الآلي على مرحلة يوم dnum ⇒ (الطريق، الحركات، النتيجة)."""
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8798', '--bind', '127.0.0.1'], cwd=T.ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path='/usr/bin/google-chrome'); pg = b.new_page()
            pg.route('**/*.mp3', lambda r: r.abort())
            pg.goto('http://127.0.0.1:8798/bus/#qa'); pg.wait_for_function('window.__bus && __bus.routes().length > 0')
            if not pg.evaluate("typeof __bus.daily === 'function' && 'STAR3' in __bus"):
                b.close(); return None
            o = pg.evaluate("""([day, dnum]) => {const B=__bus;const st=B.daily(Math.floor((%d+4*3600e3)/864e5)+dnum-1);
              B.day=day;B.setRoute(st+'_A');const a=B.autosim(true);const rec=B.rec.slice();const s=B.sim(rec);return {r:st+'_A',rec,a,nP:s.np,other:B.routes().map(x=>x.split('_')[0]).find(x=>x!==st&&x!=='test')}}""" % V.START, [V.ymd(dnum), dnum])
            b.close()
        return o
    finally:
        srv.terminate()


if __name__ == '__main__':
    T.load_rules(L, []); T.reset()
    print('— باص الفريق: القواعد —')
    T.check('السباق 1 ينقبل', T.put('u1', 'b/3/u1/1', body(3)), 200)
    T.check('نفس السباق مرة ثانية يرفض', T.put('u1', 'b/3/u1/1', body(3)), 401)
    T.check('السباق 3 قبل 2 يرفض', T.put('u1', 'b/3/u1/3', body(3)), 401)
    T.check('السباق 2 ينقبل', T.put('u1', 'b/3/u1/2', body(3)), 200)
    T.check('السباق 3 ينقبل', T.put('u1', 'b/3/u1/3', body(3)), 200)
    T.check('السباق 4 يرفض (3 بس)', T.put('u1', 'b/3/u1/4', body(3)), 401)
    T.check('سباق يوم أمس يرفض', T.put('u2', 'b/2/u2/1', body(2)), 401)
    T.check('سباق في سجل غيرك يرفض', T.put('u3', 'b/3/u2/1', body(3)), 401)
    T.check('المشجع ما يكتب النتيجة بنفسه', T.put('u1', 'bv/3/u1/1', {'ok': 1, 'rt': 3}), 401)
    T.check('حركات بصيغة غلط ترفض', T.put('u2', 'b/3/u2/1', body(3, k='<script>')), 401)

    print('\n— باص الفريق: المُعيد —')
    o = recording(3)
    if o is None:
        print('⏳ المُعيد ينتظر سطرين في اللعبة (__bus.daily و np في sim) — ينضافون بعد ما تخلص جلسة اختبار اللعبة')
    if o: T.reset({'b': {'3': {'ua': {'1': {**body(3, k=V.encode(o['rec']), s=o['r'].split('_')[0], r=o['r']), 't': L + 2 * DAY + 5000}},
                         'ub': {'1': {**body(3, k=V.encode(o['rec']), s=o['other'], r=o['other'] + '_A'), 't': L + 2 * DAY + 6000}}}}})
    if o:
        env = {**os.environ, 'FBDB': T.B, 'FBNS': T.NS, 'TOKEN': 'owner', 'NOW': str(V.START + 2 * DAY + 3600000)}
        r = subprocess.run([sys.executable, os.path.join(T.ROOT, '_tools/bus/verify.py')], env=env, capture_output=True, text=True)
        T.check('المُعيد اشتغل', r.returncode, 0)
        bv = requests.get(T.url('bv/3'), headers=T.OWNER).json() or {}
        a = (bv.get('ua') or {})
        a = a.get('1') if isinstance(a, dict) else a[1]
        T.check('الإعادة تطلع نفس الاصطدامات والكور والمخالفات', (a or {}).get('cr'), o['a']['crashes'])
        T.check('الإعادة: نفس الكور الذهبية', (a or {}).get('st'), o['a']['stars'])
        T.check('الإعادة: نفس اللاعبين اللي ركبوا', (a or {}).get('np'), o['nP'])
        b = (bv.get('ub') or {})
        b = b.get('1') if isinstance(b, dict) else b[1]
        T.check('مرحلة غير مرحلة اليوم ترفض', (b or {}).get('ok'), 0)
        r2 = subprocess.run([sys.executable, os.path.join(T.ROOT, '_tools/bus/verify.py')], env=env, capture_output=True, text=True)
        T.check('مرة ثانية: ما يعيد اللي انعاد', 'ما في سباقات' in r2.stdout, True)

    print('\n— باص الفريق: النقاط في الدوري —')
    sys.path.insert(0, os.path.join(T.ROOT, '_tools', 'fans'))
    os.environ['BUS_START'] = '1'
    import importlib, build as FB
    importlib.reload(FB)
    bv_all = {'3': {'uX': {'1': {'ok': 1, 'rt': 1, 'sc': 900, 'cr': 4, 'sec': 70, 'c': 'ain', 't': 1},
                           '2': {'ok': 1, 'rt': 3, 'sc': 2100, 'cr': 0, 'sec': 62, 'c': 'ain', 't': 2},
                           '3': {'ok': 0, 'rt': 3, 'sc': 9999}},
                    'uY': [None, {'ok': 1, 'rt': 0, 'sc': 0, 'cr': 9, 'sec': 80, 'c': 'wasl', 't': 1}]}}
    U = FB.collect_bus(bv_all, 1, 7)
    T.check('أفضل سباق: ★★★ = 9 نقاط، والأخطاء من نفس السباق', (U['uX']['pts'], U['uX']['mis'], U['uX']['plays']), (9, 0, 1))
    T.check('السباق المرفوض في الإعادة ما ينحسب حتى لو نتيجته أعلى', U['uX']['pts'], 9)
    T.check('ما وصل قبل الصافرة = 0 نقاط بس يوم لعب', (U['uY']['pts'], U['uY']['plays']), (0, 1))
    T.check('اللوحة تنضاف للدوري', [c['id'] for c in FB.CHALLENGES][-1], 'bus')
    print(f'\nالنتيجة: {T.ok} نجح · {T.fail} فشل')
    sys.exit(1 if T.fail else 0)
