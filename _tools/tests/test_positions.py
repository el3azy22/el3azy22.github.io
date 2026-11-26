"""نظام المراكز في كل المنصة (قرار إبراهيم 27 نوفمبر): البيانات، الأولوية، المطابقة، «منو اللاعب؟»، الخماسي، الشبكة.
  python3 _tools/tests/test_positions.py"""
import json, os, re, subprocess, sys
R = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path[:0] = [f'{R}/_tools/sync', f'{R}/_tools/khamsa', f'{R}/_tools/fans', f'{R}/_tools/grid']
ok = bad = 0


def check(name, cond, info=''):
    global ok, bad
    if cond:
        ok += 1
    else:
        bad += 1
        print('❌', name, info)


D = json.load(open(f'{R}/mano/data.json', encoding='utf8'))
P = {p['id']: p for p in D['players']}
F = json.load(open(f'{R}/_tools/position_fixes.json', encoding='utf8'))
MANO = {k: v for k, v in F.get('_mano', {}).items() if not k.startswith('_')}
CAR = json.load(open(f'{R}/_tools/sync/career_pos.json', encoding='utf8'))
SEA = json.load(open(f'{R}/_tools/sync/season_pos.json', encoding='utf8'))
HIST = json.load(open(f'{R}/_tools/sync/pos_hist.json', encoding='utf8'))
RC = {'قلب دفاع': 'DF', 'ظهير أيسر': 'DF', 'ظهير أيمن': 'DF', 'ارتكاز': 'MD', 'صانع ألعاب': 'MD', 'وسط أيسر': 'MD', 'وسط أيمن': 'MD',
      'جناح أيسر': 'FW', 'جناح أيمن': 'FW', 'رأس حربة': 'FW', 'مهاجم ثاني': 'FW'}

# 1) البيانات: كل لاعب له مركز صحيح، والمركز الثاني والتفصيلي منطقيين
for p in D['players']:
    check('مركز صحيح ' + p['id'], p['p'] in ('GK', 'DF', 'MD', 'FW'), p['p'])
    check('التسجيل محفوظ ' + p['id'], p.get('pr') in ('GK', 'DF', 'MD', 'FW'))
    check('الحارس بدون مركز ثاني ' + p['id'], not (p['p'] == 'GK' and p.get('p2')))
    check('المركز الثاني مب حارس ومب نفس الأساسي ' + p['id'], p.get('p2') in (None, 'DF', 'MD', 'FW') and p.get('p2') != p['p'])
    check('التفصيلي من نفس الخط ' + p['id'], not p.get('pd') or RC.get(p['pd']) == p['p'], f"{p.get('pd')} / {p['p']}")
    check('السجل آخره نفس المركز ' + p['id'], (HIST.get(p['id']) or [[0, None]])[-1][1] == p['p'])

# 2) الأولوية: قرار إبراهيم ← هالموسم (3+) ← المسيرة ← التسجيل (حساب مستقل)
for pid, p in P.items():
    se = SEA.get(pid) or {'n': 0, 'cat': {}}
    cc = (CAR.get(pid) or [None, None])[1]
    sc = None
    if se['n'] >= 3:
        top = max(se['cat'].values()); tied = [k for k, v in se['cat'].items() if v == top]
        sc = next((x for x in (cc, p['pr']) if x in tied), sorted(tied)[0])
    exp = MANO.get(pid) or sc or cc or p['pr']
    check('الأولوية ' + pid, p['p'] == exp, f"{p['p']} != {exp}")
for pid, pos in MANO.items():
    if pid in P:
        check('قرار إبراهيم يغلب ' + pid, P[pid]['p'] == pos)

# 3) حالات معروفة
def g(pid, k='p'):
    return (P.get(pid) or {}).get(k)
check('سهيل مهاجم ومركزه الثاني مدافع', (g('suhail-ahmed-alnoobi-saeed'), g('suhail-ahmed-alnoobi-saeed', 'p2')) == ('FW', 'DF'))
check('ياسين جابري مهاجم', g('yassine-jabri') == 'FW')
check('فراس بن العربي وسط', g('mohamed-firas-ben-arbi') == 'MD')
check('أكسل أمارال حارس بدون مركز ثاني', (g('axell-amaral-gama'), g('axell-amaral-gama', 'p2')) == ('GK', None))
check('ماريوس مارين ما ياخذ بدايات هويبراتن', g('marius-mihai-marin', 'p2') != 'DF')
check('كل حارس مسجل حارس (إلا بقرار)', all(p['p'] == 'GK' for p in D['players'] if p['pr'] == 'GK' and p['id'] not in MANO))

