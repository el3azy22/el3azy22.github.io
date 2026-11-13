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
json.dump(rules,open('rules.json','w'),ensure_ascii=False,indent=1)
