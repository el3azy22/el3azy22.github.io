# باركود بشعار العازي في النص: python3 make_qr.py URL out.png
import sys,qrcode
from PIL import Image,ImageDraw
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
url,out=sys.argv[1],sys.argv[2]
q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=20,border=2);q.add_data(url);q.make()
im=q.make_image(image_factory=StyledPilImage,module_drawer=RoundedModuleDrawer(),back_color=(255,245,229),front_color=(7,29,43)).convert('RGBA')
W=im.size[0];s=int(W*0.26);pad=int(s*0.08)
logo=Image.open('/home/claude/el3azy22.github.io/mano/assets/logo.png').convert('RGBA');logo.thumbnail((s-2*pad,s-2*pad),Image.LANCZOS)
bg=Image.new('RGBA',(s,s),(0,0,0,0));d=ImageDraw.Draw(bg);d.rounded_rectangle([0,0,s-1,s-1],radius=s//5,fill=(255,245,229,255))
bg.paste(logo,((s-logo.size[0])//2,(s-logo.size[1])//2),logo)
im.paste(bg,((W-s)//2,(W-s)//2),bg);im.convert('RGB').save(out,optimize=True);print(out,im.size)
