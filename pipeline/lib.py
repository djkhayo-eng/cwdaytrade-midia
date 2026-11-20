import numpy as np, cv2, subprocess, json, math, os, functools
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

W, H, FPS = 1080, 1920, 30
BASE = os.path.dirname(os.path.abspath(__file__))
ANTON = os.path.join(BASE, "fonts/anton-latin-400-normal.ttf")
MONT = os.path.join(BASE, "fonts/montserrat-latin-800-normal.ttf")
MONTR = os.path.join(BASE, "fonts/montserrat-latin-400-normal.ttf")
GREEN = (0, 230, 118); GREEN2 = (0, 150, 80)
RED = (255, 72, 72); RED2 = (190, 30, 40)
GOLD = (255, 200, 60); GOLD2 = (190, 120, 20)
WHITE = (255, 255, 255); GREY = (150, 160, 170); YEL = (255, 214, 0)
LEAD, SPD = 0.10, 1.15

# ---------------- timing ----------------
WORDS = json.load(open("words.json")) if os.path.exists("words.json") else []  # gerado por align.py no diretório de trabalho
for w in WORDS:
    w["S"] = LEAD + w["s"] / SPD; w["E"] = LEAD + w["e"] / SPD
PARA = {}
for w in WORDS: PARA.setdefault(w["p"], []).append(w)
def WT(p, k): return PARA[p][k]["S"]
def WE(p, k): return PARA[p][k]["E"]

def ease(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def ease_io(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def back(x, s=1.70158):
    x = min(max(x, 0.0), 1.0); x -= 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, t): return a + (b - a) * t
def clamp01(x): return min(max(x, 0.0), 1.0)

# ---------------- compositing ----------------
def blend(dst, src, x, y, alpha=1.0):
    """dst HxWx3 uint8 ; src hxwx4 uint8 RGBA ; top-left x,y (may be off-canvas)"""
    if alpha <= 0.003 or src is None: return
    h, w = src.shape[:2]; x = int(round(x)); y = int(round(y))
    x0, y0 = max(x, 0), max(y, 0); x1, y1 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0: return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4].astype(np.float32) * (alpha / 255.0)
    d = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (d + (s[..., :3].astype(np.float32) - d) * a).astype(np.uint8)

def blend_c(dst, src, cx, cy, alpha=1.0, scale=1.0, rot=0.0):
    if src is None: return
    if abs(scale - 1) > 1e-3 or abs(rot) > 1e-3:
        src = xform(src, scale, rot)
    blend(dst, src, cx - src.shape[1] / 2, cy - src.shape[0] / 2, alpha)

def xform(src, scale=1.0, rot=0.0):
    h, w = src.shape[:2]
    if abs(rot) < 1e-3:
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        return cv2.resize(src, (nw, nh), interpolation=cv2.INTER_LINEAR if scale > 1 else cv2.INTER_AREA)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, scale)
    c, s = abs(M[0, 0]), abs(M[0, 1]); nw, nh = int(h * s + w * c), int(h * c + w * s)
    M[0, 2] += nw / 2 - w / 2; M[1, 2] += nh / 2 - h / 2
    return cv2.warpAffine(src, M, (nw, nh), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))

def pil2np(im): return np.asarray(im.convert("RGBA")).copy()

@functools.lru_cache(maxsize=64)
def font(path, size): return ImageFont.truetype(path, size)

# ---------------- 3D text ----------------
@functools.lru_cache(maxsize=256)
def text3d(text, size, top=WHITE, bot=(205, 210, 220), side=(30, 34, 44), depth=None, f=ANTON,
           glow=None, shadow=0.65, stroke=0):
    fo = font(f, size)
    depth = depth if depth is not None else max(6, size // 11)
    l, t, r, b = fo.getbbox(text, stroke_width=stroke)
    tw, th = r - l, b - t
    pad = depth * 2 + 50
    Wc, Hc = tw + 2 * pad, th + 2 * pad
    mask = Image.new("L", (Wc, Hc), 0)
    ImageDraw.Draw(mask).text((pad - l, pad - t), text, font=fo, fill=255, stroke_width=stroke, stroke_fill=255)
    out = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    if glow:
        g = mask.filter(ImageFilter.GaussianBlur(size * 0.22))
        gl = Image.new("RGBA", (Wc, Hc), glow + (0,)); gl.putalpha(g.point(lambda v: int(v * 0.9)))
        out = Image.alpha_composite(out, gl)
    if shadow:
        sh = Image.new("L", (Wc, Hc), 0); sh.paste(mask, (int(depth * 0.9) + 10, int(depth * 1.3) + 16))
        sh = sh.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * shadow))
        sl = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0)); sl.putalpha(sh)
        out = Image.alpha_composite(out, sl)
    # extrusion
    for i in range(depth, 0, -1):
        k = i / depth
        col = tuple(int(c * (0.55 + 0.45 * (1 - k))) for c in side)
        layer = Image.new("RGBA", (Wc, Hc), col + (255,))
        m2 = Image.new("L", (Wc, Hc), 0); m2.paste(mask, (int(round(i * 0.45)), int(round(i * 0.9))))
        layer.putalpha(m2); out = Image.alpha_composite(out, layer)
    # bevel highlight
    hl = Image.new("RGBA", (Wc, Hc), (255, 255, 255, 0)); m3 = Image.new("L", (Wc, Hc), 0)
    m3.paste(mask, (-2, -2)); hl.putalpha(m3.point(lambda v: int(v * 0.55))); out = Image.alpha_composite(out, hl)
    # gradient face
    grad = np.zeros((Hc, Wc, 4), np.uint8)
    yy = np.clip((np.arange(Hc) - pad) / max(th, 1), 0, 1)[:, None]
    for c in range(3): grad[..., c] = (top[c] + (bot[c] - top[c]) * yy).astype(np.uint8)
    grad[..., 3] = np.asarray(mask)
    face = Image.fromarray(grad, "RGBA")
    out = Image.alpha_composite(out, face)
    # specular sweep line near top
    a = np.asarray(out).copy()
    return a

