# يسحب صور اللاعبين الرسمية من موقع رابطة المحترفين (بعد scrape.py) ويحفظها webp 240px في mano/assets/p
import json,subprocess,os,io
from PIL import Image
OUT='/home/claude/el3azy22.github.io/mano/assets/p';os.makedirs(OUT,exist_ok=True)
s=json.load(open('squads.json'))
for c in s.values():
  for p in c['players']:
    if 'dummy' in p['img'] or os.path.exists(f"{OUT}/{p['slug']}.webp"): continue
    b=subprocess.run(['curl','-sS','-m','40',p['img']],capture_output=True).stdout
    try: Image.open(io.BytesIO(b)).convert('RGBA').resize((240,240),Image.LANCZOS).save(f"{OUT}/{p['slug']}.webp",'WEBP',quality=82)
    except Exception as e: print(p['slug'],e)
