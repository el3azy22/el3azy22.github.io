# مؤثرات انتقال مولّدة (بدون حقوق): whoosh كبير، swish صغير، chime للفوز
import numpy as np,soundfile as sf,scipy.signal as ss,os
SR=48000;O=os.path.dirname(os.path.abspath(__file__))+'/sfx/';rng=np.random.default_rng(7)
def sweep_noise(dur,f0,f1,q=1.2,shape=(0.6,)):
    n=int(dur*SR);x=rng.standard_normal(n);out=np.zeros(n);B=512
    for i in range(0,n,B):
        t=i/n;fc=f0*(f1/f0)**t;bw=fc/q
        b,a=ss.butter(2,[max(30,fc-bw/2)/(SR/2),min(SR/2-100,fc+bw/2)/(SR/2)],'band');out[i:i+B]=ss.lfilter(b,a,x[i:i+B])
    t=np.linspace(0,1,n);pk=shape[0];env=np.where(t<pk,(t/pk)**2,((1-t)/(1-pk))**1.5)
    y=out*env;return y/np.abs(y).max()
def st(y,w=0.004):
    d=int(w*SR);l=np.concatenate([np.zeros(d),y])[:len(y)];return np.stack([y,l*0.9],1)
whoosh=sweep_noise(0.6,300,4000,shape=(0.62,))*0.5
swish=sweep_noise(0.28,1200,6000,q=1.5,shape=(0.45,))*0.32
t=np.arange(int(0.9*SR))/SR
chime=sum(a*np.sin(2*np.pi*f*t)*np.exp(-t*k) for f,a,k in [(1318.5,.5,5),(1975.5,.35,6),(2637,.15,8)])
chime[int(0.12*SR):]+=0;chime=chime/np.abs(chime).max()*0.35
for n,y in [('whoosh',whoosh),('swish',swish),('chime',chime)]: sf.write(O+n+'.wav',st(y),SR)
print('ok')
