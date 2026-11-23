"""نشر قواعد Firebase تلقائياً (بدل النسخ واللصق اليدوي).

1. يولّد القواعد من جديد (make_rules.py → rules.json و predict/lock.json).
2. يقارنها بالقواعد المنشورة. لو نفسها ما يسوي شي.
3. لو مختلفة: ينشرها بحساب الخدمة (سر FIREBASE_SA في GitHub)، ويتأكد إنها انتشرت، ويحدّث setup/rules.html.
4. لو ما في حساب خدمة أو فشل النشر: يرجّع rules.json و lock.json لنسختهم القديمة، عشان صفحة التوقعات
   ما تقفل على مواعيد غير المنشورة، ويطلع تنبيه.

حساب الخدمة صلاحيته «Firebase Realtime Database Admin» بس، ومفتاحه محفوظ في أسرار GitHub وما ينكتب في المستودع.
للتجربة على المحاكي: FBDB=http://127.0.0.1:9000 FBNS=demo-el3azy-default-rtdb TOKEN=owner
"""
import html, json, os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DB = os.environ.get('FBDB', 'https://el3azy-3b64e-default-rtdb.europe-west1.firebasedatabase.app')
NS = os.environ.get('FBNS')
FILES = ['_tools/firebase/rules.json', 'predict/lock.json', 'predict/open.json', 'predict/mopen.json']


def revert(msg):
    subprocess.run(['git', 'checkout', '--'] + FILES, cwd=ROOT, check=False)
    print('::warning::' + msg)
    sys.exit(0)


def token():
    if os.environ.get('TOKEN'):
        return None, {'Authorization': 'Bearer ' + os.environ['TOKEN']}
    sa = os.environ.get('FIREBASE_SA', '').strip()
    if not sa:
        return 'no-sa', None
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    cr = service_account.Credentials.from_service_account_info(json.loads(sa), scopes=[
        'https://www.googleapis.com/auth/firebase.database', 'https://www.googleapis.com/auth/userinfo.email'])
    cr.refresh(Request())
    return None, {'Authorization': 'Bearer ' + cr.token}


def url():
    return DB + '/.settings/rules.json' + (f'?ns={NS}' if NS else '')


def get(h):
    with urllib.request.urlopen(urllib.request.Request(url(), headers=h), timeout=30) as r:
        return json.loads(r.read().decode('utf8'))


def main():
    subprocess.run([sys.executable, 'make_rules.py'], cwd=HERE, check=True)
    local = json.load(open(os.path.join(HERE, 'rules.json'), encoding='utf8'))
    err, h = token()
    if err:
        changed = subprocess.run(['git', 'diff', '--quiet', '--'] + FILES, cwd=ROOT).returncode
        if changed:
            revert('القواعد تحتاج تحديث بس ما في FIREBASE_SA في أسرار GitHub، فما انتشرت')
        print('القواعد ما تغيرت'); return
    try:
        live = get(h)
    except Exception as e:
        revert(f'ما قدرنا نقرا القواعد المنشورة: {e}')
    if live == local:
        print('القواعد المنشورة مطابقة، ما في شي ينتشر')
    else:
        body = json.dumps(local, ensure_ascii=False, separators=(',', ':')).encode('utf8')
        try:
            urllib.request.urlopen(urllib.request.Request(url(), data=body, method='PUT', headers={**h, 'Content-Type': 'application/json'}), timeout=60)
            if get(h) != local:
                revert('النشر رجع بدون خطأ بس القواعد المنشورة مب مطابقة')
        except SystemExit:
            raise
        except Exception as e:
            revert(f'نشر القواعد فشل: {e}')
        print('✅ القواعد انتشرت وتأكدنا منها')
    # صفحة القواعد اليدوية تظل مطابقة (احتياط لو احتجنا نلصقها يدوي)
    p = os.path.join(ROOT, 'setup', 'rules.html')
    s = open(p, encoding='utf8').read()
    raw = open(os.path.join(HERE, 'rules.json'), encoding='utf8').read()
    s2 = re.sub(r'(<textarea id="r" readonly>).*?(</textarea>)', lambda m: m.group(1) + html.escape(raw, quote=False) + m.group(2), s, flags=re.S)
    if s2 != s:
        open(p, 'w', encoding='utf8').write(s2)


if __name__ == '__main__':
    main()
