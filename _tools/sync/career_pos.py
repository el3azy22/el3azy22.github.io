"""مركز اللاعب = أكثر مركز لعب فيه في مسيرته (قرار إبراهيم 26 نوفمبر 2026).

المصدر: «المركز الأساسي» في Transfermarkt لكل لاعب في قوائم أندية الدوري الـ14 (يتحدد من مسيرة اللاعب كاملة).
- الأجنحة (يمين/يسار، وسط أو جناح) = مهاجم، على قاعدة إبراهيم.
- المطابقة صارمة: نفس النادي + اسم متشابه + (نفس الرقم أو نفس العمر ±1). أي لاعب ما تطابق بثقة يبقى على تسجيل الرابطة.
- مراكز عامة («Midfielder»، «Defender»…) ما تنعتمد (ما تدل على مسيرة).
- قرارات إبراهيم في position_fixes.json/_mano فوق هذا كله.
- لو الموقع ما رد: يبقى آخر ملف محفوظ (ما يتغير شي).

المخرج: _tools/sync/career_pos.json  {player_id: [مركز Transfermarkt, GK|DF|MD|FW]}
"""
import json, os, re, sys, time, html, difflib, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, '_tools', 'sync', 'career_pos.json')
TM = {'jazira': 'al-jazira-club/kader/verein/2524', 'shababahli': 'shabab-al-ahli-club/kader/verein/60529',
      'wasl': 'al-wasl-sc/kader/verein/16214', 'sharjah': 'sharjah-fc/kader/verein/13613', 'ain': 'al-ain-fc/kader/verein/2150',
      'wahda': 'al-wahda-fc/kader/verein/161', 'nasr': 'al-nasr-sc-uae-/kader/verein/5432', 'kalba': 'kalba-fc/kader/verein/38040',
      'ajman': 'ajman-club/kader/verein/24724', 'khorfakkan': 'khor-fakkan-ssc/kader/verein/26351',
      'united': 'united-fc-uae-/kader/verein/94732', 'baniyas': 'fc-baniyas/kader/verein/4785',
      'hatta': 'hatta-club/kader/verein/17195', 'dhafra': 'al-dhafra-fc/kader/verein/14456'}
POS = {'Goalkeeper': 'GK', 'Centre-Back': 'DF', 'Left-Back': 'DF', 'Right-Back': 'DF',
       'Defensive Midfield': 'MD', 'Central Midfield': 'MD', 'Attacking Midfield': 'MD',
       'Left Midfield': 'FW', 'Right Midfield': 'FW', 'Left Winger': 'FW', 'Right Winger': 'FW',
       'Centre-Forward': 'FW', 'Second Striker': 'FW'}


def season():
    t = time.gmtime()
    return t.tm_year if t.tm_mon >= 7 else t.tm_year - 1


def squad(path):
    u = f'https://www.transfermarkt.com/{path}/saison_id/{season()}'
    h = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40).read().decode('utf8', 'replace')
    out = []
    for r in re.split(r'<tr class="(?:odd|even)">', h)[1:]:
        nm = re.search(r'class="hauptlink">\s*<a href="/[^/]+/profil/spieler/(\d+)"[^>]*>\s*([^<]+?)\s*<', r)
        if not nm:
            continue
        no = re.search(r'class=rn_nummer>([^<]*)<', r)
        pos = re.search(r'<tr>\s*<td>\s*([A-Za-z\- ]+?)\s*</td>\s*</tr>', r)
        age = re.search(r'\d\d/\d\d/\d{4} \((\d+)\)|>\s*(\d{1,2})\s*</td>', r)
        out.append(dict(id=nm.group(1), name=html.unescape(nm.group(2)), no=(no.group(1).strip() if no else ''),
                        pos=pos.group(1) if pos else '', age=int(next(g for g in age.groups() if g)) if age else None))
    return out


