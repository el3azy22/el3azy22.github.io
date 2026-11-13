import numpy as np,soundfile as sf,noisereduce as nr,pyloudnorm as pyln,subprocess
x,sr=sf.read('raw.wav')
H=int(sr*.01);fr=x[:len(x)//H*H].reshape(-1,H);e=10*np.log10((fr**2).mean(1)+1e-12)
# noise profile: frames between -75 and -50 dB (room tone / breaths excluded from speech)
q=np.where((e>-75)&(e<-50))[0];noise=np.concatenate([fr[i] for i in q[:400]]) if len(q)>20 else None
y=nr.reduce_noise(y=x,sr=sr,y_noise=noise,stationary=True,prop_decrease=0.75,n_fft=2048) if noise is not None else x
act=e>-42;m=[];i=0;n=len(act)
while i<n:
  if act[i]:
    j=i
    while j<n and act[j]:j+=1
    if m and i-m[-1][1]<8:m[-1][1]=j
    else:m.append([i,j])
    i=j
  else:i+=1
m=[s for s in m if s[1]-s[0]>3]
g=np.zeros(n)
for a,b in m:g[max(0,a-8):min(n,b+15)]=1
# smooth ramps 30ms
k=np.ones(3)/3;g=np.convolve(g,k,'same')
G=np.repeat(g,H);G=np.pad(G,(0,len(y)-len(G)))
y=y*G
sf.write('/tmp/_g.wav',y,sr)
af=("highpass=f=80,equalizer=f=280:t=q:w=1.2:g=-2.5,equalizer=f=3800:t=q:w=1.0:g=2.5,"
    "deesser=i=0.35,acompressor=threshold=-22dB:ratio=3:attack=8:release=140:makeup=4,alimiter=limit=0.89")
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','/tmp/_g.wav','-af',af,'-ar','48000','/tmp/_g2.wav'],check=True)
z,sr=sf.read('/tmp/_g2.wav');mt=pyln.Meter(sr);z=z*10**((-16-mt.integrated_loudness(z))/20)
pk=np.abs(z).max()
if pk>0.84:z*=0.84/pk
sf.write('voice_clean.wav',z,sr);print('segments',[(round(a/100,2),round(b/100,2)) for a,b in m]);print('len',len(z)/sr)
