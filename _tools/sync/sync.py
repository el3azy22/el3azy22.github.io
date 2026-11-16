"""مزامنة يومية لقوائم الأندية من موقع رابطة المحترفين (واتحاد الكرة للاعبين اللي مب في قوائم الرابطة).
التشغيل من جذر المستودع: python3 _tools/sync/sync.py   (GitHub Actions كل يوم الصبح)

اللي يسويه بروحه:
  - لاعب يديد في قائمة نادي → ينضاف لـ«اختار تشكيلتك» و«منو اللاعب؟» (البحث)، وصورته من الرابطة لو موجودة
  - انتقال لاعب بين ناديين، أو تغيير رقمه → ينعدل في القسمين
  - لاعب طلع من الدوري → ينشال من «اختار تشكيلتك». ولو كان في جدول «منو اللاعب؟» الياي، ينبدل بلاعب ثاني (الأيام اللي طافت ما تتغير)
  - بعدها يعيد تطبيق تصحيحات المراكز والجنسيات (_tools/position_fixes.json)
اللي يحتاج تدخّل يكتبه في _tools/sync/report.json (problems): صورة ناقصة، فشل السحب، جدول بدون بديل...
الحماية: لو أي نادي رجع فاضي أو أقل من 15 لاعب، أو التغييرات أكثر من 60 في يوم، ما يطبّق شي ويبلّغ.
"""
import html, io, json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UAE = timezone(timedelta(hours=4))
PH = os.path.join(ROOT, 'mano', 'assets', 'p')
REPORT = os.path.join(ROOT, '_tools', 'sync', 'report.json')
UAEFA_ONLY = os.path.join(ROOT, '_tools', 'sync', 'uaefa_only.json')  # لاعبين مسجلين في الاتحاد بس (فرق تحت 21/23)
PL_CLUBS = {'ajman': 'ajman', 'al-ain': 'ain', 'al-dhafra': 'dhafra', 'al-jazira': 'jazira', 'al-nasr': 'nasr', 'al-wahda': 'wahda',
            'al-wasl': 'wasl', 'bani-yas': 'baniyas', 'hatta': 'hatta', 'kalba': 'kalba', 'khorfakkan': 'khorfakkan',
            'shabab-alahli': 'shababahli', 'sharjah': 'sharjah', 'united': 'united'}
TK_ID = {'shababahli': 'shabab'}  # اسم النادي في tashkila/squads.json
FA_CLUB = {'nasr': '4', 'kalba': '12', 'wahda': '8', 'ajman': '21', 'dhafra': '31', 'sharjah': '3', 'wasl': '2', 'united': '464',
           'khorfakkan': '11', 'shababahli': '6', 'hatta': '20', 'jazira': '9', 'baniyas': '5', 'ain': '1'}
KNOWN_NO_PHOTO = {'stefan-pjanovic'}  # ما له صورة لا في الرابطة ولا في الاتحاد (نشيكه لو تغيّر: نشيله من هني)
POS4 = {'GK': 'GK', 'DF': 'DEF', 'MD': 'MID', 'FW': 'FWD'}
COMP = 'b8785e20-745f-11f1-82d0-f556dfffd44c'; PRO = 'd304d980-e5e8-11ea-a63c-112a991a4e3f'
# دوال التنظيف نفسها اللي في _tools/mano/build_data.py
NATFIX={"Cote d'Ivoire":'ساحل العاج','Gambia':'غامبيا','جمهورية صربيا':'صربيا','كاميرون':'الكاميرون','أورغواي':'الأوروغواي','أوزباكستان':'أوزبكستان','غينيا-بيساو':'غينيا بيساو','عُمان':'عمان'}
NAMEFIX={'سفيان راحمي':'سفيان رحيمي','بونو دي اوليفيرا':'برونو دي أوليفيرا','ماكلوم اوليفيرا':'مالكوم أوليفيرا','لوكس بيمينتا':'لوكاس بيمينتا'}
def clean_ar(s):
  s=re.sub(r'^[ً-ْ]+','',s.strip());s=re.sub(r'\s+',' ',s);return NAMEFIX.get(s,s)
def clean_en(s):
  s=re.sub(r'\s+',' ',s.strip())
  if s.isupper() or s[:1].islower() or any(w[:1].islower() for w in s.split() if len(w)>3 and w.lower() not in('da','de','do','dos','al','bin','el')): s=' '.join(w if w.lower() in('da','de','do','dos') else w[:1].upper()+w[1:].lower() if w.isupper() else w[:1].upper()+w[1:] for w in s.split())
  return s
