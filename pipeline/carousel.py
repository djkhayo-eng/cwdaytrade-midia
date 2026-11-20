"""Gerador de carrossel/post da CW Trader (1080x1350, padrão Instagram).

Uso: python3 carousel.py spec.json pasta_saida
spec.json:
{
  "slug": "ipo-anthropic",
  "slides": [
    {"type": "capa", "tag": "URGENTE · MERCADO", "title": "MAIOR IPO DA HISTÓRIA", "highlight": "-13%", "hl_color": "red",
     "subtitle": "quem comprou na abertura", "bg": "/caminho/foto_opcional.jpg"},
    {"type": "dado", "kicker": "O QUE ACONTECEU", "big": "US$ 81,3 BI", "big_color": "green", "text": "Texto curto explicando."},
    {"type": "lista", "kicker": "OS NÚMEROS", "items": [["IPO", "US$ 83"], ["Abertura", "US$ 111,50 (+34%)"]]},
    {"type": "texto", "kicker": "A LIÇÃO", "title": "NOTÍCIA NÃO É ENTRADA", "text": "Parágrafo curto."},
    {"type": "cta", "title": "SALVA E COMPARTILHA", "text": "Quer aprender a ler o gráfico? Link na bio.",
     "fonte": "Fontes: B3, Forbes, CNBC"}
  ]
}
Um "post simples" = spec com só 1 slide (type capa ou dado). Cores: green, red, gold, white.
"""
import json, os, sys, textwrap
from PIL import Image, ImageDraw, ImageFilter, ImageOps
BASE = os.path.dirname(os.path.abspath(__file__))
ANTON = os.path.join(BASE, "fonts/anton-latin-400-normal.ttf")
MONT = os.path.join(BASE, "fonts/montserrat-latin-800-normal.ttf")
MONTR = os.path.join(BASE, "fonts/montserrat-latin-400-normal.ttf")
W, H = 1080, 1350
COL = dict(green=(0, 230, 118), red=(255, 72, 72), gold=(255, 200, 60), white=(255, 255, 255))
BG = (8, 10, 14)
from PIL import ImageFont
_f = {}
def F(path, size):
    k = (path, size)
    if k not in _f: _f[k] = ImageFont.truetype(path, size)
    return _f[k]

def base(bg_path=None, dim=0.35):
    im = Image.new("RGB", (W, H), BG)
    if bg_path and os.path.exists(bg_path):
        ph = ImageOps.exif_transpose(Image.open(bg_path)).convert("RGB")
        ph = ImageOps.fit(ph, (W, H), Image.LANCZOS)
        ph = Image.blend(Image.new("RGB", (W, H), BG), ph, dim)
        im = ph
    d = ImageDraw.Draw(im, "RGBA")
    for x in range(0, W, 90): d.line([x, 0, x, H], fill=(255, 255, 255, 10))
    for y in range(0, H, 90): d.line([0, y, W, y], fill=(255, 255, 255, 10))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(glow).ellipse([-200, 350, W + 200, 1150], fill=(0, 120, 70, 55))
    im = Image.alpha_composite(im.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(150)))
    return im

def text3d(im, text, size, cx, cy, top=(255, 255, 255), side=(35, 38, 48), font=ANTON, glow=None, maxw=980):
    f = F(font, size)
    while f.getlength(text) > maxw and size > 40:
        size -= 6; f = F(font, size)
    l, t, r, b = f.getbbox(text); tw, th = r - l, b - t
    depth = max(6, size // 12)
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    x0, y0 = cx - tw / 2 - l, cy - th / 2 - t
    if glow:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(g).text((x0, y0), text, font=f, fill=glow + (200,))
        lay = Image.alpha_composite(lay, g.filter(ImageFilter.GaussianBlur(size * 0.2))); d = ImageDraw.Draw(lay)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((x0 + depth + 8, y0 + depth * 1.4 + 12), text, font=f, fill=(0, 0, 0, 170))
    lay = Image.alpha_composite(lay, sh.filter(ImageFilter.GaussianBlur(12))); d = ImageDraw.Draw(lay)
    for i in range(depth, 0, -1):
        k = 0.55 + 0.45 * (1 - i / depth); d.text((x0 + i * 0.45, y0 + i * 0.9), text, font=f, fill=tuple(int(c * k) for c in side) + (255,))
    d.text((x0, y0), text, font=f, fill=top + (255,))
    return Image.alpha_composite(im, lay), th

def pill(im, text, cx, cy, size=34, fg=(10, 12, 16), bg=COL["gold"], border=None):
    f = F(MONT, size); l, t, r, b = f.getbbox(text); w, h = r - l + 52, b - t + 26
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], h // 2, fill=bg, outline=border, width=3 if border else 0)
    d.text((cx - (r - l) / 2 - l, cy - (b - t) / 2 - t), text, font=f, fill=fg)
    return h

