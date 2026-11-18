"""رصد الكشّاف: detect() يلقى النمط ويتجاهل الحالات البريئة."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'guard'))
from scan import detect

ok = fail = 0
def check(name, got, exp):
    global ok, fail
    good = got == exp
    ok += good; fail += not good
    print(('✓ ' if good else '✗ ') + name + ('' if good else f'  (طلع {got!r} والمفروض {exp!r})'))

M = 60000
r = {'3': {'easy': {
    'kash': {'g': 0, 'dv': 'aaaaaaaaaaaa', 't': 1000},            # خسر بحساب سفاري
    'main': {'g': 1, 'dv': 'aaaaaaaaaaaa', 't': 1000 + 5 * M},    # فاز من أول محاولة بعد 5 دقايق
    'late': {'g': 1, 'dv': 'aaaaaaaaaaaa', 't': 1000 + 90 * M},   # بعد ساعة ونص: ما ينحسب
    'other': {'g': 1, 'dv': 'bbbbbbbbbbbb', 't': 1000 + 2 * M},   # تلفون ثاني
    'before': {'g': 1, 'dv': 'cccccccccccc', 't': 500},           # فاز قبل الخسارة
    'lossc': {'g': 0, 'dv': 'cccccccccccc', 't': 900},
    'g4': {'g': 4, 'dv': 'aaaaaaaaaaaa', 't': 1000 + 3 * M},      # 4 محاولات: مب النمط
}}, '4': {'easy': {
    'k2': {'g': 0, 'dv': 'aaaaaaaaaaaa', 't': 9000},
    'main': {'g': 2, 'dv': 'aaaaaaaaaaaa', 't': 9000 + 10 * M},
}, 'pro': {'solo': {'g': 0, 'dv': 'dddddddddddd', 't': 1}}}}
cases, per = detect(r)
check('حالتين بس', len(cases), 2)
check('الفايز هو الحساب الأساسي', {c['win'] for c in cases}, {'main'})
check('الخاسر حساب الكشف', [c['loss'] for c in cases], ['kash', 'k2'])
check('الفرق بالدقايق', cases[0]['gap'], 5.0)
check('تكرر يومين', per, {'main': 2})
check('عدد الحسابات بنفس البصمة', cases[0]['same_dv'], 4)
check('بيانات فاضية', detect({}), ([], {}))
print(f'\nالنتيجة: {ok} نجح · {fail} فشل')
sys.exit(1 if fail else 0)
