"""Carrossel CW Trader — versão clara (fundo creme, tinta azul-marinho). Uso: python3 carrossel_claro.py spec.json saida/"""
import json, os, sys, textwrap
from PIL import Image, ImageDraw, ImageFilter, ImageFont
P = "/home/claude/cwdaytrade-midia/pipeline/fonts/"
ANTON, MONT, MONTR = P + "anton-latin-400-normal.ttf", P + "montserrat-latin-800-normal.ttf", P + "montserrat-latin-400-normal.ttf"
MONT6 = P + "montserrat-600.ttf"
W, H = 1080, 1350
BG = (248, 245, 238); INK = (15, 27, 45); SUB = (88, 98, 114); MUTED = (140, 146, 156)
BLUE = (37, 99, 235); CORAL = (230, 76, 60); GOLD = (214, 158, 46); GREEN = (22, 150, 90)
COL = dict(blue=BLUE, red=CORAL, gold=GOLD, green=GREEN, ink=INK)
_f = {}
def F(p, s):
    if (p, s) not in _f: _f[(p, s)] = ImageFont.truetype(p, s)
    return _f[(p, s)]

def soft(im, color, box, blur):
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).ellipse(box, fill=255)
    lay = Image.new("RGBA", (W, H), color + (255,)); lay.putalpha(m.filter(ImageFilter.GaussianBlur(blur)))
    return Image.alpha_composite(im, lay)

def base():
    im = Image.new("RGBA", (W, H), BG + (255,))
    im = soft(im, (208, 224, 255), [520, -260, 1400, 560], 140)
    im = soft(im, (255, 230, 196), [-380, 900, 420, 1650], 140)
    rgb = im.convert("RGB"); d = ImageDraw.Draw(rgb, "RGBA")
    for x in range(0, W, 90): d.line([x, 0, x, H], fill=INK + (14,))
    for y in range(0, H, 90): d.line([0, y, W, y], fill=INK + (14,))
    d.rectangle([0, 0, W, 14], fill=BLUE + (255,))
    return rgb.convert("RGBA")

def panel(im, box, r=32):
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle(box, r, fill=(255, 255, 255, 235), outline=INK + (30,), width=2)
    im.alpha_composite(lay)

def title(im, text, size, cx, cy, color=INK, maxw=960):
    f = F(ANTON, size)
    while f.getlength(text) > maxw and size > 40: size -= 6; f = F(ANTON, size)
    l, t, r, b = f.getbbox(text); tw, th = r - l, b - t; x0, y0 = cx - tw / 2 - l, cy - th / 2 - t
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).text((x0 + 4, y0 + 8), text, font=f, fill=45)
    sh = Image.new("RGBA", im.size, INK + (255,)); sh.putalpha(m.filter(ImageFilter.GaussianBlur(8)))
    im = Image.alpha_composite(im, sh)
    ImageDraw.Draw(im).text((x0, y0), text, font=f, fill=color)
    return im, th

def pill(im, text, cx, cy, size=30, fg=(255, 255, 255), bg=INK):
    f = F(MONT, size); l, t, r, b = f.getbbox(text); w, h = r - l + 52, b - t + 26
    d = ImageDraw.Draw(im); d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], h // 2, fill=bg)
    d.text((cx - (r - l) / 2 - l, cy - (b - t) / 2 - t), text, font=f, fill=fg); return h

def para(im, text, cx, y, size=40, color=SUB, width=34, font=MONTR, lh=1.38, card=False):
    d = ImageDraw.Draw(im, "RGBA"); f = F(font, size)
    if card:
        lines = textwrap.wrap(text, width); hh = int(size * lh) * len(lines)
        panel(im, [90, y - 40, W - 90, y + hh + 30]); d = ImageDraw.Draw(im)
    for line in textwrap.wrap(text, width):
        l, t, r, b = f.getbbox(line); d.text((cx - (r - l) / 2 - l, y), line, font=f, fill=color); y += int(size * lh)
    return y

def footer(im, i, n):
    d = ImageDraw.Draw(im); f = F(MONT, 26)
    d.text((60, H - 72), "@cwdaytrade", font=f, fill=INK)
    if n > 1:
        s = f"{i}/{n}"; l, t, r, b = f.getbbox(s); d.text((W - 60 - (r - l), H - 72), s, font=f, fill=MUTED)
        if i < n:
            ax = W - 60 - (r - l) - 40; ay = H - 72 + (b + t) / 2
            d.polygon([(ax - 14, ay - 12), (ax + 6, ay), (ax - 14, ay + 12)], fill=BLUE)

def slide(s, i, n):
    t = s["type"]; im = base()
    if t == "capa":
        pill(im, s["tag"], W / 2, 190, 30, (255, 255, 255), BLUE)
        y = 360
        for line in textwrap.wrap(s["title"].upper(), 14):
            im, th = title(im, line, 130, W / 2, y); y += th + 42
        c = COL[s.get("hl_color", "blue")]
        im, th = title(im, s["highlight"], 260, W / 2, y + 150, c); y += 330
        pill(im, s["subtitle"].upper(), W / 2, y + 30, 34, INK, (255, 255, 255))
    elif t == "dado":
        pill(im, s["kicker"], W / 2, 200, 30)
        im, th = title(im, s["big"], 230, W / 2, 470, COL[s.get("big_color", "blue")])
        para(im, s["text"], W / 2, 720, 42, INK, 32, card=True)
    elif t == "lista":
        pill(im, s["kicker"], W / 2, 190, 30)
        d = ImageDraw.Draw(im, "RGBA"); y = 300
        for k, v in s["items"]:
            panel(im, [70, y, W - 70, y + 148], 28); d = ImageDraw.Draw(im)
            d.rounded_rectangle([70, y, 84, y + 148], 7, fill=BLUE)
            d.text((115, y + 28), k.upper(), font=F(MONT, 28), fill=MUTED)
            vc = CORAL if v.strip().startswith(("-", "+")) and "%" in v and "-" in v[:2] else INK
            d.text((115, y + 66), v, font=F(ANTON, 50), fill=vc)
            y += 168
    elif t == "texto":
        pill(im, s["kicker"], W / 2, 200, 30)
        y = 370
        for line in textwrap.wrap(s["title"].upper(), 16):
            im, th = title(im, line, 112, W / 2, y, BLUE); y += th + 36
        para(im, s["text"], W / 2, y + 70, 42, INK, 32, card=True)
    elif t == "cta":
        im, th = title(im, s["title"].upper(), 112, W / 2, 400)
        y = para(im, s["text"], W / 2, 520, 44, INK, 30, MONT)
        pill(im, "LINK NA BIO", W / 2, y + 90, 50, (255, 255, 255), BLUE)
        panel(im, [90, H - 340, W - 90, H - 140])
        y = para(im, "Conteúdo educativo e informativo. Não é recomendação de compra ou venda de ativos. Renda variável envolve risco.", W / 2, H - 305, 26, SUB, 60)
        para(im, s["fonte"], W / 2, y + 10, 24, MUTED, 70)
    footer(im, i, n)
    return im.convert("RGB")

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True); n = len(spec["slides"])
    for i, s in enumerate(spec["slides"], 1):
        p = os.path.join(out, f"{spec['slug']}_slide-{i:02d}.jpg"); slide(s, i, n).save(p, quality=92); print(p)
