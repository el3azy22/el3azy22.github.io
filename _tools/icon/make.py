from PIL import Image,ImageDraw,ImageFilter,ImageChops
import math
S=1024
logo=Image.open('/home/claude/icon/logo_orig.png').convert('RGBA');logo=logo.crop(logo.getbbox())
GOLD2=(246,227,174);GOLD=(215,180,101);GOLD3=(176,138,62);NAVY=(7,29,43);NAVY2=(22,64,90)
def bg(glow=True):
    im=Image.new('RGB',(S,S),NAVY);px=im.load()
    for y in range(S):
        for x in range(S):
            t=y/S;c=[int(NAVY2[i]*(1-t)+NAVY[i]*t) for i in range(3)]
            if glow:
                d=math.hypot(x-S*.5,y-S*.42)/(S*.55);g=max(0,1-d)**2*.45
                c=[int(c[i]*(1-g)+GOLD[i]*g) for i in range(3)]
            px[x,y]=tuple(c)
    return im
def sadu(w,h,col):
    L=Image.new('RGBA',(w,h),(0,0,0,0));d=ImageDraw.Draw(L);step=h*1.5
    x=0
    while x<w:
        d.line([(x,h*.92),(x+step/2,h*.2),(x+step,h*.92)],fill=col,width=max(2,int(h*.11)))
        cx=x+step/2;cy=h*.72;r=h*.18;d.polygon([(cx,cy-r),(cx+r,cy),(cx,cy+r),(cx-r,cy)],fill=col);x+=step
    return L
def ring(im,inset,width):
    m=Image.new('L',(S,S),0);d=ImageDraw.Draw(m);d.rounded_rectangle([inset,inset,S-inset,S-inset],radius=int(S*.225)-inset,outline=255,width=width)
    gold=Image.new('RGB',(S,S));gp=gold.load()
    for y in range(S):
        t=y/S;c=[int(GOLD2[i]*(1-t)+GOLD3[i]*t) for i in range(3)]
        for x in range(S):gp[x,y]=tuple(c)
    im.paste(gold,(0,0),m)
def put_logo(im,scale,cy):
    lw=int(S*scale);lh=int(logo.height*lw/logo.width)
    if lh>S*.86:lh=int(S*.86);lw=int(logo.width*lh/logo.height)
    L=logo.resize((lw,lh),Image.LANCZOS)
    sh=Image.new('RGBA',(S,S),(0,0,0,0));a=L.split()[3];blk=Image.new('RGBA',L.size,(0,0,0,150));blk.putalpha(a.point(lambda v:v*150//255))
    x=(S-lw)//2;y=int(cy-lh/2);sh.paste(blk,(x,y+14),blk);sh=sh.filter(ImageFilter.GaussianBlur(18))
    im.paste(sh,(0,0),sh);im.paste(L,(x,y),L)
# A: navy + glow + gold ring + sadu bottom
A=bg();ring(A,34,14);put_logo(A,.80,S*.47);sd=sadu(int(S*.5),34,GOLD+(220,));A.paste(sd,((S-sd.width)//2,S-110),sd);A.save('A.png')
# B: bigger logo, no ring, sadu top & bottom subtle
B=bg();put_logo(B,.92,S*.5);B.save('B.png')
# C: gold ring + bigger logo
C=bg();ring(C,30,18);put_logo(C,.86,S*.5);C.save('C.png')
# preview: rounded mask at 180 and 60 on a phone-like bg
def rnd(p,size):
    im=Image.open(p).resize((size,size),Image.LANCZOS);m=Image.new('L',(size,size),0);ImageDraw.Draw(m).rounded_rectangle([0,0,size,size],radius=int(size*.225),fill=255);im.putalpha(m);return im
pv=Image.new('RGB',(3*400,520),(40,44,52))
for i,p in enumerate('ABC'):
    pv.paste(rnd(p+'.png',300),(i*400+50,20),rnd(p+'.png',300));s=rnd(p+'.png',120);pv.paste(s,(i*400+60,370),s);t=rnd(p+'.png',60);pv.paste(t,(i*400+220,400),t)
pv.save('preview.png')