def para(im, text, cx, y, size=40, color=(225, 230, 236), width=34, font=MONTR, lh=1.32):
    d = ImageDraw.Draw(im); f = F(font, size)
    for line in textwrap.wrap(text, width):
        l, t, r, b = f.getbbox(line); d.text((cx - (r - l) / 2 - l, y), line, font=f, fill=color); y += int(size * lh)
    return y

def footer(im, i, n):
    d = ImageDraw.Draw(im); f = F(MONT, 26)
    d.text((60, H - 70), "@cwdaytrade", font=f, fill=(200, 205, 212))
    if n > 1:
        s = f"{i}/{n}"; l, t, r, b = f.getbbox(s); d.text((W - 60 - (r - l), H - 70), s, font=f, fill=(150, 156, 165))
        if i < n:
            ax = W - 60 - (r - l) - 40; ay = H - 70 + (b + t) / 2
            d.polygon([(ax - 14, ay - 12), (ax + 6, ay), (ax - 14, ay + 12)], fill=COL["gold"])

def slide(s, i, n):
    t = s.get("type", "texto")
    im = base(s.get("bg"), s.get("bg_dim", 0.38))
    if t == "capa":
        if s.get("tag"): pill(im, s["tag"], W / 2, 170, 30, (255, 255, 255), (40, 8, 10), COL["red"])
        y = 330
        for line in textwrap.wrap(s["title"], 16):
            im, th = text3d(im, line.upper(), 120, W / 2, y); y += th + 40
        if s.get("highlight"):
            c = COL.get(s.get("hl_color", "gold"), COL["gold"])
            im, th = text3d(im, s["highlight"], 230, W / 2, y + 140, tuple(min(255, int(v + (255 - v) * 0.3)) for v in c), tuple(int(v * 0.3) for v in c), glow=c)
            y += 300
        if s.get("subtitle"): pill(im, s["subtitle"].upper(), W / 2, min(y + 40, H - 200), 36)
    elif t == "dado":
        pill(im, s.get("kicker", ""), W / 2, 200, 32)
        c = COL.get(s.get("big_color", "gold"), COL["gold"])
        im, th = text3d(im, s["big"], 190, W / 2, 470, tuple(min(255, int(v + (255 - v) * 0.3)) for v in c), tuple(int(v * 0.3) for v in c), glow=c)
        para(im, s.get("text", ""), W / 2, 700, 42, width=32)
    elif t == "lista":
        pill(im, s.get("kicker", ""), W / 2, 190, 32)
        d = ImageDraw.Draw(im); y = 320
        for k, v in s["items"]:
            d.rounded_rectangle([70, y, W - 70, y + 140], 28, fill=(14, 17, 23, 235), outline=(255, 255, 255, 40), width=2)
            d.text((110, y + 30), k.upper(), font=F(MONT, 30), fill=(160, 166, 175))
            vc = COL["red"] if v.strip().startswith("-") or "(-" in v else COL["green"] if "(+" in v or v.strip().startswith("+") else (255, 255, 255)
            d.text((110, y + 68), v, font=F(ANTON, 52), fill=vc)
            y += 165
    elif t == "texto":
        pill(im, s.get("kicker", ""), W / 2, 200, 32)
        y = 360
        for line in textwrap.wrap(s["title"].upper(), 15):
            im, th = text3d(im, line, 110, W / 2, y, (255, 236, 160), (90, 55, 5)); y += th + 36
        para(im, s.get("text", ""), W / 2, y + 60, 42, width=32)
    elif t == "cta":
        im, th = text3d(im, s.get("title", "SALVA E COMPARTILHA").upper(), 110, W / 2, 400)
        y = para(im, s.get("text", ""), W / 2, 520, 44, (255, 255, 255), 30, MONT)
        pill(im, "LINK NA BIO", W / 2, y + 90, 50, (8, 10, 12), COL["green"])
        y = para(im, "Conteúdo educativo e informativo. Não é recomendação de compra ou venda de ativos. Renda variável envolve risco.", W / 2, H - 300, 26, (150, 156, 165), 60)
        if s.get("fonte"): para(im, s["fonte"], W / 2, y + 10, 24, (130, 136, 145), 70)
    footer(im, i, n)
    return im.convert("RGB")

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    n = len(spec["slides"]); paths = []
    for i, s in enumerate(spec["slides"], 1):
        p = os.path.join(out, f"{spec['slug']}_slide-{i:02d}.jpg"); slide(s, i, n).save(p, quality=92); paths.append(p)
    print("\n".join(paths))
