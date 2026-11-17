"""جدول «لاعب اليوم» في Firebase (q/<يوم> = رقم اللاعب)، مب في ملفات الموقع العامة.
القواعد تخلي كل يوم يتقرى بس من 12 بالليل حقه، والكتابة لحساب الخدمة (FIREBASE_SA) بس.

  python3 _tools/mano/sched.py push   # مرة وحدة: ياخذ الجدول من mano/data.json، يعيد ترتيب الأيام الياية
                                      # (الجدول القديم مكشوف في تاريخ git)، يكتبه في q، ويشيله من data.json
تحدي الخبير صار لاعب عشوائي لكل مشجع (من نفس مستوى الصعوبة)، فـ schedule_pro ما له داعي وينشال بعد."""
import json, os, random, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB = os.environ.get('FBDB', 'https://el3azy-3b64e-default-rtdb.europe-west1.firebasedatabase.app')
NS = os.environ.get('FBNS', '')
UAE = timezone(timedelta(hours=4))
START = 1794859200000


def hdrs():
    if os.environ.get('TOKEN'):
        return {'Authorization': 'Bearer ' + os.environ['TOKEN']}
    sa = os.environ.get('FIREBASE_SA', '').strip()
    if not sa:
        sys.exit('يحتاج FIREBASE_SA')
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    cr = service_account.Credentials.from_service_account_info(json.loads(sa), scopes=[
        'https://www.googleapis.com/auth/firebase.database', 'https://www.googleapis.com/auth/userinfo.email'])
    cr.refresh(Request())
    return {'Authorization': 'Bearer ' + cr.token}


def req(method, path, h, body=None):
    u = f'{DB}/{path}.json' + (f'?ns={NS}' if NS else '')
    r = urllib.request.Request(u, method=method, headers={**h, 'Content-Type': 'application/json'},
                               data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(r, timeout=40) as x:
        return json.loads(x.read().decode() or 'null')


def get_q(h):
    """يرجع الجدول كقائمة (اليوم 1 = الخانة 0)."""
    q = req('GET', 'q', h) or {}
    if isinstance(q, list):
        return [x for x in q[1:]]
    return [q[str(d)] for d in range(1, len(q) + 1)]


def put_q(h, sched):
    req('PUT', 'q', h, {str(i + 1): pid for i, pid in enumerate(sched)})


def today_index(now_ms=None):
    now_ms = now_ms or int(time.time() * 1000)
    return max(0, (now_ms - START) // 86400000)   # 0 = اليوم الأول


def push():
    h = hdrs()
    f = os.path.join(ROOT, 'mano', 'data.json')
    md = json.load(open(f, encoding='utf8'))
    sched = md.get('schedule')
    if not sched:
        existing = get_q(h)
        sys.exit(f'data.json ما فيه schedule (q فيه {len(existing)} يوم) — ما سويت شي')
    t = today_index()
    keep, rest = sched[:t + 1], sched[t + 1:]
    random.SystemRandom().shuffle(rest)          # ترتيب يديد ما ينحفظ في أي مكان عام
    new = keep + rest
    put_q(h, new)
    back = get_q(h)
    assert back == new, 'الجدول اللي انكتب غير اللي انقرى'
    md.pop('schedule', None); md.pop('schedule_pro', None)
    md['days'] = len(new)
    json.dump(md, open(f, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print(f'q ✓ {len(new)} يوم · اليوم {t + 1} ما تغير · {len(rest)} يوم انعاد ترتيبهم · data.json بدون جدول')


if __name__ == '__main__':
    {'push': push}[sys.argv[1] if len(sys.argv) > 1 else 'push']()
