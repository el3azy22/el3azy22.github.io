import json
import os
L=int(os.environ.get("L","1794859200000")); DAYMS=86400000; GRACE=15*60000
CL="ajman|ain|dhafra|jazira|nasr|wahda|wasl|baniyas|hatta|kalba|khorfakkan|shababahli|sharjah|united"
R="newData.parent().parent().parent().parent()"  # root-after from s/$d/$m/$f
P=lambda base:f"{base}.child('p').child($d).child($m).child(auth.uid)"
inc="((!data.exists() && newData.val() == 1) || newData.val() == data.val() + 1)"
fresh=lambda after:f"auth != null && !root.child('p').child($d).child($m).child(auth.uid).exists() && {P(after)}.exists()"
g=lambda after:f"{P(after)}.child('g').val()"
s_after="newData.parent().parent().parent().parent()"
c_after="newData.parent().parent().parent().parent().parent()"
CA="newData.parent().parent().parent().parent().child('c').child($d).child($m).child(newData.child('c').val())"   # بعد الكتابة
CR="root.child('c').child($d).child($m).child(newData.child('c').val())"                                        # قبل الكتابة
rules={"rules":{
 ".read":False,".write":False,
 "p":{"$d":{"$m":{"$u":{
   ".read":"auth != null && auth.uid == $u",   # المشجع يتأكد إن نتيجته انحفظت (لو انقطع الاتصال قبل التأكيد)
   ".write":"auth != null && auth.uid == $u && !data.exists()",
   # «تحدي الخبير» (pro) ينفتح بعد لاعب اليوم: نتيجته ما تنقبل إلا من مشجع عنده نتيجة لاعب اليوم في نفس اليوم
   ".validate":("newData.hasChildren(['g','c','d']) && ($m == 'easy' || ($m == 'pro' && newData.parent().parent().child('easy').child($u).exists())) && $d.matches(/^[0-9]{1,4}$/)"
     " && newData.child('d').isNumber() && $d == '' + newData.child('d').val()"
     # النتيجة تنقبل في يومها بس، مع سماح 15 دقيقة بعد 12 بالليل (اللي خلّص 11:59 والطلب وصل متأخر)
     f" && now >= {L} + (newData.child('d').val() - 1) * {DAYMS} && now < {L} + newData.child('d').val() * {DAYMS} + {GRACE}"
     # نتيجة الخبير لازم تكون لنفس نادي نتيجة لاعب اليوم (عشان نقاطه تنحسب لنفس الجمهور اللي انحسبت له لعبته)
     " && ($m == 'easy' || newData.child('c').val() == newData.parent().parent().child('easy').child($u).child('c').val())"
     " && newData.child('g').isNumber() && newData.child('g').val() % 1 == 0 && newData.child('g').val() >= 0 && newData.child('g').val() <= 6"
     f" && newData.child('c').isString() && newData.child('c').val().matches(/^({CL})?$/)"
     " && newData.parent().parent().parent().parent().child('s').child($d).child($m).child('n').val() == (root.child('s').child($d).child($m).child('n').exists() ? root.child('s').child($d).child($m).child('n').val() : 0) + 1"
     # اللعبة لازم تنحسب لناديها كاملة: لعبة +1 دايماً، ونقاط +(7 − المحاولات) لو عرفه (ما يقدر يرسل الفوز ويخفي الخسارة)
     f" && (newData.child('c').val() == '' || ({CA}.child('n').val() == ({CR}.child('n').exists() ? {CR}.child('n').val() : 0) + 1"
     f" && (newData.child('g').val() == 0 || {CA}.child('t').val() == ({CR}.child('t').exists() ? {CR}.child('t').val() : 0) + 7 - newData.child('g').val())))"),
   # t (اختياري): وقت السيرفر لحظة الحل، لفك التعادل في «نجوم الأسبوع» (الأسبق)
   "d":{".validate":True},"g":{".validate":True},"c":{".validate":True},"t":{".validate":"newData.val() == now"},
   # sec (اختياري): كم ثانية أخذ من فتح التحدي لين خلّص — لكسر التعادل الأخير (الأسرع). ينقاس في التلفون
   "sec":{".validate":"newData.isNumber() && newData.val() % 1 == 0 && newData.val() >= 0 && newData.val() <= 86400"},"$other":{".validate":False}}}}},
 "s":{".read":True,"$d":{"$m":{"$f":{
   ".write":fresh(s_after),
   ".validate":f"newData.isNumber() && {inc} && ($f == 'n' || ($f == 'w' && {g(s_after)} > 0) || $f == 'g' + {g(s_after)})"}}}},
 "c":{".read":True,"$d":{"$m":{"$c":{
   "n":{".write":fresh(c_after),
        ".validate":f"newData.isNumber() && {inc} && {P(c_after)}.child('c').val() == $c"},
   "t":{".write":fresh(c_after),
        ".validate":f"newData.isNumber() && {P(c_after)}.child('c').val() == $c && {g(c_after)} > 0 && newData.val() == (data.exists() ? data.val() : 0) + 7 - {g(c_after)}"},
   "$o":{".validate":False}}}}}
}}
# ── جواب «لاعب اليوم» ── q/<day> = رقم اللاعب. كل يوم يتقرى بس من بدايته (12 بالليل الإمارات)، والكتابة لحساب الخدمة بس.
# عشان محد يعرف جواب يوم قبل ما يجي (الجدول مب في ملفات الموقع)
rules["rules"]["q"]={str(d):{".read":f"now >= {L + (d - 1) * DAYMS}"} for d in range(1,401)}
# ── «قيّم اللاعبين» ── $k = <match_id>_<kickoff ms>
# rv/$k/$u  سجل الجهاز (مقفول): {t: وقت البداية, r: {$p: 1..10}, st: نجم المباراة}
# ra/$k/$p = {n: عدد, s: مجموع}   rs/$k/$p = أصوات نجم المباراة   rn/$k = عدد المقيّمين  (كلها مقروءة)
H=3600000
RV=lambda after:f"{after}.child('rv').child($k).child(auth.uid)"
rfresh=lambda after:f"auth != null && !root.child('rv').child($k).child(auth.uid).exists() && {RV(after)}.exists()"
ra_after="newData.parent().parent().parent().parent()"
rs_after="newData.parent().parent().parent()"
rn_after="newData.parent().parent()"
PID="/^c?[0-9]{1,7}$/"
rules["rules"].update({
 "rv":{"$k":{"$u":{
   ".write":"auth != null && auth.uid == $u && !data.exists()",
   ".validate":("newData.hasChildren(['t','r']) && $k.matches(/^[0-9]{3,8}_[0-9]{13}$/)"
     " && newData.child('t').isNumber() && $k.endsWith('_' + newData.child('t').val())"
     f" && now >= newData.child('t').val() + {100*60000} && now < newData.child('t').val() + {50*H}"
     f" && newData.parent().parent().parent().child('rn').child($k).val() == (root.child('rn').child($k).exists() ? root.child('rn').child($k).val() : 0) + 1"),
   "t":{".validate":True},
   # كل لاعب تقيّمه لازم يزيد عدده +1 ومجموعه بنفس التقييم (ما ينفع مجموع بدون عدد)
   "r":{"$p":{".validate":(f"$p.matches({PID}) && newData.isNumber() && newData.val() >= 1 && newData.val() <= 10 && newData.val() % 1 == 0"
     " && newData.parent().parent().parent().parent().parent().child('ra').child($k).child($p).child('n').val() == (root.child('ra').child($k).child($p).child('n').exists() ? root.child('ra').child($k).child($p).child('n').val() : 0) + 1"
     " && newData.parent().parent().parent().parent().parent().child('ra').child($k).child($p).child('s').val() == (root.child('ra').child($k).child($p).child('s').exists() ? root.child('ra').child($k).child($p).child('s').val() : 0) + newData.val()")}},
   "st":{".validate":f"newData.isString() && newData.val().matches({PID})"},
   "$other":{".validate":False}}}},
 "rn":{".read":True,"$k":{".write":rfresh(rn_after),".validate":f"newData.isNumber() && {inc}"}},
 "ra":{".read":True,"$k":{"$p":{
   "n":{".write":rfresh(ra_after),".validate":f"newData.isNumber() && {inc} && {RV(ra_after)}.child('r').child($p).exists()"},
   "s":{".write":rfresh(ra_after),".validate":f"newData.isNumber() && newData.val() == (data.exists() ? data.val() : 0) + {RV(ra_after)}.child('r').child($p).val()"},
   "$o":{".validate":False}}}},
 "rs":{".read":True,"$k":{"$p":{".write":rfresh(rs_after),".validate":f"newData.isNumber() && {inc} && {RV(rs_after)}.child('st').val() == $p"}}},
})
# ── هوية المشجع ── f/$u = {c: النادي أو none, n: الاسم الاختياري}   fc/$c = عدد مشجعي النادي (مقروء)
FCL=CL+"|none"
S0=1785528000000; YMS=31557600000   # 1 أغسطس 2026 00:00 الإمارات · سنة = 365.25 يوم
KEEPX="newData.child('x').val() == data.child('x').val()"
# حساب المدير (Claude): يقرا f ويقدر يشيل حسابات وهمية ويصحح fc. الحساب مجهول ومفتاحه برا المستودع
ADMIN=os.environ.get("ADMIN","Vt7pBIwn9jhQCI2LSORFpnU3aCa2"); ISADM=f"auth != null && auth.uid == '{ADMIN}'"
rules["rules"].update({
 "f":{".read":ISADM,"$u":{
   ".read":"auth != null && auth.uid == $u",
   # المشجع ما يقدر يمسح بطاقته (كان يسمح بتغيير النادي بلا حد)؛ المسح للمدير بس
   ".write":f"(auth != null && auth.uid == $u && newData.exists()) || ({ISADM} && !newData.exists())",
   ".validate":(f"newData.hasChildren(['c','t']) && newData.child('c').isString() && newData.child('c').val().matches(/^({FCL})$/)"
     " && (data.child('c').val() == newData.child('c').val() || newData.parent().parent().child('fc').child(newData.child('c').val()).val() == (root.child('fc').child(newData.child('c').val()).exists() ? root.child('fc').child(newData.child('c').val()).val() : 0) + 1)"
     # تغيير النادي: الجديد +1 والقديم −1 مع بعض (عدد المشجعين ما يتضخم)
     " && (!data.child('c').exists() || data.child('c').val() == newData.child('c').val() || newData.parent().parent().child('fc').child(data.child('c').val()).val() == root.child('fc').child(data.child('c').val()).val() - 1)"
     # تغيير النادي: 24 ساعة تعديل بعد كل اختيار، وبعدها تغيير واحد في الموسم (x = رقم الموسم اللي غيّر فيه).
     # الموسم يبدا 1 أغسطس (S0 = 1 أغسطس 2026 بتوقيت الإمارات) ويتجدد كل سنة تلقائياً. «محايد» يختار نادي أي وقت.
     f" && (!data.child('t').exists() ? newData.child('t').val() == now && {KEEPX}"
     f" : data.child('c').val() == newData.child('c').val() ? newData.child('t').val() == data.child('t').val() && {KEEPX}"
     f" : now - data.child('t').val() < {DAYMS} ? newData.child('t').val() == data.child('t').val() && {KEEPX}"
     f" : data.child('c').val() == 'none' ? newData.child('t').val() == now && {KEEPX}"
     f" : (!data.child('x').exists() || now >= {S0} + (data.child('x').val() + 1) * {YMS}) && newData.child('t').val() == now"
     f" && newData.child('x').isNumber() && now >= {S0} + newData.child('x').val() * {YMS} && now < {S0} + (newData.child('x').val() + 1) * {YMS})"),
   "c":{".validate":True},
   "n":{".validate":"newData.isString() && newData.val().length <= 16"},
   "t":{".validate":"newData.isNumber()"},
   "x":{".validate":"newData.isNumber()"},
   "$other":{".validate":False}}},
 "fc":{".read":True,"$c":{
   ".write":"auth != null",
   ".validate":(f"$c.matches(/^({FCL})$/) && newData.isNumber() && ({ISADM} && newData.val() >= 0 || "
     "(newData.parent().parent().child('f').child(auth.uid).child('c').val() == $c && root.child('f').child(auth.uid).child('c').val() != $c && newData.val() == (data.exists() ? data.val() : 0) + 1)"
     " || (root.child('f').child(auth.uid).child('c').val() == $c && newData.parent().parent().child('f').child(auth.uid).child('c').val() != $c && newData.val() == data.val() - 1))")}},
})