def toks(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower().replace('al-', 'al ')
    return [w for w in re.sub(r'[^a-z ]', ' ', s).split() if len(w) > 2 and w not in ('al', 'bin', 'ben')]


COMMON = set('mohamed mohammed mohammad muhammad mohamad ahmed ahmad ali abdulla abdullah abdalla khalid khaled saeed said salem salim hamad hamid rashid rashed sultan saif obaid omar hassan hasan ibrahim yousef yousif youssef khamis juma jumaa abdulrahman abdelrahman mubarak eisa issa essa majid mansour nasser naser zayed hamdan humaid suhail matar fahad faisal hussain marcos silva santos souza oliveira junior'.split()) | set('balooshi blooshi baloushi bloushi hammadi hamadi mansoori zaabi ameri amiri naqbi nuqbi ketbi shamsi suwaidi dhaheri kaabi mazrouei mheiri mehairi marzooqi marzouqi hosani hosni menhali qubaisi mehairbi nuaimi shehhi kuwaiti hashemi darmaki yammahi ali mahri bedwawi neyadi mesmari jaberi'.split())


def close(a, b):   # كم كلمة متشابهة (تتحمل اختلاف التهجئة: Lazro/Lazaro)
    return sum(1 for x in set(a) if any(difflib.SequenceMatcher(None, x, y).ratio() >= 0.8 for y in set(b)))


def main():
    md = json.load(open(os.path.join(ROOT, 'mano', 'data.json'), encoding='utf8'))
    AL = json.load(open(os.path.join(ROOT, 'mano', 'aliases.json'), encoding='utf8'))   # أسماء الشهرة (كاكو، تاليسكا…) تساعد المطابقة
    old = json.load(open(OUT, encoding='utf8')) if os.path.exists(OUT) else {}
    res, ok = {}, set()
    for c, path in TM.items():
        try:
            L = squad(path); ok.add(c); time.sleep(2)
        except Exception as e:
            print('فشل', c, e); continue
        for p in [q for q in md['players'] if q['c'] == c]:
            alias = [a for a in AL.get(p['id'], []) if re.match(r'[A-Za-z]', a)]
            mine = toks(p.get('e')) + [w for a in alias for w in toks(a)]
            exact = {' '.join(toks(a)) for a in alias}
            best = None
            for x in L:
                theirs = toks(x['name'])
                ov = close(mine, theirs)
                rare = close([w for w in mine if w not in COMMON], [w for w in theirs if w not in COMMON])
                num = x['no'] and str(x['no']) == str(p.get('no'))
                if x['no'] and x['no'] != '-' and p.get('no') and not num and ov < 2:
                    continue   # رقم مختلف واسم واحد مشترك: غالباً لاعب ثاني
                age = x['age'] and p.get('a') and abs(x['age'] - p['a']) <= 1
                # اسم نادر مشترك + (رقم أو عمر)، أو اسمين مشتركين + الرقم والعمر. الأسامي الشايعة (محمد، أحمد…) بروحها ما تكفي
                if ' '.join(theirs) in exact and (num or age):   # اسم الشهرة نفسه بالضبط
                    ov, rare = 9, 1
                if ((rare and (num or age)) or (ov >= 2 and num and age)) and (best is None or ov > best[0]):
                    best = (ov, x)
            if best and best[1]['pos'] in POS:
                res[p['id']] = [best[1]['pos'], POS[best[1]['pos']]]
    for pid, v in old.items():   # نادي ما رد اليوم: نخلي اللي عندنا
        p = next((q for q in md['players'] if q['id'] == pid), None)
        if p and p['c'] not in ok and pid not in res:
            res[pid] = v
    if len(res) < 200:
        print('نتيجة قليلة، ما حدثنا الملف', len(res)); return
    json.dump(res, open(OUT, 'w', encoding='utf8'), ensure_ascii=False, indent=0, sort_keys=True)
    print('مراكز المسيرة:', len(res))


if __name__ == '__main__':
    main()
