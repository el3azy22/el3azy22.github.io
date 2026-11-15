"""صورة لاعب من موقع اتحاد الكرة بنفس مقاس صور الرابطة (لما الرابطة ما عندها صورة).
python3 _tools/sync/fa_photo.py <player_id في الاتحاد> <slug>
يحتاج: pip install "rembg[cpu]" opencv-python-headless pillow numpy
الخطوات: يشيل الخلفية (u2net_human_seg، ولو القميص أبيض على خلفية بيضا يضيف isnet ويعبّي الكتوف)،
وبعدين يحط الوجه بنفس الحجم والمكان (عرض الوجه 100 من 240، مركزه 121،85.5)، والقميص يوصل لين تحت.
"""
import io, os, sys, urllib.request
import cv2, numpy as np
from PIL import Image
from rembg import remove, new_session
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
K, DY, DX = 1.0386, -0.0012, -0.0013
D = cv2.CascadeClassifier(os.path.join(HERE, 'haar_default.xml')); A = cv2.CascadeClassifier(os.path.join(HERE, 'haar_alt2.xml'))


def det(C, g, mn):
    f = [r for r in C.detectMultiScale(g, 1.05, mn, minSize=(60, 60)) if r[1] + r[3] / 2 < g.shape[0] * 0.5]
    return max(f, key=lambda r: r[2]) if f else None


def make(pid, slug):
    raw = urllib.request.urlopen(urllib.request.Request(f'https://www.fanet.ae/UAEFA/img.ashx?type=player&id={pid}', headers={'User-Agent': 'Mozilla/5.0'}), timeout=40).read()
    pil = Image.open(io.BytesIO(raw)).convert('RGB'); rgb = np.array(pil)
    g = cv2.cvtColor(rgb[:, :, ::-1], cv2.COLOR_BGR2GRAY)
    d = det(D, g, 5); a = None if d is not None else det(A, cv2.equalizeHist(g), 3)
    if d is not None: cx, cy, w = d[0] + d[2] / 2, d[1] + d[3] / 2, d[2]
    elif a is not None: w = a[2] * K; cx = a[0] + a[2] / 2 + DX * a[2]; cy = a[1] + a[3] / 2 + DY * a[2]
    else: raise SystemExit('ما لقينا الوجه في الصورة')
    al = np.array(remove(pil, session=new_session('u2net_human_seg')))[:, :, 3]; H, W = al.shape
    if al[int(H * 0.9):, int(W * 0.35):int(W * 0.65)].mean() < 200:  # قميص أبيض انمسح مع الخلفية
        al = np.maximum(al, np.array(remove(pil, session=new_session('isnet-general-use')))[:, :, 3]); al = al.copy()
        lo, hi = W, -1
        for y in range(int(cy + 0.75 * w), H):
            xs = np.where(al[y] > 20)[0]
            if len(xs): lo = min(lo, xs[0]); hi = max(hi, xs[-1])
            if hi > lo: al[y, lo:hi + 1] = 255
        al = cv2.GaussianBlur(al, (3, 3), 0)
    cut = Image.fromarray(np.dstack([rgb, al]))
    rows = np.where(al.max(axis=1) > 40)[0]; Hb = rows[-1] + 1 - 2
    Z = 240 * w / 100; fy = 85.5
    bot = lambda fy, Z: cy + (240 - fy) / 240 * Z
    if bot(fy, Z) > Hb: fy = min(95, 240 - (Hb - cy) * 240 / Z)
    if bot(fy, Z) > Hb: Z = (Hb - cy) * 240 / (240 - fy)
    L = cx - 121 / 240 * Z; T = cy - fy / 240 * Z
    big = Image.new('RGBA', (int(np.ceil(Z)) + 2,) * 2, (0, 0, 0, 0)); big.paste(cut, (int(round(-L)), int(round(-T))), cut)
    out = os.path.join(ROOT, 'mano', 'assets', 'p', slug + '.webp')
    big.crop((0, 0, int(round(Z)), int(round(Z)))).resize((240, 240), Image.LANCZOS).save(out, 'WEBP', quality=82)
    print('saved', out)


if __name__ == '__main__':
    make(sys.argv[1], sys.argv[2])