@functools.lru_cache(maxsize=512)
def label(text, size=34, fg=WHITE, bg=(12, 14, 18), bga=215, padx=22, pady=12, f=MONT, border=None, radius=None):
    fo = font(f, size); l, t, r, b = fo.getbbox(text)
    w, h = r - l + 2 * padx, b - t + 2 * pady
    im = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rad = radius if radius is not None else h // 2
    if bga > 0: d.rounded_rectangle([4, 4, w + 3, h + 3], rad, fill=bg + (bga,), outline=(border + (255,)) if border else None, width=3 if border else 0)
    d.text((4 + padx - l, 4 + pady - t), text, font=fo, fill=fg)
    return pil2np(im)

@functools.lru_cache(maxsize=256)
def plain(text, size, fg=WHITE, f=MONT, stroke=0, sfill=(0, 0, 0)):
    fo = font(f, size); l, t, r, b = fo.getbbox(text, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 8, b - t + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t), text, font=fo, fill=fg, stroke_width=stroke, stroke_fill=sfill)
    return pil2np(im)

# ---------------- grading ----------------
def _lut():
    x = np.arange(256) / 255.0
    s = x + 0.10 * np.sin(2 * np.pi * x) * (-0.5)  # gentle S
    s = np.clip(0.5 + (x - 0.5) * 1.12, 0, 1) * 0.6 + s * 0.4
    r = np.clip(s * 1.03 + 0.01, 0, 1); g = np.clip(s * 1.0, 0, 1); b = np.clip(s * 0.96 + 0.035 * (1 - s), 0, 1)
    return [(v * 255).astype(np.uint8) for v in (r, g, b)]
LUT = _lut()
def grade(img, bright=1.0):
    out = np.empty_like(img)
    for c in range(3): out[..., c] = cv2.LUT(img[..., c], LUT[c])
    if bright != 1.0: out = cv2.convertScaleAbs(out, alpha=bright)
    return out
_yy, _xx = np.mgrid[0:H, 0:W]
VIG = (1 - 0.55 * np.clip(((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.6)) ** 2, 0, 1) ** 1.3).astype(np.float32)[..., None]
del _yy, _xx
def vignette(img, k=1.0):
    v = VIG if k == 1.0 else (1 - (1 - VIG) * k)
    return (img.astype(np.float32) * v).astype(np.uint8)

def cover(img, w=W, h=H, fx=0.5, fy=0.5):
    ih, iw = img.shape[:2]; s = max(w / iw, h / ih)
    nw, nh = int(round(iw * s)), int(round(ih * s))
    r = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    x0 = int((nw - w) * fx); y0 = int((nh - h) * fy)
    return r[y0:y0 + h, x0:x0 + w]