def ap(p):
  try:return int(p['apps'][1])
  except:return 0



def fetch(u, xhr=False, tries=3):
    for k in range(tries):
        try:
            h = {'User-Agent': 'Mozilla/5.0 el3azy-sync'}
            if xhr: h['X-Requested-With'] = 'XMLHttpRequest'
            with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=40) as r:
                return r.read()
        except Exception:
            if k == tries - 1: raise
            time.sleep(4 + 6 * k)


def parse(h):  # نفس محلل _tools/mano/scrape.py
    out = []
    for blk in re.split(r'(?=<a href="https://uaeproleague\.ae/(?:en|ar)/player/)|(?=<h\d[^>]*class="[^"]*title)', h):
        m = re.match(r'<a href="(https://uaeproleague\.ae/(?:en|ar)/player/([^/]+)/[^"]+)"', blk)
        if not m: continue
        t = lambda p: (re.search(p, blk, re.S) or [None, None])[1]
        nat = re.search(r'countrySubWrap.*?<div class="left">(.*?)<span class="citizen-info">\s*(.*?)\s*</span>', blk, re.S)
        flag = re.search(r'/flags/([A-Z]{2,3})\.png', blk)
        out.append(dict(slug=m.group(2), num=(t(r'jerseyNum">\s*([^<]*?)\s*<') or '').strip(), img=t(r'profileWrap.*?<img src="([^"]+)"'),
                        flag=flag.group(1) if flag else '', nat=html.unescape(re.sub(r'<[^>]+>', '', nat.group(1)).strip()) if nat else '',
                        age=t(r'(?:Age|العمر)\s*:?\s*(\d+)'), pos=(t(r'class="position">\s*(.*?)\s*<') or '').strip(),
                        name=html.unescape((t(r'class="fullname">\s*(.*?)\s*<') or '').strip()),
                        apps=re.findall(r'<div class="right">\s*([^<]*?)\s*</div>', blk)))
    return out


def scrape_pl():
    data = {}
    for pc, c in PL_CLUBS.items():
        page = fetch(f'https://uaeproleague.ae/en/clubs/{pc}').decode('utf8')
        uid = re.search(r'clubs/([0-9a-f-]{36})/content/squad', page).group(1)
        res = {}
        for lang in ('en', 'ar'):
            j = json.loads(fetch(f'https://uaeproleague.ae/{lang}/clubs/{uid}/content/squad?seasonCompetition={COMP}&person_status_id={PRO}', xhr=True))
            res[lang] = parse(j['squad']); time.sleep(1)
        ar = {p['slug']: p for p in res['ar']}
        for p in res['en']:
            a = ar.get(p['slug'], {}); p['name_ar'] = a.get('name', ''); p['nat_ar'] = a.get('nat', '')
        data[c] = res['en']
    return data


