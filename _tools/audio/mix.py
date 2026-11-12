# خلط صوت العازي مع الموسيقى: الصوت -16 LUFS، الموسيقى أخفض بـ18dB وقت الكلام و10dB بين الجمل
# python3 mix.py voice.wav music.m4a out.wav total_seconds voice_offset
import sys,subprocess,numpy as np,soundfile as sf,pyloudnorm as pyln
v,mu,out,T,off=sys.argv[1],sys.argv[2],sys.argv[3],float(sys.argv[4]),float(sys.argv[5])
SR=48000
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',mu,'-ac','2','-ar',str(SR),'/tmp/_mus.wav'],check=True)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',v,'-ac','1','-ar',str(SR),'/tmp/_voc.wav'],check=True)
m,_=sf.read('/tmp/_mus.wav');x,_=sf.read('/tmp/_voc.wav')
N=int(T*SR);voc=np.zeros(N);o=int(off*SR);voc[o:o+len(x)]=x[:max(0,N-o)]
reps=int(np.ceil(N/len(m)));m=np.tile(m,(reps,1))[:N]
meter=pyln.Meter(SR);m=m*10**((-16-meter.integrated_loudness(m))/20)
# voice activity envelope (attack 60ms, release 500ms)
H=int(0.01*SR);fr=np.abs(voc[:N//H*H]).reshape(-1,H).max(1);act=(fr>10**(-40/20)).astype(float)
env=np.zeros_like(act);a,r=1-np.exp(-1/6),1-np.exp(-1/50)
for i in range(1,len(act)): env[i]=env[i-1]+(a if act[i]>env[i-1] else r)*(act[i]-env[i-1])
gdb=-10+env*(-8)  # -10dB in gaps, -18dB under speech
g=np.repeat(10**(gdb/20),H);g=np.pad(g,(0,N-len(g)),constant_values=g[-1])
# fades
fi=int(0.5*SR);fo=int(1.5*SR);g[:fi]*=np.linspace(0,1,fi);g[-fo:]*=np.linspace(1,0,fo)
mix=m*g[:,None]+voc[:,None]
mix*=10**((-14-meter.integrated_loudness(mix))/20)
pk=np.abs(mix).max()
if pk>0.89: mix*=0.89/pk
sf.write(out,mix,SR)
sp=act>0.5;vs=np.repeat(sp,H)[:N]
def rms(z): return 10*np.log10((z**2).mean()+1e-12)
print('voice-vs-music under speech: %.1f dB'%(rms(voc[:len(vs)][vs])-rms((m*g[:,None]).mean(1)[:len(vs)][vs])))