# ── «دوري التوقعات» ── pr/<match_id>/<uid> = {h, a, x?, c, n, w}
# كل مباراة لها قاعدة بموعدها الرسمي (من predict/data.json): الكتابة قبل الصافرة بس، والقراية للكل بعد الصافرة.
# c و n لازم يطابقون بطاقة المشجع (f/uid)، و w = وقت السيرفر (الحساب يرفض أي توقع w فيه بعد الموعد الرسمي).
# لو تغيّر موعد مباراة أو انضافت مباريات يديدة: python3 _tools/predict/build.py ثم هالملف، وتنلصق القواعد من يديد.
_pd=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','predict','data.json')
_ms=json.load(open(_pd,encoding='utf8'))['matches'] if os.path.exists(_pd) else []
FCU="root.child('f').child($u)"
NUM="newData.isNumber() && newData.val() % 1 == 0 && newData.val() >= 0 && newData.val() <= 20"
# متى يفتح التوقع (قرار إبراهيم 17 نوفمبر: الجولة الجاية بس، مب كل الجولات):
# الجولات بترتيب أول مباراة فيها؛ الجولة تفتح بعد آخر مباراة في الجولة اللي قبلها (اللي قبل أول مباراة فيها) بساعتين.
# أول جولة في الملف مفتوحة من البداية.
def _opens(ms):
  rd={}
  for m in ms: rd.setdefault(m['wk'],[]).append(m['t'])
  order=sorted(rd,key=lambda w:(min(rd[w]),w)); op={}; prev=None
  for w in order:
    t0=min(rd[w])
    if prev is None: op[w]=0
    else:
      before=[t for t in rd[prev] if t<t0]
      op[w]=(max(before) if before else min(rd[prev]))+2*3600000
    prev=w
  return op
