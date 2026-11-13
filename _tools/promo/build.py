# يركّب الفيديو النهائي: لقطات record.py بتوقيتها → 30fps ثابت + الموسيقى والمؤثرات من timeline.json + صورة مراجعة
#   python3 build.py /home/claude/promo/frames /home/claude/promo/el3azy-promo.mp4 [voice.wav]
# لو عطيته ملف صوت (التعليق) يخفض الموسيقى تحته تلقائي.
import json,os,sys,subprocess,bisect,numpy as np,soundfile as sf,pyloudnorm as pyln
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__));SFX=os.path.join(HERE,'..','audio','sfx')
TL=json.load(open(os.path.join(HERE,'timeline.json'),encoding='utf-8'))
FR,OUT=sys.argv[1],sys.argv[2];VOICE=sys.argv[3] if len(sys.argv)>3 else None
WORK=os.path.dirname(os.path.abspath(OUT));FPS=TL['fps'];T=TL['duration'];SR=48000;N=int(round(T*FPS))
# ---------- الصورة ----------
d=json.load(open(f'{FR}/ts.json'));ts=[t-d['t0']+d.get('from',0) for t in d['ts']]
pick=lambda t:max(0,bisect.bisect_right(ts,t)-1)
with open(f'{WORK}/frames.txt','w') as f:
  for n in range(N): f.write(f"file '{os.path.abspath(FR)}/{pick((n+.5)/FPS):05d}.jpg'\nduration {1/FPS:.6f}\n")
# ---------- الصوت ----------
def load(p):
  w=f'{WORK}/_tmp.wav';subprocess.run(['ffmpeg','-y','-v','error','-i',p,'-ar',str(SR),'-ac','2',w],check=True);x,_=sf.read(w,dtype='float32');os.remove(w);return x
M=TL['music'];mus=np.zeros((int(T*SR),2),'float32');cache={}
for g in M['segments']:
  p=os.path.join(HERE,g['file']);x=cache.get(p);
  if x is None:x=cache[p]=load(p)
  a=int(g['at']*SR);e=int(min(T,g.get('until',T))*SR);src=x[int(g['trackStart']*SR):int(g['trackStart']*SR)+e-a].copy()
  k=int(.03*SR);src[:k]*=np.linspace(0,1,k)[:,None];src[-k:]*=np.linspace(1,0,k)[:,None]   # قص ناعم عند أطراف المقطع
  mus[a:a+len(src)]+=src
meter=pyln.Meter(SR);mus*=10**((M['lufs']-meter.integrated_loudness(mus))/20)
mix=mus.copy()
for s in TL['scenes']:
  if s.get('sfx'):
    x=load(os.path.join(SFX,s['sfx']+'.wav'))*10**(M.get('sfxGainDb',-9)/20);a=int(max(0,s['start']-.08)*SR);x=x[:len(mix)-a];mix[a:a+len(x)]+=x
if VOICE:   # التعليق: -16 LUFS والموسيقى تنخفض تحته
  v=load(VOICE)[:len(mix)];v*=10**((-16-meter.integrated_loudness(v))/20)
  env=np.abs(v).max(1);w=int(.25*SR);env=np.convolve(env,np.ones(w)/w,'same');duck=1-.78*np.clip(env/.02,0,1);mix[:len(v)]*=duck[:,None];mix[:len(v)]+=v
fi,fo=int(M['fadeIn']*SR),int(M['fadeOut']*SR);mix[:fi]*=np.linspace(0,1,fi)[:,None];mix[-fo:]*=(np.linspace(1,0,fo)**1.5)[:,None]
pk=np.abs(mix).max();
if pk>.89:mix=np.tanh(mix/pk*1.2)/np.tanh(1.2)*.89   # حد ناعم للقمم
sf.write(f'{WORK}/audio.wav',mix,SR)
print('audio: %.1f LUFS, peak %.1f dBFS'%(meter.integrated_loudness(mix),20*np.log10(np.abs(mix).max())))
subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',f'{WORK}/frames.txt','-i',f'{WORK}/audio.wav','-r',str(FPS),'-vf','scale=1080:1920:flags=lanczos,format=yuv420p',
  '-c:v','libx264','-preset','veryfast','-crf','17','-c:a','aac','-b:a','192k','-movflags','+faststart','-t',str(T),OUT],check=True)
# ---------- صورة المراجعة: لقطة من كل مشهد ----------
S=TL['scenes'];tiles=[]
for i,s in enumerate(S):
  end=S[i+1]['start'] if i+1<len(S) else T;t=s['start']+(end-s['start'])*s.get('thumb',.82)
  tiles.append(Image.open(f"{FR}/{pick(t):05d}.jpg").convert('RGB').resize((540,960),Image.LANCZOS))
cs=Image.new('RGB',(540*4+50,960*2+30),(7,29,43))
for i,im in enumerate(tiles):cs.paste(im,(10+(i%4)*550,10+(i//4)*970))
cs.save(f'{WORK}/contact.png');print('ok',OUT)
