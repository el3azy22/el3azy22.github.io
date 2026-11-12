import re,json,subprocess,time,html
clubs=['ajman','al-ain','al-dhafra','al-jazira','al-nasr','al-wahda','al-wasl','bani-yas','hatta','kalba','khorfakkan','shabab-alahli','sharjah','united']
COMP='b8785e20-745f-11f1-82d0-f556dfffd44c'; PRO='d304d980-e5e8-11ea-a63c-112a991a4e3f'
def get(u):
  r=subprocess.run(['curl','-sS','-m','30','-H','X-Requested-With: XMLHttpRequest',u],capture_output=True,text=True);return r.stdout
def parse(h):
  out=[];cur=None
  for blk in re.split(r'(?=<a href="https://uaeproleague\.ae/(?:en|ar)/player/)|(?=<h\d[^>]*class="[^"]*title)',h):
    m=re.match(r'<a href="(https://uaeproleague\.ae/(?:en|ar)/player/([^/]+)/[^"]+)"',blk)
    if not m: continue
    t=lambda p:(re.search(p,blk,re.S) or [None,None])[1]
    nat=re.search(r'countrySubWrap.*?<div class="left">(.*?)<span class="citizen-info">\s*(.*?)\s*</span>',blk,re.S)
    flag=re.search(r'/flags/([A-Z]{2,3})\.png',blk)
    out.append(dict(slug=m.group(2),url=m.group(1),num=(t(r'jerseyNum">\s*([^<]*?)\s*<') or '').strip(),
      img=t(r'profileWrap.*?<img src="([^"]+)"'),flag=flag.group(1) if flag else '',
      nat=html.unescape(re.sub(r'<[^>]+>','',nat.group(1)).strip()) if nat else '',status=nat.group(2).strip() if nat else '',
      age=t(r'(?:Age|العمر)\s*:?\s*(\d+)'),pos=(t(r'class="position">\s*(.*?)\s*<') or '').strip(),
      name=html.unescape((t(r'class="fullname">\s*(.*?)\s*<') or '').strip()),
      apps=re.findall(r'<div class="right">\s*([^<]*?)\s*</div>',blk)))
  return out
data={}
for c in clubs:
  page=get(f'https://uaeproleague.ae/en/clubs/{c}')
  uid=re.search(r'clubs/([0-9a-f-]{36})/content/squad',page).group(1)
  res={}
  for lang in ['en','ar']:
    j=get(f'https://uaeproleague.ae/{lang}/clubs/{uid}/content/squad?seasonCompetition={COMP}&person_status_id={PRO}')
    res[lang]=parse(json.loads(j)['squad'])
    time.sleep(1)
  ar={p['slug']:p for p in res['ar']}
  for p in res['en']:
    a=ar.get(p['slug'],{});p['name_ar']=a.get('name','');p['nat_ar']=a.get('nat','');p['pos_ar']=a.get('pos','')
  data[c]=dict(uid=uid,players=res['en'])
  print(c,uid,len(res['en']),len(res['ar']))
json.dump(data,open('squads.json','w'),ensure_ascii=False,indent=1)