def _pr(T,O=0):
  return {".read":f"now >= {T}","$u":{
    ".read":"auth != null && auth.uid == $u",
    ".write":f"auth != null && auth.uid == $u && now < {T}"+(f" && now >= {O}" if O else ""),
    ".validate":"newData.hasChildren(['h','a','c','n','w'])",
    "h":{".validate":NUM},"a":{".validate":NUM},
    "x":{".validate":"newData.isBoolean()"},
    "c":{".validate":f"newData.val() == ({FCU}.child('c').exists() ? {FCU}.child('c').val() : 'none')"},
    "n":{".validate":f"newData.isString() && newData.val() == ({FCU}.child('n').exists() ? {FCU}.child('n').val() : '')"},
    "w":{".validate":"newData.val() == now"},
    "$other":{".validate":False}}}
_op=_opens(_ms)
rules["rules"]["pr"]={m['id']:_pr(m['t'],_op[m['wk']]) for m in _ms}
# نسخة من مواعيد القفل اللي في القواعد: الصفحة تقفل على الأبكر، ولوحة التحكم تنبّه لو المواعيد تغيرت
if _ms:json.dump({m['id']:m['t'] for m in _ms},open(os.path.join(os.path.dirname(_pd),'lock.json'),'w'),separators=(',',':'))
if _ms:json.dump({str(w):t for w,t in _op.items()},open(os.path.join(os.path.dirname(_pd),'open.json'),'w'),separators=(',',':'))   # متى تفتح كل جولة (للصفحة)

