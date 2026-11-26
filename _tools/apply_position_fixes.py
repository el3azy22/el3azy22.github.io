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
# نظام المراكز (قرار إبراهيم 27 نوفمبر 2026):
# المركز الأساسي p = قرار إبراهيم/إعلان النادي (_mano) ← اللي بدا فيه أكثر هالموسم (3 مباريات أو أكثر) ← مسيرته ← التسجيل المحلي pr
# المركز الثاني p2 = أول مركز يختلف عن الأساسي من: هالموسم/المسيرة/التسجيل (3 بدايات أو أكثر) يختلف عن الأساسي. الحارس ما له مركز ثاني
# المركز التفصيلي pd (ظهير أيسر، جناح أيمن...) من هالموسم أو المسيرة، بشرط يكون من نفس الخط
CP=f'{R}/_tools/sync/career_pos.json';SP=f'{R}/_tools/sync/season_pos.json'
CAR=json.load(open(CP,encoding='utf8')) if os.path.exists(CP) else {}
SEA=json.load(open(SP,encoding='utf8')) if os.path.exists(SP) else {}
MANO={k:v for k,v in F.get('_mano',{}).items() if not k.startswith('_')}
TMR={'Goalkeeper':None,'Centre-Back':'cb','Left-Back':'lb','Right-Back':'rb','Defensive Midfield':'dm','Central Midfield':'cm','Attacking Midfield':'am',
     'Left Midfield':'lw','Right Midfield':'rw','Left Winger':'lw','Right Winger':'rw','Centre-Forward':'st','Second Striker':'ss'}
RC={'cb':'DF','lb':'DF','rb':'DF','lwb':'DF','rwb':'DF','dm':'MD','cm':'MD','am':'MD','lm':'MD','rm':'MD','lw':'FW','rw':'FW','st':'FW','ss':'FW'}
RAR={'cb':'قلب دفاع','lb':'ظهير أيسر','rb':'ظهير أيمن','lwb':'ظهير أيسر','rwb':'ظهير أيمن','dm':'ارتكاز','am':'صانع ألعاب','lm':'وسط أيسر','rm':'وسط أيمن',
     'lw':'جناح أيسر','rw':'جناح أيمن','st':'رأس حربة','ss':'مهاجم ثاني'}
plog={'mano':0,'season':0,'career':0,'reg':0}
import time as _t
NOW=int(_t.time()*1000)
for mp in m['players']:
  OLD=(mp.get('p'),mp.get('p2'),mp.get('pd'))
  pid=mp['id'];reg=mp.get('pr') or mp['p'];mp['pr']=reg
  car=CAR.get(pid,[None,None]);cc=car[1]
  se=SEA.get(pid) or {'n':0,'cat':{},'role':{}}
  sc=None
  if se['n']>=3:
    top=max(se['cat'].values());tied=[k for k,v in se['cat'].items() if v==top]
    sc=next((x for x in (cc,reg) if x in tied),sorted(tied)[0])
  src,p=next(((a,b) for a,b in (('mano',MANO.get(pid)),('season',sc),('career',cc),('reg',reg)) if b),('reg',reg))
  plog[src]+=1
  if mp['p']!=p: log.append(f"   {src} {pid}: {mp['p']} -> {p}")
  mp['p']=p;mp['ps']=src
  p2=None
  if p!='GK':
    cands=[k for k,v in sorted(se['cat'].items(),key=lambda x:-x[1]) if v>=3]+[cc,reg]   # الأقرب للواقع أول: هالموسم ← المسيرة ← التسجيل
    p2=next((x for x in cands if x and x!=p and x!='GK'),None)
  if p2: mp['p2']=p2
  else: mp.pop('p2',None)
  rl=None
  if p!='GK':
    rs=sorted(((v,k) for k,v in se['role'].items() if RC.get(k)==p),reverse=True)
    if se['n']>=3 and rs: rl=rs[0][1]
    elif TMR.get(car[0]) and RC.get(TMR[car[0]])==p: rl=TMR[car[0]]
  if rl in RAR: mp['pd']=RAR[rl]
  else: mp.pop('pd',None)
  # تثبيت اليوم (قرار إبراهيم 27 نوفمبر): لو المركز تغيّر، اليوم الحالي يكمل على القديم ويتغيّر من بداية اليوم القادم
  # (صفحة «منو اللاعب؟» تقرا pz لو وقت التغيير بعد بداية اليوم)، عشان التلميح والألوان ما يتغيرون وسط اليوم
  NEW=(mp.get('p'),mp.get('p2'),mp.get('pd'))
  if NEW!=OLD and OLD[0]:
    pz=mp.get('pz')
    if not (pz and NOW-pz['t']<86400000):   # تغيير ثاني بنفس اليوم: نخلي أول نسخة
      mp['pz']={'p':OLD[0],'p2':OLD[1],'pd':OLD[2],'t':NOW}
  elif mp.get('pz') and NOW-mp['pz']['t']>2*86400000:
    mp.pop('pz')
log.append(f'   main position sources: {plog}')
# سجل المراكز (قرار إبراهيم 27 نوفمبر: النظام لكل التحديات): كل تغيير ينحفظ بوقته، عشان التحدي يحسب
# بمركز اللاعب وقت المباراة، فمحد ينظلم لو تغيّر مركز لاعبه بعد ما اختاره (الخماسي وأي تحدي قادم)
import time
HP=f'{R}/_tools/sync/pos_hist.json'
H=json.load(open(HP,encoding='utf8')) if os.path.exists(HP) else {}
now=int(time.time()*1000)
for mp in m['players']:
  h=H.setdefault(mp['id'],[])
  if not h: h.append([0,mp['p']])
  elif h[-1][1]!=mp['p']: h.append([now,mp['p']])
json.dump(H,open(HP,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
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