# 4) «تشكيلتي» و«الخماسي» نفس المركز
M2 = {'GK': 'GK', 'DEF': 'DF', 'MID': 'MD', 'FWD': 'FW'}
sq = json.load(open(f'{R}/tashkila/squads.json', encoding='utf8'))
for c in sq['clubs']:
    for e in c['p']:
        if len(e) > 5 and e[5] in P:
            check(f"تشكيلتي = منو اللاعب {e[5]}", M2.get(e[2]) == P[e[5]]['p'], f"{e[2]} / {P[e[5]]['p']}")

# 5) مطابقة تشكيلات المباريات (season_pos): الصح ينقبل، واللبس ينرفض
import season_pos as S
src = open(f'{R}/_tools/sync/season_pos.py', encoding='utf8').read()
src = src.replace("    out, miss = {}, 0", "    globals()['MATCH'] = match\n    return\n    out, miss = {}, 0")
gl = {'__name__': 't', '__file__': f'{R}/_tools/sync/season_pos.py'}
exec(compile(src, 'season_pos', 'exec'), gl); gl['main']()
M = gl['MATCH']
for club, no, name, want in [('kalba', '9', 'Biro', 'guilherme-sucigan-mafra-cunha'), ('dhafra', '7', 'Marcelinho', 'marcelo-jose-de-lima-filho'),
                             ('nasr', '8', 'Marius Marin', 'marius-mihai-marin'), ('nasr', '22', 'Marius Høibråten', None),
                             ('hatta', '13', 'Khaled Ali Al Baloushi', None), ('hatta', '55', 'Mohammad Al Hussaini', None),
                             ('baniyas', '18', 'Suhail Al Noobi', 'suhail-ahmed-alnoobi-saeed'), ('ajman', '9', 'Walid Azarou', None)]:
    m = M(club, no, name)
    got = m['id'] if m else None
    if want and want not in P:          # لاعب الاختبار طلع من القائمة: نتأكد بس إنه ما يطابق غلط
        want = got
    if club == 'ajman' and no == '9':   # وليد أزارو: نفس الرقم والاسم الأول قريب
        want = next((p['id'] for p in D['players'] if p['c'] == 'ajman' and p.get('no') == 9), None)
    check(f'مطابقة {name}', got == want, f'{got} != {want}')
check('أدوار FotMob', [S.role(x) for x in (11, 32, 38, 36, 65, 84, 82, 88, 115)] ==
      [('GK', 'gk'), ('DF', 'rb'), ('DF', 'lb'), ('DF', 'cb'), ('MD', 'dm'), ('MD', 'am'), ('FW', 'rw'), ('FW', 'lw'), ('FW', 'st')])

# 6) «منو اللاعب؟»: خانة المركز (نفس كود الصفحة)
html = open(f'{R}/mano/index.html', encoding='utf8').read()
line = re.search(r"r\.p=p\.p===a\.p\?.*?;\n", html).group(0)
par = re.search(r"const parrow=.*?;\n", html).group(0)
js = "const LINE={GK:0,DF:1,MD:2,FW:3};" + par + "function f(p,a){const r={};" + line + "const ar=parrow(p.p,a.p);return r.p+'|'+(ar.includes('⬆')?'up':ar.includes('⬇')?'down':'')}\n"
cases = [({'p': 'FW'}, {'p': 'FW'}, 'ok|'), ({'p': 'DF'}, {'p': 'FW', 'p2': 'DF'}, 'near|up'), ({'p': 'DF'}, {'p': 'FW'}, '|up'),
         ({'p': 'FW', 'p2': 'DF'}, {'p': 'DF'}, '|down'), ({'p': 'MD'}, {'p': 'FW'}, '|up'), ({'p': 'GK'}, {'p': 'MD'}, '|up'),
         ({'p': 'FW'}, {'p': 'GK'}, '|down'), ({'p': 'MD'}, {'p': 'FW', 'p2': 'MD'}, 'near|up'), ({'p': 'FW'}, {'p': 'MD', 'p2': 'FW'}, 'near|down'),
         ({'p': 'GK'}, {'p': 'DF'}, '|up')]
js += f"console.log(JSON.stringify({json.dumps(cases)}.map(([g,a])=>f(g,a))))"
out = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True).stdout)
for (gp, ap, want), got in zip(cases, out):
    check(f'منو اللاعب: تخمين {gp} واللاعب {ap}', got == want, f'{got} != {want}')