# ── «توقّع تشكيلة ناديك» (صفحة «تشكيلتي»، قرار إبراهيم 18 نوفمبر) ──
# tp/<مباراة>/<uid> = {c: نادي المشجع، x: 11 مفتاح لاعب مفصولة بـ ~، w: وقت السيرفر}
#   يتعدل لين ساعتين قبل البداية، وينفتح مع جولة التوقعات (نفس O). النادي = بطاقة المشجع ولازم يكون طرف في المباراة.
#   النقاط يحسبها _tools/fans/build.py من التشكيلة الرسمية (tashkila/lineups.json).
TPLOCK=2*3600000
def _tp(m,O=0):
  T=m['t']-TPLOCK
  return {"$u":{
    ".read":"auth != null && auth.uid == $u",
    ".write":f"auth != null && auth.uid == $u && now < {T}"+(f" && now >= {O}" if O else ""),
    ".validate":"newData.hasChildren(['c','x','w'])",
    "c":{".validate":f"newData.isString() && newData.val() == {FCU}.child('c').val() && (newData.val() == '{m['h']}' || newData.val() == '{m['a']}')"},
    "x":{".validate":"newData.isString() && newData.val().length <= 2000 && newData.val().matches(/^[^~]+(~[^~]+){10}$/)"},
    "w":{".validate":"newData.val() == now"},
    "$other":{".validate":False}}}
