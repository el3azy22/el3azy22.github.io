# يطبّق _tools/position_fixes.json على قوائم «اختار تشكيلتك» (المراكز)، والجنسية الرياضية على «منو اللاعب؟»
import json,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F=json.load(open(f'{R}/_tools/position_fixes.json'))
t=json.load(open(f'{R}/tashkila/squads.json'));m=json.load(open(f'{R}/mano/data.json'))
M2={'GK':'GK','DEF':'DF','MID':'MD','FWD':'FW'};CLUBMAP={'shabab':'shababahli'}
byid={p['id']:p for p in m['players']};log=[]
for c in [t['national']]+t['clubs']:
  fx=F.get(c['id'],{})
  for p in c['p']:
    new=fx.get(str(p[0])) if not any(k.startswith('name:') for k in fx) else next((v for k,v in fx.items() if k.startswith('name:') and p[1].startswith(k[5:])),None)
    if not new or p[2]==new: continue
    log.append(f"{c['id']} #{p[0]} {p[1]}: {p[2]} -> {new}");p[2]=new
    if c['id']=='uae_nt': continue
    mc=CLUBMAP.get(c['id'],c['id'])
    mp=byid.get(p[5]) if p[5] else None
    if not mp: mp=next((x for x in m['players'] if x['c']==mc and str(x.get('no'))==str(p[0])),None)
    # «منو اللاعب؟» والشبكة يستخدمون المركز المسجل في الرابطة (اللي يشوفه المشجع في موقعها)، فالتصحيح هني لـ«اختار تشكيلتك» بس
# مراكز «منو اللاعب؟» اللي نخالف فيها الرابطة بقرار إبراهيم
for pid,pos in {k:v for k,v in F.get('_mano',{}).items() if not k.startswith('_')}.items():
  mp=byid.get(pid)
  if mp and mp['p']!=pos: log.append(f"   mano {pid}: {mp['p']} -> {pos}");mp['p']=pos
for pid,(nat,cc) in {k:v for k,v in F.get('_nat',{}).items() if not k.startswith('_')}.items():
  mp=byid.get(pid)
  if mp and (mp['nat'],mp['f'])!=(nat,cc): log.append(f"   mano {pid}: {mp['nat']} -> {nat}");mp['nat'],mp['f']=nat,cc
# توحيد إملاء الأسماء (_tools/name_fixes.json): كلمة كاملة بكلمة، في الاسم الكامل والاسم القصير
NF=json.load(open(f'{R}/_tools/name_fixes.json'));W=NF['words'];SKIP=set(NF.get('_skip',[]))
PH=NF.get('phrases',{})
def fixw(s):
  if not isinstance(s,str): return s
  for a,b in PH.items(): s=s.replace(a,b)   # عبارة كاملة (مثلاً «عبد الله» ← «عبدالله») قبل الكلمات
  return ' '.join(W.get(w,w) for w in s.split(' '))
skip_ids=set();nlog=0
for c in [t['national']]+t['clubs']:
  for p in c['p']:
    if f"{c['id']}#{p[0]}" in SKIP:
      if p[5]: skip_ids.add(p[5])
      continue
    for i in (1,6):
      if len(p)>i:
        v=fixw(p[i])
        if v!=p[i]: p[i]=v;nlog+=1
for mp in m['players']:
  if mp['id'] in skip_ids: continue
  v=fixw(mp['n'])
  if v!=mp['n']: mp['n']=v;nlog+=1
log.append(f'   names: {nlog}')
# مركز واحد لكل لاعب في كل المنصة: «تشكيلتي» تاخذ مركز «منو اللاعب؟» (الرابطة + إعلانات الأندية + قرارات إبراهيم)
R2={v:k for k,v in M2.items()};ulog=0
for c in t['clubs']:
  for p in c['p']:
    mp=byid.get(p[5]) if len(p)>5 and p[5] else None
    if mp and R2.get(mp['p']) and p[2]!=R2[mp['p']]: p[2]=R2[mp['p']];ulog+=1
log.append(f'   tashkila<-mano: {ulog}')
json.dump(t,open(f'{R}/tashkila/squads.json','w'),ensure_ascii=False,separators=(',',':'))
json.dump(m,open(f'{R}/mano/data.json','w'),ensure_ascii=False,separators=(',',':'))
print('\n'.join(log));print(len([l for l in log if not l.startswith('   ')]),'fixes')
