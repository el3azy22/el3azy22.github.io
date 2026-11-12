import json,re,random,datetime
d=json.load(open('squads.json'))
CK={'ajman':'ajman','al-ain':'ain','al-dhafra':'dhafra','al-jazira':'jazira','al-nasr':'nasr','al-wahda':'wahda','al-wasl':'wasl','bani-yas':'baniyas','hatta':'hatta','kalba':'kalba','khorfakkan':'khorfakkan','shabab-alahli':'shababahli','sharjah':'sharjah','united':'united'}
CN={'ajman':'عجمان','ain':'العين','dhafra':'الظفرة','jazira':'الجزيرة','nasr':'النصر','wahda':'الوحدة','wasl':'الوصل','baniyas':'بني ياس','hatta':'حتا','kalba':'كلباء','khorfakkan':'خورفكان','shababahli':'شباب الأهلي','sharjah':'الشارقة','united':'يونايتد'}
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
P=[];fixes=[]
for ck,v in d.items():
  for p in v['players']:
    na=clean_ar(p['name_ar']) or clean_en(p['name'])
    if na!=re.sub(r'\s+',' ',p['name_ar'].strip()): fixes.append((p['name_ar'],na))
    nat=NATFIX.get(p['nat_ar'],NATFIX.get(p['nat'],p['nat_ar']))
    P.append(dict(id=p['slug'],n=na,e=clean_en(p['name']),c=CK[ck],p=p['pos'],nat=nat,f=p['flag'],a=int(p['age']) if p['age'] else None,no=int(p['num']) if p['num'].isdigit() else None,ap=ap(p),src=p['url']))
# answer pool
pool=[p for p in P if p['ap']>=5 and p['nat'] and p['a'] and p['no']]
rnd=random.Random(2026)
pool.sort(key=lambda p:-p['ap']);top=pool[:60];rest=pool[60:]
rnd.shuffle(top);rnd.shuffle(rest);seq=top+rest
order=[]
while seq:
  for i,p in enumerate(seq):
    recent=[q['c'] for q in order[-4:]]; rp=[q['p'] for q in order[-2:]]
    if p['c'] not in recent and not (len(rp)==2 and rp[0]==rp[1]==p['p']): order.append(seq.pop(i));break
  else: order.append(seq.pop(0))
FIRST=['Soufian Rahimi','Christian Benteke','Mehdi Taremi','Laba Kodjo','Malcom Olivieira','Khalid Eisa','Igor Coronado']
first=[next(p for p in order if p['e']==n) for n in FIRST]
order=first+[p for p in order if p not in first]
out=dict(updated=datetime.date.today().isoformat(),start='2026-11-17',clubs=CN,players=[{k:v for k,v in p.items() if k!='src'} for p in P],schedule=[p['id'] for p in order])
json.dump(out,open('/home/claude/el3azy22.github.io/mano/data.json','w'),ensure_ascii=False,separators=(',',':'))
json.dump(P,open('players_full.json','w'),ensure_ascii=False,indent=1)
print(len(P),'players',len(order),'days');print('fixes',fixes)
print([ (p['n'],p['c']) for p in order[:10]])