rules["rules"]["tp"]={m['id']:_tp(m,_op[m['wk']]) for m in _ms}

# ── «رمز النقل» (قرار إبراهيم 18 نوفمبر): ينقل بطاقة المشجع لتلفون أو متصفح ثاني بدون تسجيل ──
# x/<sha256(الرمز)> = {u: صاحب البطاقة، c: البيانات مشفّرة بالرمز (AES-GCM)، i: IV، e: ينتهي (10 دقايق، 15 بالكثير)}
# اللي يعرف الرمز بس يوصل للمسار ويفك التشفير. ما ينقرا بعد ما ينتهي، وما في قراءة للقائمة. ينمسح بعد ما ينستخدم.
rules["rules"]["x"]={"$h":{
  ".read":"data.child('e').val() > now",
  ".write":"auth != null && (!data.exists() || data.child('u').val() == auth.uid)",
  ".validate":"$h.matches(/^[a-f0-9]{64}$/) && newData.hasChildren(['u','c','i','e'])",
  "u":{".validate":"newData.val() == auth.uid"},
  "c":{".validate":"newData.isString() && newData.val().length <= 60000"},
  "i":{".validate":"newData.isString() && newData.val().length <= 40"},
  "e":{".validate":"newData.isNumber() && newData.val() > now && newData.val() <= now + 900000"},
  "$other":{".validate":False}}}

# ── عداد الإحصائيات الخاص (موافقة إبراهيم 16 نوفمبر) ── v/<يوم>/{t,u,r,p/<قسم>,s/<أغنية>/<حدث>}
# زيادة +1 بس لكل طلب. القراءة مفتوحة مثل s و c (أرقام مجمعة بدون أي بيانات شخصية، واللوحة ما فيها تسجيل دخول Firebase).
VINC=f"newData.isNumber() && {inc}"
SECS="home|mano|predict|fans|rate|songs|tashkila|grid"
rules["rules"]["v"]={".read":True,"$d":{
  ".validate":"$d.matches(/^[1-9][0-9]{0,2}$/)",
  "t":{".write":True,".validate":VINC},"u":{".write":True,".validate":VINC},"r":{".write":True,".validate":VINC},
  "p":{"$s":{".write":True,".validate":f"$s.matches(/^({SECS})$/) && {VINC}"}},
  "s":{"$id":{"$e":{".write":True,".validate":f"$id.matches(/^[a-z0-9-]{{1,20}}$/) && $e.matches(/^(play|dl|share)$/) && {VINC}"}}},
  "$other":{".validate":False}}}

