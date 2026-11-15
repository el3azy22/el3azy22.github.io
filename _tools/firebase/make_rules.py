import json
import os
L=int(os.environ.get("L","1794859200000")); DAYMS=86400000
CL="ajman|ain|dhafra|jazira|nasr|wahda|wasl|baniyas|hatta|kalba|khorfakkan|shababahli|sharjah|united"
R="newData.parent().parent().parent().parent()"  # root-after from s/$d/$m/$f
P=lambda base:f"{base}.child('p').child($d).child($m).child(auth.uid)"
inc="((!data.exists() && newData.val() == 1) || newData.val() == data.val() + 1)"
fresh=lambda after:f"auth != null && !root.child('p').child($d).child($m).child(auth.uid).exists() && {P(after)}.exists()"
g=lambda after:f"{P(after)}.child('g').val()"
s_after="newData.parent().parent().parent().parent()"
c_after="newData.parent().parent().parent().parent().parent()"
rules={"rules":{
 ".read":False,".write":False,
 "p":{"$d":{"$m":{"$u":{
   ".write":"auth != null && auth.uid == $u && !data.exists()",
   ".validate":("newData.hasChildren(['g','c','d']) && ($m == 'easy' || $m == 'pro') && $d.matches(/^[0-9]{1,4}$/)"
     " && newData.child('d').isNumber() && $d == '' + newData.child('d').val()"
     f" && now >= {L} + (newData.child('d').val() - 1) * {DAYMS} && now < {L} + (newData.child('d').val() + 1) * {DAYMS}"
     " && newData.child('g').isNumber() && newData.child('g').val() >= 0 && newData.child('g').val() <= 6"
     f" && newData.child('c').isString() && newData.child('c').val().matches(/^({CL})?$/)"
     " && newData.parent().parent().parent().parent().child('s').child($d).child($m).child('n').val() == (root.child('s').child($d).child($m).child('n').exists() ? root.child('s').child($d).child($m).child('n').val() : 0) + 1"),
   "d":{".validate":True},"g":{".validate":True},"c":{".validate":True},"$other":{".validate":False}}}}},
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
   "r":{"$p":{".validate":f"$p.matches({PID}) && newData.isNumber() && newData.val() >= 1 && newData.val() <= 10 && newData.val() % 1 == 0"}},
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
rules["rules"].update({
 "f":{"$u":{
   ".read":"auth != null && auth.uid == $u",
   ".write":"auth != null && auth.uid == $u",
   ".validate":(f"newData.hasChildren(['c','t']) && newData.child('c').isString() && newData.child('c').val().matches(/^({FCL})$/)"
     " && (data.child('c').val() == newData.child('c').val() || newData.parent().parent().child('fc').child(newData.child('c').val()).val() == (root.child('fc').child(newData.child('c').val()).exists() ? root.child('fc').child(newData.child('c').val()).val() : 0) + 1)"
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
   ".validate":(f"$c.matches(/^({FCL})$/) && newData.isNumber() && ("
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
def _pr(T):
  return {".read":f"now >= {T}","$u":{
    ".read":"auth != null && auth.uid == $u",
    ".write":f"auth != null && auth.uid == $u && now < {T}",
    ".validate":"newData.hasChildren(['h','a','c','n','w'])",
    "h":{".validate":NUM},"a":{".validate":NUM},
    "x":{".validate":"newData.isBoolean()"},
    "c":{".validate":f"newData.val() == ({FCU}.child('c').exists() ? {FCU}.child('c').val() : 'none')"},
    "n":{".validate":f"newData.isString() && newData.val() == ({FCU}.child('n').exists() ? {FCU}.child('n').val() : '')"},
    "w":{".validate":"newData.val() == now"},
    "$other":{".validate":False}}}
rules["rules"]["pr"]={m['id']:_pr(m['t']) for m in _ms}
# نسخة من مواعيد القفل اللي في القواعد: الصفحة تقفل على الأبكر، ولوحة التحكم تنبّه لو المواعيد تغيرت
if _ms:json.dump({m['id']:m['t'] for m in _ms},open(os.path.join(os.path.dirname(_pd),'lock.json'),'w'),separators=(',',':'))

json.dump(rules,open('rules.json','w'),ensure_ascii=False,separators=(',',':'))