def main():
    import types; B = types.SimpleNamespace(clean_ar=clean_ar, clean_en=clean_en, NATFIX=NATFIX, ap=ap)
    now = datetime.now(UAE)
    rep = {'date': now.strftime('%Y-%m-%d %H:%M'), 'changes': [], 'problems': []}
    ch, pr = rep['changes'], rep['problems']
    try:
        pl = scrape_pl()
    except Exception as e:
        pr.append(f'فشل السحب من موقع الرابطة: {e}'); return finish(rep, False)
    small = [c for c, v in pl.items() if len(v) < 15]
    if small:
        pr.append('قائمة ناقصة من الرابطة (ما طبقنا شي): ' + '، '.join(small)); return finish(rep, False)

    tk = json.load(open(os.path.join(ROOT, 'tashkila', 'squads.json'), encoding='utf8'))
    md = json.load(open(os.path.join(ROOT, 'mano', 'data.json'), encoding='utf8'))
    fa_only = set(json.load(open(UAEFA_ONLY))) if os.path.exists(UAEFA_ONLY) else set()
    clubs = {c['id']: c for c in tk['clubs']}
    where = {p[5]: (cid, p) for cid, c in clubs.items() for p in c['p'] if p[5]}
    mp = {p['id']: p for p in md['players']}
    seen = set()

    for c, players in pl.items():
        tid = TK_ID.get(c, c)
        for q in players:
            s = q['slug']; seen.add(s)
            no = int(q['num']) if q['num'].isdigit() else None
            na = B.clean_ar(q['name_ar']) or B.clean_en(q['name'])
            nat = B.NATFIX.get(q['nat_ar'], B.NATFIX.get(q['nat'], q['nat_ar']))
            age = int(q['age']) if q['age'] else None
            # «منو اللاعب؟»
            m = mp.get(s)
            if m is None:
                m = dict(id=s, n=na, e=B.clean_en(q['name']), c=c, p=q['pos'], nat=nat, f=q['flag'], a=age, no=no, ap=B.ap(q))
                md['players'].append(m); mp[s] = m; ch.append(f'لاعب يديد: {na} ({tid} #{no})')
            else:
                if m['c'] != c: ch.append(f"انتقال: {m['n']} من {m['c']} إلى {c}"); m['c'] = c
                if no and m.get('no') != no: ch.append(f"رقم {m['n']}: {m.get('no')} ← {no}"); m['no'] = no
                if age and m.get('a') != age: m['a'] = age
                m['ap'] = B.ap(q)
            # «اختار تشكيلتك»
            if s in where:
                cid, e = where[s]
                if cid != tid:
                    clubs[cid]['p'].remove(e); clubs[tid]['p'].append(e); where[s] = (tid, e)
                if no and e[0] != no: e[0] = no
            elif no is not None and (e := next((x for x in clubs[tid]['p'] if not x[5] and x[0] == no), None)):
                e[5] = s; where[s] = (tid, e)  # لاعب كان عندنا بدون رابط في الرابطة: نربطه بس
            elif no is not None and q['pos'] in POS4:
                e = [no, na, POS4[q['pos']], '', 0, s, na]
                clubs[tid]['p'].append(e); where[s] = (tid, e)
            # الصورة
            f = os.path.join(PH, s + '.webp')
            if os.path.exists(f): m['ph'] = 1
            else:
                if q['img'] and 'dummy' not in q['img']:
                    try:
                        from PIL import Image
                        im = Image.open(io.BytesIO(fetch(q['img']))).convert('RGBA').resize((240, 240), Image.LANCZOS)
                        im.save(f, 'WEBP', quality=82); m['ph'] = 1; ch.append(f'صورة يديدة: {na}')
                    except Exception as ex:
                        pr.append(f'صورة {na} ({s}) ما نزلت: {ex}')
                elif s not in KNOWN_NO_PHOTO:
                    pr.append(f'صورة ناقصة: {na} ({tid} #{no}) — الرابطة ما عندها، تنجاب من الاتحاد')

    # اللي طلعوا من قوائم الرابطة: لاعبين الاتحاد بس نتأكد منهم في موقع الاتحاد
    fa_names = {}
    # مقارنة الأسماء بدون الهمزات والتاء المربوطة والألف المقصورة (أسماءنا موحدة الإملاء في _tools/name_fixes.json)
    def nk(x):
        x = re.sub(r'[\u064B-\u0652\u0640]', '', x)
        x = re.sub('[أإآ]', 'ا', x).replace('ة', 'ه').replace('ى', 'ي')
        return re.sub(r'\s+', '', x)
    def fa_has(club, slug, name):
        if club not in fa_names:
            try:
                d = json.loads(fetch(f'https://www.uaefa.ae/api/players?club_id={FA_CLUB[club]}&lang=ar'))
                fa_names[club] = {nk(p.get('shortname') or '') for p in d.get('players', [])}
            except Exception:
                fa_names[club] = None
        return None if fa_names[club] is None else nk(name) in fa_names[club]
    rev = {v: k for k, v in TK_ID.items()}
    for cid, c in clubs.items():
        for e in list(c['p']):
            s = e[5]
            if not s or s in seen: continue
            club = rev.get(cid, cid)
            if s in fa_only:
                ok = fa_has(club, s, e[1])
                if ok is None: pr.append(f'ما قدرنا نتأكد من {e[1]} في موقع الاتحاد'); continue
                if ok: continue
            c['p'].remove(e); ch.append(f'طلع من قائمة {cid}: {e[1]} #{e[0]}')
    gone = [p for p in md['players'] if p['id'] not in seen and p['id'] not in fa_only]

    # جدول «منو اللاعب؟»: نبدّل اللي طلعوا من الدوري في الأيام الجاية بس
    start = datetime.fromisoformat(md['start']).replace(tzinfo=UAE)
    today = max(0, (now - start).days)  # 0 = اليوم الأول
    sched = md['schedule']
    gone_ids = {p['id'] for p in gone}
    pro = md.setdefault('schedule_pro', [])
    used = set(sched) | set(pro)
    spare = [p for p in md['players'] if p['id'] not in used and p['id'] in seen and p.get('ap', 0) >= 5 and p.get('nat') and p.get('a') and p.get('no')]
    spare.sort(key=lambda p: -p.get('ap', 0))
    for i in range(today + 1, len(sched)):  # اليوم الحالي ما يتغير
        if sched[i] in gone_ids:
            old = mp[sched[i]]['n']
            if spare:
                nw = spare.pop(0); sched[i] = nw['id']; ch.append(f'جدول منو اللاعب يوم {i + 1}: {old} ← {nw["n"]} (طلع من الدوري)')
            else:
                pr.append(f'جدول منو اللاعب يوم {i + 1}: {old} طلع من الدوري وما في بديل')
    # «تحدي الخبير»: نفس الشي، والبديل من اللي شاركوا 1–4 مباريات. ونضيف أي لاعب صار مؤهل لآخر الجدول
    pro_ok = lambda p: p['id'] not in used and p['id'] in seen and 1 <= p.get('ap', 0) <= 4 and p.get('ph') and p.get('nat') and p.get('a') and p.get('no')
    pspare = sorted([p for p in md['players'] if pro_ok(p)], key=lambda p: -p.get('ap', 0))
    for i in range(today + 1, len(pro)):
        if pro[i] in gone_ids:
            old = mp[pro[i]]['n']
            if pspare:
                nw = pspare.pop(0); pro[i] = nw['id']; used.add(nw['id']); ch.append(f'تحدي الخبير يوم {i + 1}: {old} ← {nw["n"]} (طلع من الدوري)')
            else:
                pr.append(f'تحدي الخبير يوم {i + 1}: {old} طلع من الدوري وما في بديل')
    added = [p for p in pspare if p['id'] not in used]
    for p in added:
        pro.append(p['id']); used.add(p['id'])
    if added: ch.append(f'تحدي الخبير: انضاف {len(added)} لاعب لآخر الجدول (صار {len(pro)} يوم)')
    # تنبيه قبل ما يخلص أي جدول بشهر (بعدها اللعبة ترجع تعيد لاعبين من أول الموسم)
    for nm, L in (('لاعب اليوم', sched), ('تحدي الخبير', pro)):
        left = len(L) - today - 1
        if left < 30:
            pr.append(f'جدول {nm} باقي له {left} يوم بس، لازم نمدده قبل ما يخلص')

    if len(ch) > 60:
        pr.append(f'تغييرات كثيرة ({len(ch)}) في يوم واحد، ما طبقناها. لازم مراجعة'); rep['changes'] = ch[:80]; return finish(rep, False)
    for c in clubs.values():
        c['p'].sort(key=lambda e: (['GK', 'DEF', 'MID', 'FWD'].index(e[2]) if e[2] in POS4.values() else 9, e[0]))
    md['updated'] = now.date().isoformat()
    json.dump(tk, open(os.path.join(ROOT, 'tashkila', 'squads.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(md, open(os.path.join(ROOT, 'mano', 'data.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    subprocess.run([sys.executable, os.path.join(ROOT, '_tools', 'apply_position_fixes.py')], check=False, capture_output=True)
    return finish(rep, True)


def finish(rep, applied):
    rep['applied'] = applied
    # مواعيد المباريات: لو تغيرت عن قواعد Firebase، نجهز القواعد اليديدة ونبلّغ (النشر يدوي من صفحة القواعد)
    try:
        d = json.load(open(os.path.join(ROOT, 'predict', 'data.json'), encoding='utf8'))
        L = json.load(open(os.path.join(ROOT, 'predict', 'lock.json'), encoding='utf8'))
        T = time.time() * 1000
        bad = [m for m in d['matches'] if m['t'] > T and L.get(m['id']) != m['t']]
        if bad:
            rep['problems'].append(f'مواعيد {len(bad)} مباراة تغيرت أو انضافت: لازم تحديث قواعد Firebase (صفحة القواعد)')
            rep['rules_outdated'] = len(bad)
    except Exception as e:
        rep['problems'].append(f'فحص المواعيد فشل: {e}')
    old = json.load(open(REPORT, encoding='utf8')) if os.path.exists(REPORT) else {}
    hist = (old.get('history') or [])[-29:]
    hist.append({'date': rep['date'], 'changes': len(rep['changes']), 'problems': len(rep['problems'])})
    rep['history'] = hist
    json.dump(rep, open(REPORT, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != 'history'}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