# ── «شبكة الدوري» (قرار إبراهيم 17 نوفمبر) ──
# gq/<يوم> = {r: الأندية، c: الشروط، a: {خانة: [أجوبة]}، n: رقم الشبكة} — يتقرى بس من 12 بالليل حقه، والكتابة لحساب الخدمة
# gp/<يوم>/<uid> = {c: النادي، n: عدد المحاولات (1..9)، a/<1..9> = {k: الخانة، p: اللاعب، d: اليوم، t: وقت السيرفر}، s: الثواني}
#   كل محاولة تنكتب مرة وحدة وبالترتيب (ما ينمسح الغلط)، و9 بالكثير، وفي يومها بس. الصح والغلط يحسبه build من gq.
# gc/<يوم>/<خانة>/<لاعب> و gn/<يوم>/<خانة> = عدادات الاختيارات (للنسب)، +1 بس ومع محاولة يديدة لنفس الخانة واللاعب
rules["rules"]["gq"]={str(d):{".read":f"now >= {L + (d - 1) * DAYMS}"} for d in range(1,401)}
GPU="root.child('gp').child($d).child(auth.uid)"
def _gaft(levels):
  return "newData"+".parent()"*levels+f".child('gp').child($d).child(auth.uid)"
def _gentry(levels):
  a=_gaft(levels); return f"{a}.child('a').child('' + {a}.child('n').val())"
def _gfresh(levels):
  a=_gaft(levels); return f"auth != null && ({GPU}.child('n').exists() ? {GPU}.child('n').val() : 0) + 1 == {a}.child('n').val()"
rules["rules"]["gp"]={"$d":{"$u":{
  ".read":"auth != null && auth.uid == $u",
  ".validate":"$d.matches(/^[1-9][0-9]{0,2}$/)",
  "c":{".write":"auth != null && auth.uid == $u && !data.exists()",".validate":f"newData.isString() && newData.val().matches(/^({CL})?$/)"},
  "n":{".write":"auth != null && auth.uid == $u",
       ".validate":"newData.isNumber() && newData.val() >= 1 && newData.val() <= 9 && newData.val() == (data.exists() ? data.val() : 0) + 1"
                   " && newData.parent().child('a').child('' + newData.val()).exists()"},
  "a":{"$i":{".write":"auth != null && auth.uid == $u && !data.exists()",
       ".validate":("$i.matches(/^[1-9]$/) && newData.hasChildren(['k','p','d','t']) && newData.parent().parent().child('n').val() + '' == $i"
         f" && $d == '' + newData.child('d').val() && now >= {L} + (newData.child('d').val() - 1) * {DAYMS} && now < {L} + newData.child('d').val() * {DAYMS} + {GRACE}"),
       "k":{".validate":"newData.isString() && newData.val().matches(/^[0-2][0-2]$/)"},
       "p":{".validate":"newData.isString() && newData.val().matches(/^[a-z0-9-]{1,80}$/)"},
       "d":{".validate":"newData.isNumber()"},"t":{".validate":"newData.val() == now"},
       "$other":{".validate":False}}},
  "s":{".write":"auth != null && auth.uid == $u",".validate":"newData.isNumber() && newData.val() % 1 == 0 && newData.val() >= 0 && newData.val() <= 86400"},
  "$other":{".validate":False}}}}
rules["rules"]["gc"]={".read":True,"$d":{"$k":{"$p":{
  ".write":_gfresh(4),
  ".validate":f"newData.isNumber() && {inc} && {_gentry(4)}.child('k').val() == $k && {_gentry(4)}.child('p').val() == $p"}}}}
rules["rules"]["gn"]={".read":True,"$d":{"$k":{
  ".write":_gfresh(3),
  ".validate":f"newData.isNumber() && {inc} && {_gentry(3)}.child('k').val() == $k"}}}

