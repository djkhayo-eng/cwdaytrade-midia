"""Modelo de vídeo motivacional CW Trader (estilo: cenas cinematográficas escuras + frase falada,
palavras de destaque em itálico serifado, logo discreto). Uso: python3 make_m.py info|stills t1,t2|render a b out.mp4
Precisa no diretório: words.json (align.py) e chunks.json (frases da legenda)."""
import sys, os, json, math, time, subprocess, functools
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
PIPE = os.environ.get("PIPELINE", "/home/claude/cwdaytrade-midia/pipeline")
W, H, FPS = 1080, 1920, 30
F_SANS = os.path.join(PIPE, "fonts/montserrat-600.ttf")
F_SERIF = os.path.join(PIPE, "fonts/playfair-600-italic.ttf")
LEAD = 0.4
WORDS = json.load(open("words.json"))
for w in WORDS: w["S"] = LEAD + w["s"]; w["E"] = LEAD + w["e"]
PARA = {}
for w in WORDS: PARA.setdefault(w["p"], []).append(w)
NP = len(PARA)
SPEC = json.load(open("chunks.json"))   # {"chunks": [[p, i0, i1, ["palavra_destaque",...]], ...], "scenes": [[path, start, fx], ...]}
CH = SPEC["chunks"]; SCN = SPEC["scenes"]
SC = [0.0] + [PARA[p][0]["S"] - 0.35 for p in range(1, NP)]
T_LAST = PARA[NP - 1][-1]["E"]
DUR = T_LAST + 2.6
XF = 0.45

def ease(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def clamp01(x): return min(max(x, 0.0), 1.0)
@functools.lru_cache(maxsize=32)
def font(p, s): return ImageFont.truetype(p, s)

# ---- grade: escuro, frio, cinematográfico ----
_yy, _xx = np.mgrid[0:H, 0:W]
VIG = (1 - 0.62 * np.clip(((_xx - W / 2) / (W * 0.6)) ** 2 + ((_yy - H / 2) / (H * 0.58)) ** 2, 0, 1) ** 1.2).astype(np.float32)[..., None]
x = np.arange(256) / 255.0
base = np.clip((x - 0.5) * 1.22 + 0.5, 0, 1) ** 1.28
LUTS = [np.clip(base * k + o * (1 - base), 0, 1) for k, o in ((0.84, 0.0), (0.97, 0.025), (1.08, 0.07))]
LUTS = [(l * 255).astype(np.uint8) for l in LUTS]
BLUR = {}
def moody(img, blur=0):
    if blur: img = cv2.GaussianBlur(img, (0, 0), blur)
    f = img.astype(np.float32); m = f[::8, ::8].mean(); f *= min(1.0, 92.0 / max(m, 1))
    g = f.mean(2, keepdims=True); f = g + (f - g) * 0.78
    f = np.clip(f, 0, 255).astype(np.uint8)
    out = np.empty_like(f)
    for c in range(3): out[..., c] = cv2.LUT(f[..., c], LUTS[c])
    return (out.astype(np.float32) * VIG * 0.9).astype(np.uint8)

class Vid:
    def __init__(s, path, start, fx=0.5):
        s.path, s.start, s.fx = path, start, fx; s.p = None; s.idx = -1; s.last = None
    def _open(s, i):
        if s.p: s.p.kill()
        vf = f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}:(iw-{W})*{s.fx}:(ih-{H})/2"
        s.p = subprocess.Popen(["ffmpeg", "-v", "error", "-stream_loop", "-1", "-ss", f"{s.start + i / FPS:.3f}", "-i", s.path, "-vf", vf,
                                "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10 ** 8)
        s.idx = i - 1
    def get(s, t):
        i = max(0, int(t * FPS))
        if s.p is None or i < s.idx or i > s.idx + 60: s._open(i)
        n = W * H * 3
        while s.idx < i:
            b = s.p.stdout.read(n)
            if len(b) < n: break
            s.last = np.frombuffer(b, np.uint8).reshape(H, W, 3); s.idx += 1
        return s.last
VIDS = {}
def scene_frame(p, t):
    path, st, fx = SCN[p][:3]; bl = SCN[p][3] if len(SCN[p]) > 3 else 0
    if path.lower().endswith((".jpg", ".jpeg", ".png")):
        if p not in VIDS:
            im = np.asarray(Image.open(path).convert("RGB")); ih, iw = im.shape[:2]; s = max(W / iw, H / ih)
            im = cv2.resize(im, (int(iw * s) + 1, int(ih * s) + 1)); x0 = int((im.shape[1] - W) * fx); y0 = (im.shape[0] - H) // 2
            VIDS[p] = im[y0:y0 + H, x0:x0 + W]
        fr = VIDS[p]
    else:
        if p not in VIDS: VIDS[p] = Vid(path, st, fx)
        fr = VIDS[p].get(max(0, t - SC[p] + XF))
    t0 = SC[p]; t1 = SC[p + 1] if p + 1 < NP else DUR
    u = clamp01((t - t0) / max(0.1, t1 - t0)); z = 1.0 + 0.06 * u
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
    return moody(cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT), bl)

# ---- legenda estilo "frase": sans + destaque itálico serifado ----
SANS, SERIF = 62, 100
def clean(w): return w.strip(".,:;!?…").lower()
@functools.lru_cache(maxsize=256)
def layout(ci):
    p, i0, i1, emph = CH[ci]; emph = set(e.lower() for e in emph)
    ws = PARA[p][i0:i1 + 1]; items = []
    for k, w in enumerate(ws):
        txt = w["w"]; em = clean(txt) in emph
        f = font(F_SERIF, SERIF) if em else font(F_SANS, SANS)
        items.append((txt, f, em, f.getlength(txt), w["S"]))
    sp = 18; lines = [[]]; lw = 0
    for it in items:
        if lines[-1] and lw + sp + it[3] > 900: lines.append([]); lw = 0
        lines[-1].append(it); lw += (sp if lw else 0) + it[3]
    return lines
def draw_chunk(fr, ci, t):
    s = CH_T[ci][0]; e = CH_T[ci][1]
    fade_out = 1 - clamp01((t - e + 0.25) / 0.25)
    lines = layout(ci); LH = 128
    im = Image.new("RGBA", (W, LH * len(lines) + 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sh = Image.new("L", im.size, 0); sd = ImageDraw.Draw(sh)
    y = 40
    for line in lines:
        tw = sum(i[3] for i in line) + 18 * (len(line) - 1); x = (W - tw) / 2
        base = y + 100
        for (txt, f, em, ww, ws) in line:
            a = clamp01((t - ws + 0.08) / 0.28)
            if a > 0:
                asc = f.getmetrics()[0]; dy = (1 - ease(a)) * 14
                col = (255, 255, 255, int(255 * a)) if not em else (255, 236, 200, int(255 * a))
                sd.text((x, base - asc + dy + 4), txt, font=f, fill=int(200 * a))
                d.text((x, base - asc + dy), txt, font=f, fill=col)
            x += ww + 18
        y += LH
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0)); shadow.putalpha(sh.filter(ImageFilter.GaussianBlur(14)))
    im = Image.alpha_composite(shadow, im)
    a = np.asarray(im).copy(); a[..., 3] = (a[..., 3] * fade_out).astype(np.uint8)
    y0 = int(H * 0.44 - a.shape[0] / 2)
    blend(fr, a, 0, y0)
def blend(dst, src, x, y):
    h, w = src.shape[:2]; x0, y0 = max(x, 0), max(y, 0); x1, y1 = min(x + w, W), min(y + h, H)
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]; al = s[..., 3:4].astype(np.float32) / 255
    d = dst[y0:y1, x0:x1].astype(np.float32); dst[y0:y1, x0:x1] = (d + (s[..., :3] - d) * al).astype(np.uint8)
