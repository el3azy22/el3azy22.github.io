# يطابق نبرة تسجيل يديد على تسجيل مرجعي (EQ مطابقة طيفية): python3 match_tone.py ref.wav target.wav out.wav
import sys,numpy as np,soundfile as sf,scipy.signal as ss,pyloudnorm as pyln
ref,sr=sf.read(sys.argv[1]);tg,sr2=sf.read(sys.argv[2]);assert sr==sr2
def ltas(x):
    f,t,Z=ss.stft(x,sr,nperseg=4096);P=np.abs(Z)**2;e=P.sum(0);keep=e>np.percentile(e,40)  # الكلام بس
    return f,10*np.log10(P[:,keep].mean(1)+1e-12)
f,R=ltas(ref);_,T=ltas(tg)
d=R-T;d-=np.interp(1000,f,d)  # نثبّت 1kHz
# تنعيم 1/3 أوكتاف
sm=np.array([d[(f>=fc/2**(1/6))&(f<=fc*2**(1/6))].mean() if fc>40 else d[i] for i,fc in enumerate(f)])
sm=np.clip(sm,-9,9);sm[f<60]=0;sm[f>12000]=np.interp(12000,f,sm)
taps=ss.firwin2(2047,f/(sr/2),10**(sm/20))
y=ss.fftconvolve(tg,taps,mode='same')
m=pyln.Meter(sr);y*=10**((m.integrated_loudness(ref)-m.integrated_loudness(y))/20)
pk=np.abs(y).max()
if pk>0.84:y*=0.84/pk
sf.write(sys.argv[3],y,sr)
for name,x in [('ref',ref),('before',tg),('after',y)]:
    _,L=ltas(x);b=lambda a,b_:L[(f>=a)&(f<b_)].mean()
    print(f"{name:7s} low(80-250) {b(80,250)-b(800,1200):+.1f}  mid(250-800) {b(250,800)-b(800,1200):+.1f}  high(3k-8k) {b(3000,8000)-b(800,1200):+.1f} dB rel 1kHz")