# ── «باص الفريق» في دوري الجماهير (قرار إبراهيم 17 نوفمبر) ──
# «تحدي الجولة»: باص نادي المشجع باتجاه ملعب مباراته، في يوم المباراة بس، ومحاولة وحدة. اللعب الحر للتدريب وما ينحسب.
# b/<يوم>/<uid> = {m: رقم المباراة، s: الملعب، r: الطريق، k: حركات اللاعب (مضغوطة)، c: نادي المشجع، d: اليوم، t: وقت السيرفر}
#   ينكتب مرة وحدة، وفي يومه، والنادي لازم يطابق بطاقة المشجع (اللي ما اختار نادي ما يدخل التحدي).
#   النتيجة ما تنقبل من التلفون: المُعيد (_tools/bus/verify.py) يتأكد إن المباراة لنادي المشجع في هاليوم وإن الملعب ملعبها،
#   ويعيد السباق من الحركات، ويكتب bv (حساب الخدمة بس).
rules["rules"]["b"]={"$d":{"$u":{
  ".read":"auth != null && auth.uid == $u",
  ".write":"auth != null && auth.uid == $u && !data.exists()",
  ".validate":("$d.matches(/^[1-9][0-9]{0,2}$/) && newData.hasChildren(['m','s','r','k','c','d','t'])"
    f" && $d == '' + newData.child('d').val() && now >= {L} + (newData.child('d').val() - 1) * {DAYMS} && now < {L} + newData.child('d').val() * {DAYMS} + {GRACE}"),
  "m":{".validate":"newData.isString() && newData.val().matches(/^[0-9]{1,9}$/)"},
  "s":{".validate":"newData.isString() && newData.val().matches(/^[a-z]{2,12}$/)"},
  "r":{".validate":"newData.isString() && newData.val().matches(/^[a-z]{2,12}_[AB]$/)"},
  "k":{".validate":"newData.isString() && newData.val().length <= 30000 && newData.val().matches(/^[0-9a-f:,]*$/)"},
  "c":{".validate":f"newData.isString() && newData.val().matches(/^({CL})$/) && newData.val() == root.child('f').child($u).child('c').val()"},
  "d":{".validate":"newData.isNumber()"},"t":{".validate":"newData.val() == now"},
  "$other":{".validate":False}}}}
rules["rules"]["bv"]={".read":True}   # نتايج المُعيد (مقروءة للكل، الكتابة لحساب الخدمة بس)
# r = سجل خاص بنهاية كل لعبة في «منو اللاعب» (فاز أو خسر، بنادي أو بدون) + بصمة جهاز مختصرة مجهولة (dv)
# الهدف: نرصد «الكشّاف» (حساب ثاني بنفس التلفون يخسر عشان يطلع الاسم، وبعدها فوز من أول محاولة). القراءة للمدير بس
rules["rules"]["r"]={".read":ISADM,"$d":{"$m":{"$u":{
   ".write":"auth != null && auth.uid == $u && !data.exists()",
   ".validate":("newData.hasChildren(['d','g','dv','t']) && $m.matches(/^(easy|pro)$/) && $d.matches(/^[0-9]{1,4}$/)"
     f" && newData.child('d').isNumber() && $d == '' + newData.child('d').val() && now >= {L} + (newData.child('d').val() - 1) * {DAYMS} && now < {L} + newData.child('d').val() * {DAYMS} + {GRACE}"),
   "d":{".validate":True},
   "g":{".validate":"newData.isNumber() && newData.val() % 1 == 0 && newData.val() >= 0 && newData.val() <= 6"},
   "dv":{".validate":"newData.isString() && newData.val().matches(/^[0-9a-f]{12}$/)"},
   "t":{".validate":"newData.val() == now"},
   "$other":{".validate":False}}}}}

json.dump(rules,open('rules.json','w'),ensure_ascii=False,separators=(',',':'))
