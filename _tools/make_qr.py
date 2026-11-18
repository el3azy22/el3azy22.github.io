# باركود العازي بهوية المنصة: python3 make_qr.py URL out.png
# نقاط كحلية مدورة على عاجي، عيون الزوايا إطار ذهبي غامق وبؤبؤ كحلي مدور (الإطار المدور ما يقراه OpenCV فخليناه حاد)، وصورة العازي في دائرة عاجية بإطار ذهبي.
# بعد الرسم نتأكد إنه ينقرا (pyzbar + OpenCV) على الحجم الكبير وعلى 120px، وإلا يوقف بخطأ.
import os, sys
import qrcode
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IVORY, NAVY, GOLD, GOLD_D = (255, 245, 229), (7, 29, 43), (215, 180, 101), (150, 112, 44)


def make(url, out, box=28, border=2, dot=0.43, lf=0.17, eyr=(0, 0, 0.95), sq=False, verify=True):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=0)
    q.add_data(url); q.make(fit=True)
    M = q.get_matrix(); n = len(M)
    S = 4                                      # نرسم ×4 ونصغّر عشان الحواف تطلع ناعمة
    b = box * S; W = (n + 2 * border) * b
    im = Image.new('RGB', (W, W), IVORY); d = ImageDraw.Draw(im)
    o = border * b
    eyes = [(0, 0), (0, n - 7), (n - 7, 0)]
    in_eye = lambda r, c: any(er <= r < er + 7 and ec <= c < ec + 7 for er, ec in eyes)
    # فراغ الشعار في النص (دائرة)
    cx = cy = W / 2; lr = n * b * lf
    for r in range(n):
        for c in range(n):
            if not M[r][c] or in_eye(r, c):
                continue
            x, y = o + c * b + b / 2, o + r * b + b / 2
            if ((x - cx) ** 2 + (y - cy) ** 2) ** .5 < lr + b * 0.9:
                continue
            rr = b * dot
            (d.rounded_rectangle([x - rr, y - rr, x + rr, y + rr], radius=int(rr * .45), fill=NAVY) if sq else d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=NAVY))
    for er, ec in eyes:
        x, y = o + ec * b, o + er * b
        d.rounded_rectangle([x, y, x + 7 * b - 1, y + 7 * b - 1], radius=int(b * eyr[0]), fill=GOLD_D)
        d.rounded_rectangle([x + b, y + b, x + 6 * b - 1, y + 6 * b - 1], radius=int(b * eyr[1]), fill=IVORY)
        d.rounded_rectangle([x + 2 * b, y + 2 * b, x + 5 * b - 1, y + 5 * b - 1], radius=int(b * eyr[2]), fill=NAVY)
    # الشعار: دائرة عاجية بإطار ذهبي
    ring = int(b * 0.32)
    d.ellipse([cx - lr, cy - lr, cx + lr, cy + lr], fill=GOLD)
    d.ellipse([cx - lr + ring, cy - lr + ring, cx + lr - ring, cy + lr - ring], fill=IVORY)
    logo = Image.open(os.path.join(ROOT, 'mano', 'assets', 'logo.png')).convert('RGBA')
    logo = logo.crop(logo.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox())   # نشيل الفراغ الشفاف حول الصورة
    s = int((lr - ring) * 2 * 0.80); logo = logo.resize((int(s * logo.width / max(logo.size)), int(s * logo.height / max(logo.size))), Image.LANCZOS)
    im.paste(logo, (int(cx - logo.width / 2), int(cy - logo.height / 2)), logo)
    im = im.resize((W // S, W // S), Image.LANCZOS)
    im.save(out, optimize=True)
    if verify:
        check(im, url)
    print(out, im.size, 'ينقرا ✓')


def check(im, url):
    from pyzbar.pyzbar import decode
    import cv2, numpy as np
    for size in (im.width, 600, 400, 300, 240, 160, 120):
        x = im.resize((size, size), Image.LANCZOS)
        a = [r.data.decode() for r in decode(x)]
        g = cv2.QRCodeDetector().detectAndDecode(np.array(x.convert('RGB'))[:, :, ::-1])[0]
        if url not in a or g != url:
            raise SystemExit(f'❌ الباركود ما ينقرا على {size}px (zbar={a}, opencv={g!r})')


if __name__ == '__main__':
    make(sys.argv[1], sys.argv[2])