CH_T = []
for ci, (p, i0, i1, em) in enumerate(CH):
    s = PARA[p][i0]["S"] - 0.05
    if ci + 1 < len(CH):
        np_, j0 = CH[ci + 1][0], CH[ci + 1][1]; e = min(PARA[np_][j0]["S"] - 0.08, PARA[p][i1]["E"] + 0.9)
    else: e = DUR - 0.6
    CH_T.append((s, e))

_logo = None
def logo():
    global _logo
    if _logo is None:
        f = font(F_SANS, 30); txt = "CW TRADER"; sp = 6
        wid = sum(f.getlength(c) + sp for c in txt)
        im = Image.new("RGBA", (int(wid) + 40, 50), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 0
        for c in txt:
            d.text((x, 6), c, font=f, fill=(255, 255, 255, 235)); x += f.getlength(c) + sp
        d.ellipse([x + 4, 6, x + 16, 18], fill=(255, 200, 60, 255))
        _logo = np.asarray(im).copy()
    return _logo

BAND = (1 - 0.38 * np.exp(-((np.arange(H) - H * 0.44) / (H * 0.12)) ** 2)).astype(np.float32)[:, None, None]
def frame(t):
    p = 0
    for q in range(NP - 1, -1, -1):
        if t >= SC[q]: p = q; break
    fr = scene_frame(p, t)
    if p + 1 < NP and t > SC[p + 1] - XF:   # crossfade para a próxima cena
        k = (t - (SC[p + 1] - XF)) / XF
        nxt = scene_frame(p + 1, t)
        fr = cv2.addWeighted(fr, 1 - k, nxt, k, 0)
    if t < 0.6: fr = (fr.astype(np.float32) * ease(t / 0.6)).astype(np.uint8)
    if t > DUR - 0.8: fr = (fr.astype(np.float32) * clamp01((DUR - t) / 0.8)).astype(np.uint8)
    fr[:] = (fr.astype(np.float32) * BAND).astype(np.uint8)
    for ci, (s, e) in enumerate(CH_T):
        if s <= t < e: draw_chunk(fr, ci, t)
    lg = logo(); blend(fr, lg, (W - lg.shape[1]) // 2, int(H * 0.77))
    return fr

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "info":
        print("DUR", DUR, "SC", [round(s, 2) for s in SC])
        json.dump(dict(DUR=DUR, SC=SC, T_LAST=T_LAST), open("timeline_m.json", "w"))
    elif mode == "stills":
        os.makedirs("stills", exist_ok=True)
        for t in [float(v) for v in sys.argv[2].split(",")]:
            Image.fromarray(frame(t)).save(f"stills/t{t:06.2f}.jpg", quality=85)
    elif mode == "render":
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for i in range(a, b): enc.stdin.write(frame(i / FPS).tobytes())
        enc.stdin.close(); enc.wait()
