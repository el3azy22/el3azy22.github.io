# تنظيف صوت العازي: قص الوقفات الطويلة + إزالة ضوضاء خفيفة + EQ + ضغط + ضبط الارتفاع
# python3 voice_chain.py in.wav out.wav [max_pause=0.45] [lufs=-16]
import sys,subprocess,numpy as np,soundfile as sf,noisereduce as nr,pyloudnorm as pyln
src,dst=sys.argv[1],sys.argv[2];MAXP=float(sys.argv[3]) if len(sys.argv)>3 else 0.45;LUFS=float(sys.argv[4]) if len(sys.argv)>4 else -16
x,sr=sf.read(src)
if x.ndim>1:x=x.mean(1)
# noise profile from quietest 10% frames
H=int(sr*0.02);fr=x[:len(x)//H*H].reshape(-1,H);e=10*np.log10((fr**2).mean(1)+1e-12)
q=np.argsort(e)[:max(10,len(e)//10)];noise=np.concatenate([fr[i] for i in sorted(q)])
y=nr.reduce_noise(y=x,sr=sr,y_noise=noise,stationary=True,prop_decrease=0.8,n_fft=2048)
# tighten long pauses (keep MAXP, 20ms crossfade)
floor=np.percentile(e,10);thr=floor+12
act=e>thr
segs=[];i=0;n=len(act)
while i<n:
  j=i
  while j<n and act[j]==act[i]: j+=1
  segs.append((act[i],i*H,j*H));i=j
out=[];xf=int(0.02*sr)
for a,s,t in segs:
  seg=y[s:t]
  if not a and (t-s)>MAXP*sr:
    k=int(MAXP*sr/2);seg=np.concatenate([seg[:k],seg[-k:]])
  out.append(seg)
y=np.concatenate(out+[y[len(act)*H:]])
sf.write('/tmp/_vc_tmp.wav',y,sr)
# EQ + de-ess + compression + limiter via ffmpeg
af=("highpass=f=75,equalizer=f=280:t=q:w=1.2:g=-2.5,equalizer=f=3800:t=q:w=1.0:g=2.5,"
    "deesser=i=0.35,acompressor=threshold=-22dB:ratio=3:attack=8:release=140:makeup=4,alimiter=limit=0.89")
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','/tmp/_vc_tmp.wav','-af',af,'-ar',str(sr),'/tmp/_vc_tmp2.wav'],check=True)
z,sr=sf.read('/tmp/_vc_tmp2.wav');m=pyln.Meter(sr);g=LUFS-m.integrated_loudness(z)
z=z*10**(g/20);pk=np.abs(z).max()
if pk>0.84: z=z*0.84/pk
sf.write(dst,z,sr);print('ok',round(len(z)/sr,2),'s',round(pyln.Meter(sr).integrated_loudness(z),1),'LUFS')