def zoom_frame(img, s, cx=0.5, cy=0.5, dx=0, dy=0):
    """img is canvas-size or bigger base; returns WxH view zoomed by s around (cx,cy) of img"""
    ih, iw = img.shape[:2]
    base = max(W / iw, H / ih)
    sc = base * s
    M = np.array([[sc, 0, W / 2 - cx * iw * sc + dx], [0, sc, H / 2 - cy * ih * sc + dy]], np.float32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def load_img(path):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return np.asarray(im).copy()

# ---------------- video reader ----------------
class Vid:
    def __init__(self, path, start=0.0, w=W, h=H, speed=1.0, fx=0.5, fy=0.5):
        self.path, self.start, self.w, self.h, self.speed = path, start, w, h, speed
        self.fx, self.fy = fx, fy; self.p = None; self.idx = -1; self.last = None
    def _open(self, i):
        if self.p: self.p.kill()
        t = self.start + i / FPS * self.speed
        vf = f"setpts=PTS/{self.speed},fps={FPS},scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h}:(iw-{self.w})*{self.fx}:(ih-{self.h})*{self.fy}"
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-stream_loop", "-1", "-ss", f"{t:.3f}", "-i", self.path, "-vf", vf,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10 ** 8)
        self.idx = i - 1
    def get(self, t):
        i = max(0, int(t * FPS))
        if self.p is None or i <= self.idx - 1 or i > self.idx + 60: self._open(i)
        n = self.w * self.h * 3
        while self.idx < i:
            b = self.p.stdout.read(n)
            if len(b) < n: break
            self.last = np.frombuffer(b, np.uint8).reshape(self.h, self.w, 3); self.idx += 1
        return self.last
    def close(self):
        if self.p: self.p.kill(); self.p = None

def blur_bg(small, bright=0.5, sigma=3):
    b = cv2.GaussianBlur(small, (0, 0), sigma) if sigma > 0 else small
    b = cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
    return grade(b, bright)

# ---------------- candles ----------------
def candle_sprite(o, h, l, c, ymap, x, w, col, a=1.0):
    pass

def draw_candle(d, x, w, o, h, l, c, ymap, kind=None, alpha=255, glow_d=None):
    """d: ImageDraw on RGBA panel. kind: None->by o/c ; 'grey'"""
    up = c >= o
    if kind == "grey": body, edge = (92, 102, 114), (60, 66, 76)
    elif up: body, edge = GREEN, GREEN2
    else: body, edge = RED, RED2
    yo, yc, yh, yl = ymap(o), ymap(c), ymap(h), ymap(l)
    top, bot = min(yo, yc), max(yo, yc)
    if bot - top < 4: top, bot = (top + bot) / 2 - 2, (top + bot) / 2 + 2
    ww = max(3, w // 9)
    d.rounded_rectangle([x - ww / 2, yh, x + ww / 2, yl], ww / 2, fill=edge + (alpha,))
    d.rounded_rectangle([x - w / 2, top, x + w / 2, bot], 7, fill=edge + (alpha,))
    d.rounded_rectangle([x - w / 2 + 3, top + 2, x + w / 2 - 3, bot - 2], 6, fill=body + (alpha,))
    hl = tuple(min(255, int(v + (255 - v) * 0.45)) for v in body)
    if bot - top > 10:
        d.rounded_rectangle([x - w / 2 + 7, top + 5, x - w / 2 + 7 + max(4, w // 6), bot - 5], 3, fill=hl + (int(alpha * 0.8),))
    if glow_d is not None and kind != "grey":
        glow_d.rounded_rectangle([x - w / 2 - 6, top - 6, x + w / 2 + 6, bot + 6], 10, fill=body + (int(alpha * 0.9),))
        glow_d.rounded_rectangle([x - ww, yh, x + ww, yl], ww, fill=body + (int(alpha * 0.6),))

def dashed_line(d, p0, p1, col, width=3, dash=14, gap=10):
    x0, y0 = p0; x1, y1 = p1; L = math.hypot(x1 - x0, y1 - y0)
    if L < 1: return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L; s = 0
    while s < L:
        e = min(s + dash, L)
        d.line([x0 + ux * s, y0 + uy * s, x0 + ux * e, y0 + uy * e], fill=col, width=width); s = e + gap

def dashed_rect(d, box, col, width=3):
    x0, y0, x1, y1 = box
    for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        dashed_line(d, a, b, col, width)

def arrow(d, p0, p1, col, width=5, head=18):
    d.line([p0, p1], fill=col, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    pts = [p1, (p1[0] - head * math.cos(ang - 0.45), p1[1] - head * math.sin(ang - 0.45)),
           (p1[0] - head * math.cos(ang + 0.45), p1[1] - head * math.sin(ang + 0.45))]
    d.polygon(pts, fill=col)

def persp(img, ry=0.0, rx=0.0, scale=1.0):
    """fake 3D tilt: ry,rx in degrees"""
    h, w = img.shape[:2]; f = 1400.0
    pts = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]], np.float32)
    ay, ax = math.radians(ry), math.radians(rx); out = []
    for X, Y in pts:
        x1 = X * math.cos(ay); z1 = X * math.sin(ay)
        y2 = Y * math.cos(ax) - z1 * math.sin(ax); z2 = Y * math.sin(ax) + z1 * math.cos(ax)
        k = f / (f + z2) * scale; out.append([x1 * k, y2 * k])
    out = np.array(out, np.float32)
    mn = out.min(0); mx = out.max(0); out -= mn
    M = cv2.getPerspectiveTransform(pts - pts.min(0), out)
    sz = (int(mx[0] - mn[0]) + 2, int(mx[1] - mn[1]) + 2)
    return cv2.warpPerspective(img, M, sz, flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))

def motion_blur(img, k, horiz=True):
    k = int(k) | 1
    if k < 3: return img
    small = cv2.resize(img, (W // 2, H // 2))
    ker = np.zeros((k, k), np.float32)
    if horiz: ker[k // 2, :] = 1.0 / k
    else: ker[:, k // 2] = 1.0 / k
    return cv2.resize(cv2.filter2D(small, -1, ker), (W, H))
