# python3 add_sfx.py mix.wav out.wav "whoosh@6.0,swish@9.5,..."  (الوقت = لحظة الذروة تقريباً)
import sys,numpy as np,soundfile as sf,os,pyloudnorm as pyln
m,sr=sf.read(sys.argv[1]);D=os.path.dirname(os.path.abspath(__file__))+'/sfx/'
G={'whoosh':0.55,'swish':0.6,'chime':0.5};PK={'whoosh':0.37,'swish':0.12,'chime':0.0}
for it in sys.argv[3].split(','):
    n,t=it.split('@');y,_=sf.read(D+n+'.wav');s=int((float(t)-PK[n])*sr);s=max(0,s);e=min(len(m),s+len(y))
    m[s:e]+=y[:e-s]*G[n]
mt=pyln.Meter(sr);m*=10**((-14-mt.integrated_loudness(m))/20);pk=np.abs(m).max()
if pk>0.89:m*=0.89/pk
sf.write(sys.argv[2],m,sr);print('ok')
