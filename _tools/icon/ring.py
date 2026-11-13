from PIL import Image,ImageDraw,ImageFilter
import math,json,sys
exec(open(__file__.replace('ring.py','make.py')).read().split('# A:')[0])
C={'ain':[.83,1.197],'wahda':[.91,1.176],'jazira':[1,1],'shababahli':[1.037,1.074],'sharjah':[.979,1.133],'wasl':[.973,1.165],'nasr':[1,1],'baniyas':[1.234,.681],'ajman':[1.154,1.016],'kalba':[.995,1],'khorfakkan':[1.048,1.069],'dhafra':[.92,1.106],'hatta':[.989,1.122],'united':[.995,.995]}
def crests(im,R,size,cy=S*.5,start=-90):
    for i,(k,f) in enumerate(C.items()):
        a=math.radians(start+i*360/14);x=S/2+R*math.cos(a);y=cy+R*math.sin(a)
        c=Image.open(f'/home/claude/el3azy22.github.io/mano/assets/{k}.png').convert('RGBA');c=c.crop(c.getbbox())
        w,h=int(size*f[0]),int(size*f[1]);c=c.resize((w,h),Image.LANCZOS)
        im.paste(c,(int(x-w/2),int(y-h/2)),c)
def variant(name,R,cs,ls,inset=30):
    im=bg();ring(im,inset,16)
    # faint orbit circle
    o=Image.new('RGBA',(S,S));ImageDraw.Draw(o).ellipse([S/2-R,S/2-R,S/2+R,S/2+R],outline=(215,180,101,70),width=4);im.paste(o,(0,0),o)
    crests(im,R,cs);put_logo(im,ls,S*.5);im.save(name)
variant('D.png',S*.385,S*.105,.56)
variant('E.png',S*.40,S*.09,.60)
def rnd(p,size):
    im=Image.open(p).resize((size,size),Image.LANCZOS);m=Image.new('L',(size,size),0);ImageDraw.Draw(m).rounded_rectangle([0,0,size,size],radius=int(size*.225),fill=255);im.putalpha(m);return im
pv=Image.new('RGB',(2*400,520),(40,44,52))
for i,p in enumerate('DE'):
    a=rnd(p+'.png',300);pv.paste(a,(i*400+50,20),a);s=rnd(p+'.png',120);pv.paste(s,(i*400+60,370),s);t=rnd(p+'.png',60);pv.paste(t,(i*400+220,400),t)
pv.save('preview2.png')