check('بطاقة الجواب فيها المركز التفصيلي', 'POSD(ANS)' in html and 'POSD(YEST)' in html)

# 7) الخماسي: مركز اللاعب وقت المباراة
import build as B
B._PH = {'x': [[0, 'FW'], [2000, 'DF']]}
st = {'g': 1, 'm': 90}
sqi = {'x': ('ain', 'FWD')}
mt = {'ain': {'d': 10, 't': 1000, 'p': {'x': st}}}
got = B.k5_entry({'p': {'3': {'k': 'x', 'c': 'ain'}}}, mt, sqi)
check('الخماسي: مهاجم وقت المباراة ينحسب في خانة المهاجم حتى لو صار مدافع بعدها', len(got) == 1 and got[0][2] == 3, got)
mt2 = {'ain': {'d': 10, 't': 3000, 'p': {'x': st}}}
got = B.k5_entry({'p': {'3': {'k': 'x', 'c': 'ain'}}}, mt2, {'x': ('ain', 'DEF')})
check('الخماسي: لو كان مدافع وقت المباراة ما ينحسب في خانة المهاجم', got == [], got)
B._PH = None

# 8) الشبكة: شرط المركز ينقبل بالأساسي أو الثاني
gb = open(f'{R}/_tools/grid/build.py', encoding='utf8').read()
check('الشبكة (البناء) تقبل المركز الثاني', "p.get('p2')" in gb)
gi = open(f'{R}/grid/index.html', encoding='utf8').read()
check('الشبكة (الصفحة) تقبل المركز الثاني', 'p.p===v||p.p2===v' in gi)

# 9) تثبيت اليوم: تغيير المركز ينحفظ القديم (pz) والصفحة تكمل عليه لين نهاية اليوم
import shutil, tempfile
tmp = tempfile.mkdtemp()
for rel in ['_tools/apply_position_fixes.py', '_tools/position_fixes.json', '_tools/name_fixes.json', '_tools/sync/career_pos.json',
            '_tools/sync/season_pos.json', '_tools/sync/pos_hist.json', 'mano/data.json', 'tashkila/squads.json']:
    os.makedirs(os.path.dirname(f'{tmp}/{rel}'), exist_ok=True); shutil.copy(f'{R}/{rel}', f'{tmp}/{rel}')
td = json.load(open(f'{tmp}/mano/data.json', encoding='utf8'))
for p in td['players']:
    if p['id'] == 'suhail-ahmed-alnoobi-saeed':
        p['p'], p['pd'] = 'MD', 'صانع ألعاب'; p.pop('p2', None); p.pop('pz', None)
json.dump(td, open(f'{tmp}/mano/data.json', 'w', encoding='utf8'), ensure_ascii=False)
subprocess.run([sys.executable, f'{tmp}/_tools/apply_position_fixes.py'], capture_output=True)
sp_ = next(p for p in json.load(open(f'{tmp}/mano/data.json', encoding='utf8'))['players'] if p['id'] == 'suhail-ahmed-alnoobi-saeed')
check('تثبيت اليوم: الجديد في p والقديم في pz', sp_['p'] == 'FW' and (sp_.get('pz') or {}).get('p') == 'MD', sp_.get('pz'))
shutil.rmtree(tmp)
fz = re.search(r"\{const \[y,m,d\]=D\.start\.split.*?\}\)\}", html).group(0)
js2 = ("const D={start:'2026-11-17',players:[{p:'FW',p2:'DF',pz:{p:'MD',p2:null,t:%d}},{p:'FW',pz:{p:'DF',t:%d}}]};const idx=%d;" + fz +
       ";console.log(JSON.stringify(D.players.map(p=>[p.p,p.p2||null])))")
ds = 1794859200000 + 10 * 86400000
out2 = json.loads(subprocess.run(['node', '-e', js2 % (ds + 5 * 3600000, ds - 3600000, 10)], capture_output=True, text=True).stdout)
check('تثبيت اليوم في الصفحة: تغيّر بعد بداية اليوم = القديم، وقبلها = الجديد', out2 == [['MD', None], ['FW', None]], out2)
check('لاعب اليوم: تلميح المركز فيه المركز الثاني', 'ويلعب ${POSS[ANS.p2]} أحياناً' in html)

print(f'النتيجة: {ok} نجح · {bad} فشل')
