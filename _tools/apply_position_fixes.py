# يطبّق _tools/position_fixes.json على قوائم «اختار تشكيلتك» و«منو اللاعب؟»
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
    if mp and mp['p']!=M2[new]: log.append(f"   mano {mp['id']}: {mp['p']} -> {M2[new]}");mp['p']=M2[new]
for pid,(nat,cc) in {k:v for k,v in F.get('_nat',{}).items() if not k.startswith('_')}.items():
  mp=byid.get(pid)
  if mp and (mp['nat'],mp['f'])!=(nat,cc): log.append(f"   mano {pid}: {mp['nat']} -> {nat}");mp['nat'],mp['f']=nat,cc
json.dump(t,open(f'{R}/tashkila/squads.json','w'),ensure_ascii=False,separators=(',',':'))
json.dump(m,open(f'{R}/mano/data.json','w'),ensure_ascii=False,separators=(',',':'))
print('\n'.join(log));print(len([l for l in log if not l.startswith('   ')]),'fixes')
