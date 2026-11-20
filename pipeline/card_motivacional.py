"""Card motivacional CW Trader (1080x1350): foto cinematográfica escura + frase (sans maiúscula + destaque itálico serifado) + logo.
Uso: python3 card_motivacional.py spec.json saida.jpg
spec.json: {"bg": "/caminho/foto.jpg", "fx": 0.5, "fy": 0.3, "y": 0.27, "blur": 0,
            "lines": [[["O MERCADO NÃO PAGA", false]], [["QUEM TEM ", false], ["pressa.", true]]]}
  - cada linha é uma lista de segmentos [texto, destaque]; destaque=true usa itálico serifado maior.
  - y = centro vertical do bloco de texto (0–1). fx/fy = ponto de recorte da foto."""
import json, os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
PIPE = os.path.dirname(os.path.abspath(__file__))
F_SANS = os.path.join(PIPE, "fonts/montserrat-600.ttf"); F_SERIF = os.path.join(PIPE, "fonts/playfair-600-italic.ttf")
W, H = 1080, 1350
SANS, SERIF = 58, 104

def moody(img):
    f = img.astype(np.float32); m = f[::8, ::8].mean(); f *= min(1.0, 92.0 / max(m, 1))
    g = f.mean(2, keepdims=True); f = g + (f - g) * 0.78
    x = np.arange(256) / 255.0; base = np.clip((x - 0.5) * 1.22 + 0.5, 0, 1) ** 1.28
    luts = [(np.clip(base * k + o * (1 - base), 0, 1) * 255).astype(np.uint8) for k, o in ((0.84, 0.0), (0.97, 0.025), (1.08, 0.07))]
    f = np.clip(f, 0, 255).astype(np.uint8); out = np.empty_like(f)
    for c in range(3): out[..., c] = cv2.LUT(f[..., c], luts[c])
    yy, xx = np.mgrid[0:H, 0:W]
    vig = (1 - 0.6 * np.clip(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2, 0, 1) ** 1.2)[..., None]
    out = out.astype(np.float32) * vig * 0.9
    noise = np.random.default_rng(1).normal(0, 4, (H, W, 1)).astype(np.float32)
    return np.clip(out + noise, 0, 255).astype(np.uint8)

def render(spec):
    im = ImageOps.exif_transpose(Image.open(spec["bg"])).convert("RGB")
    im = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(spec.get("fx", 0.5), spec.get("fy", 0.5)))
    a = np.asarray(im)
    if spec.get("blur"): a = cv2.GaussianBlur(a, (0, 0), spec["blur"])
    a = moody(a)
    yc = spec.get("y", 0.3) * H
    band = (1 - 0.35 * np.exp(-((np.arange(H) - yc) / (H * 0.16)) ** 2)).astype(np.float32)[:, None, None]
    a = (a.astype(np.float32) * band).astype(np.uint8)
    base = Image.fromarray(a).convert("RGBA")
    fs, fe = ImageFont.truetype(F_SANS, SANS), ImageFont.truetype(F_SERIF, SERIF)
    LH = 122; lines = spec["lines"]; top = yc - LH * len(lines) / 2
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    sh = Image.new("L", (W, H), 0); sd = ImageDraw.Draw(sh)
    for li, segs in enumerate(lines):
        widths = [(fe if em else fs).getlength(t) for t, em in segs]; x = (W - sum(widths)) / 2
        bl = top + li * LH + 96
        for (t, em), wdt in zip(segs, widths):
            f = fe if em else fs; asc = f.getmetrics()[0]
            col = (255, 236, 200) if em else (255, 255, 255)
            sd.text((x, bl - asc + 5), t, font=f, fill=210); d.text((x, bl - asc), t, font=f, fill=col); x += wdt
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); shadow.putalpha(sh.filter(ImageFilter.GaussianBlur(14)))
    base = Image.alpha_composite(Image.alpha_composite(base, shadow), txt)
    # logo
    d = ImageDraw.Draw(base); f = ImageFont.truetype(F_SANS, 26); s = "CW TRADER"; sp = 6
    wid = sum(f.getlength(c) + sp for c in s); x = (W - wid) / 2; y = H - 120
    for c in s: d.text((x, y), c, font=f, fill=(255, 255, 255, 235)); x += f.getlength(c) + sp
    d.ellipse([x + 4, y + 2, x + 15, y + 13], fill=(255, 200, 60, 255))
    return base.convert("RGB")

if __name__ == "__main__":
    render(json.load(open(sys.argv[1]))).save(sys.argv[2], quality=93); print(sys.argv[2])
