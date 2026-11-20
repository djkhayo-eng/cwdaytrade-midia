import sys, os, time, random
PIPE = os.environ.get("PIPELINE", "/home/claude/cwdaytrade-midia/pipeline")
sys.path.insert(0, PIPE)
from lib import *

SFX = []
def sfx(t, name, g=1.0): SFX.append((round(t, 3), name, g))
NP = 7
SC = [0.0] + [WT(p, 0) - 0.12 for p in range(1, NP)]
T_END = WE(6, len(PARA[6]) - 1) + 0.6
DUR = T_END + 2.8
def scene_of(t):
    for p in range(NP - 1, -1, -1):
        if t >= SC[p]: return p
    return 0
def K(p, word):
    for k, w in enumerate(PARA[p]):
        if w["w"].lower().strip(".,:?!").startswith(word.lower()): return w["S"]
    raise KeyError(word)

# ---------------- captions (texto na tela) ----------------
SEM_G = {"salva", "segue", "link", "bio", "plano", "plano?", "stop", "menor"}
SEM_R = {"death", "cross", "baixa", "medo", "extremo", "28%", "caiu", "cai", "1,6%", "10", "atrasado", "não", "subir"}
SEM_Y = {"us$", "bitcoin", "fed", "nasdaq", "95%", "50", "200", "juros", "cw", "trader"}
def clean(w): return w.strip(".,:!?").lower()
CHUNKS = []
for p in range(NP):
    ws = PARA[p]; cur = []
    for i, w in enumerate(ws):
        cur.append(i)
        txt = " ".join(ws[j]["w"] for j in cur)
        brk = w["w"][-1] in ".,:?" or len(cur) >= 4 or len(txt) >= 18
        if brk or i == len(ws) - 1: CHUNKS.append((p, cur)); cur = []
CH_T = []
for ci, (p, idx) in enumerate(CHUNKS):
    s = PARA[p][idx[0]]["S"]
    if ci + 1 < len(CHUNKS):
        np_, nidx = CHUNKS[ci + 1]; e = min(PARA[np_][nidx[0]]["S"], PARA[p][idx[-1]]["E"] + 0.6)
    else: e = PARA[p][idx[-1]]["E"] + 0.5
    CH_T.append((s, e))
CAP = 64
@functools.lru_cache(maxsize=1024)
def cap_img(ci, act):
    p, idx = CHUNKS[ci]; ws = [PARA[p][j]["w"].upper() for j in idx]
    fo = font(MONT, CAP); foA = font(MONT, int(CAP * 1.12)); sp = 18; items = []
    for k, w in enumerate(ws):
        f = foA if k == act else fo; l, t_, r, b = f.getbbox(w, stroke_width=8); items.append((w, f, r - l, l, t_))
    lines = [[]]; lw = 0
    for it in items:
        if lines[-1] and lw + sp + it[2] > 900: lines.append([]); lw = 0
        lines[-1].append(it); lw += (sp if lw else 0) + it[2]
    LH = int(CAP * 1.32); Wc = 1000; Hc = LH * len(lines) + 40
    im = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sh = Image.new("L", (Wc, Hc), 0); sd = ImageDraw.Draw(sh); k = 0; y = 20
    for line in lines:
        tw = sum(i[2] for i in line) + sp * (len(line) - 1); x = (Wc - tw) / 2
        for (w, f, ww, l, t_) in line:
            base = y + (LH - CAP) / 2 - (8 if k == act else 0); cw = clean(w)
            col = WHITE
            if k == act:
                col = GREEN if cw in SEM_G else RED if cw in SEM_R else GOLD if cw in SEM_Y else YEL
            sd.text((x - l + 4, base - t_ + 8), w, font=f, fill=200, stroke_width=8, stroke_fill=200)
            d.text((x - l, base - t_), w, font=f, fill=col, stroke_width=8, stroke_fill=(8, 8, 10))
            x += ww + sp; k += 1
        y += LH
    shi = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0)); shi.putalpha(sh.filter(ImageFilter.GaussianBlur(8)))
    return np.asarray(Image.alpha_composite(shi, im)).copy()
def draw_caption(fr, t):
    if t >= T_END: return
    for ci, (s, e) in enumerate(CH_T):
        if s <= t < e:
            p, idx = CHUNKS[ci]; act = 0
            for k, j in enumerate(idx):
                if t >= PARA[p][j]["S"] - 0.02: act = k
            img = cap_img(ci, act); u = ease((t - s) / 0.16)
            blend(fr, img, (W - img.shape[1]) / 2, 1340 - (1 - u) * 26, alpha=u); return

# ---------------- helpers ----------------
def slam(fr, img, x, y, t0, t, dur=0.22, amp=0.5, alpha=1.0, rot=0):
    if t < t0 - 0.06: return
    k = (t - t0 + 0.06) / dur
    blend_c(fr, img, x, y, clamp01(k * 2) * alpha, 1 + amp * (1 - ease(k)), rot)
def shake(fr, t, t0, dur=0.35, amp=22):
    if t0 <= t < t0 + dur:
        a = amp * (1 - (t - t0) / dur); dx = int(a * math.sin(t * 90)); dy = int(a * math.cos(t * 73))
        return np.roll(np.roll(fr, dx, 1), dy, 0)
    return fr
def rgb_split(fr, amt):
    if amt < 1: return fr
    o = fr.copy(); a = int(amt)
    o[..., 0] = np.roll(fr[..., 0], a, 1); o[..., 2] = np.roll(fr[..., 2], -a, 1); return o
_grids = {}
def grid_bg(col=(0, 120, 70)):
    if col not in _grids:
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for x in range(0, W, 90): d.line([x, 0, x, H], fill=(255, 255, 255, 12))
        for y in range(0, H, 90): d.line([0, y, W, y], fill=(255, 255, 255, 12))
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([-200, 500, W + 200, 1500], fill=col + (70,))
        _grids[col] = pil2np(Image.alpha_composite(g.filter(ImageFilter.GaussianBlur(160)), im))
    return _grids[col]
REDG = (150, 20, 30); ORG = (247, 147, 26)
def dark(fr, col=(0, 120, 70)):
    fr[:] = (8, 10, 14); blend(fr, grid_bg(col), 0, 0)

TAPE = "  BTC ~US$ 62 MIL   •   -28% DO PICO   •   DEATH CROSS 50x200   •   MEDO & GANÂNCIA: 10   •   FED DEZ: 95%+ CHANCE DE ALTA   •   NASDAQ FUT -1,6%   "
_tape = None
def tape_img():
    global _tape
    if _tape is None:
        fo = font(MONT, 30); w = int(round(fo.getlength(TAPE)))
        im = Image.new("RGBA", (w * 3 + 200, 62), (12, 14, 18, 230)); d = ImageDraw.Draw(im)
        d.text((0, 12), TAPE * 3, font=fo, fill=ORG)
        d.line([0, 0, w * 3 + 200, 0], fill=ORG + (255,), width=2); d.line([0, 61, w * 3 + 200, 61], fill=ORG + (255,), width=2)
        _tape = (pil2np(im), w)
    return _tape
def draw_tape(fr, t, y=215, a=1.0):
    img, w = tape_img(); off = int((t * 140) % w)
    blend(fr, img[:, off:off + W], 0, y, a)

@functools.lru_cache(maxsize=4)
def btc_coin(size=260):
    s = size; im = Image.new("RGBA", (s + 80, s + 80), (0, 0, 0, 0))
    g = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([30, 30, s + 50, s + 50], fill=ORG + (170,))
    im = Image.alpha_composite(im, g.filter(ImageFilter.GaussianBlur(24))); d = ImageDraw.Draw(im)
    d.ellipse([40, 40, s + 40, s + 40], fill=(200, 110, 10, 255)); d.ellipse([52, 46, s + 34, s + 28], fill=ORG + (255,))
    f = font(ANTON, int(s * 0.62)); l, t_, r, b = f.getbbox("₿") if f.getbbox("₿")[2] > 0 else f.getbbox("B")
    txt = "B"; l, t_, r, b = f.getbbox(txt)
    cx, cy_ = 40 + s / 2, 40 + s / 2 - 6
    d.text((cx - (r + l) / 2, cy_ - (b + t_) / 2), txt, font=f, fill=WHITE)
    for dx in (-s * 0.07, s * 0.07):
        d.rectangle([cx + dx - 5, cy_ - (b - t_) / 2 - 22, cx + dx + 5, cy_ + (b - t_) / 2 + 22], fill=WHITE)
    return pil2np(im)

# ---------------- cena 0: gancho ----------------
def cross_icon(u):
    im = Image.new("RGBA", (900, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    gl = Image.new("RGBA", im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    n = 60; xs = np.linspace(40, 860, n)
    a = [(x, 90 + 260 * (i / (n - 1)) ** 1.4) for i, x in enumerate(xs)]          # MA50 descendo
    b = [(x, 170 + 90 * (i / (n - 1))) for i, x in enumerate(xs)]                 # MA200 mais lenta
    k = max(2, int(n * u))
    gd.line(a[:k], fill=GOLD + (200,), width=18); gd.line(b[:k], fill=WHITE + (160,), width=18)
    im = Image.alpha_composite(im, gl.filter(ImageFilter.GaussianBlur(10))); d = ImageDraw.Draw(im)
    d.line(a[:k], fill=GOLD + (255,), width=8); d.line(b[:k], fill=WHITE + (255,), width=8)
    return pil2np(im)
def s_hook(fr, t):
    dark(fr, REDG)
    td = K(0, "death"); t0 = WT(0, 0)
    blend_c(fr, btc_coin(), W / 2, 470, clamp01((t - t0) / 0.2), 0.8 + 0.2 * back((t - t0) / 0.4))
    slam(fr, text3d("BITCOIN", 120, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 700, K(0, "Bitcoin"), t)
    if t > td - 0.05:
        slam(fr, text3d("DEATH CROSS", 160, (255, 150, 150), RED, (90, 10, 15), None, ANTON, glow=(255, 40, 40)), W / 2, 880, td, t, 0.2, 0.6)
        u = clamp01((t - td) / 0.9)
        blend_c(fr, cross_icon(u), W / 2, 1130, 0.9)
        if t > td: fr[:] = (fr.astype(np.float32) * np.array([1.08, 0.88, 0.88])).clip(0, 255).astype(np.uint8)

# ---------------- cena 1: preço ----------------
def s_price(fr, t):
    dark(fr, REDG); draw_tape(fr, t)
    t62 = K(1, "US$ 62"); t28 = K(1, "28%"); t87 = K(1, "US$ 87")
    blend_c(fr, label("PREÇO AGORA", 40, (8, 10, 12), ORG, 255, 26, 12), W / 2, 440, clamp01((t - SC[1]) / 0.2))
    if t > t62 - 0.06:
        u = ease((t - t62) / 0.9); val = 87 - 25 * u
        blend_c(fr, text3d(f"US$ {val:0.0f} MIL", 170, (255, 236, 160), ORG, (90, 45, 5), None, ANTON, glow=(255, 140, 0)), W / 2, 640, clamp01((t - t62 + 0.06) / 0.12))
    if t > t28 - 0.05:
        slam(fr, text3d("-28%", 200, (255, 150, 150), RED, (90, 10, 15), None, ANTON, glow=(255, 40, 40)), W / 2, 900, t28, t, 0.2, 0.6)
        blend_c(fr, plain("desde o pico de setembro", 36, GREY, MONTR), W / 2, 1060, clamp01((t - t28 - 0.2) / 0.3))
    if t > t87 - 0.05:
        blend_c(fr, label("PICO SET/26 ~US$ 87 MIL", 36, WHITE, (12, 14, 18), 235, 22, 11, border=GREEN), W / 2, 1160, clamp01((t - t87 + 0.05) / 0.2), 0.7 + 0.3 * back((t - t87) / 0.35))

# ---------------- cena 2: gráfico death cross ----------------
random.seed(7)
NPT = 120
_px = np.linspace(0, 1, NPT)
_base = 74 + 13 * np.sin(np.clip(_px / 0.30, 0, 1) * np.pi / 2) - 25 * np.clip((_px - 0.30) / 0.70, 0, 1) ** 1.2
_noise = np.cumsum(np.random.RandomState(4).normal(0, 0.55, NPT)); _noise -= np.linspace(_noise[0], _noise[-1], NPT)
PRICE = _base + _noise * 0.9; PRICE[0] = 74; PRICE[-1] = 62
def _ma(arr, n, start):
    out = np.empty_like(arr); hist = list(np.full(n, start))
    for i, v in enumerate(arr):
        hist.append(v); hist.pop(0); out[i] = np.mean(hist)
    return out
MA50 = _ma(PRICE, 30, 76.5); MA200 = _ma(PRICE, 95, 75.3)
XC = next(i for i in range(60, NPT) if MA50[i] < MA200[i])
CW_, CH_ = 980, 880; PMIN, PMAX = 56, 92
def cyy(p): return 70 + (PMAX - p) / (PMAX - PMIN) * (CH_ - 160)
def cxx(i): return 40 + i / (NPT - 1) * (CW_ - 120)
def chart(t):
    im = Image.new("RGBA", (CW_, CH_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, CW_ - 1, CH_ - 1], 38, fill=(10, 13, 19, 215), outline=(255, 255, 255, 46), width=2)
    for p in (60, 70, 80, 90):
        y = cyy(p); d.line([30, y, CW_ - 30, y], fill=(255, 255, 255, 16)); d.text((CW_ - 92, y - 30), f"{p} mil", font=font(MONTR, 22), fill=(140, 150, 160))
    tS = SC[2]; tc = K(2, "cruza")
    if t < tc: xr = 0.15 + 0.6 * ease_io((t - tS) / max(0.5, tc - tS))
    else: xr = 0.75 + 0.25 * ease((t - tc) / 1.2)
    n = max(2, int(xr * (NPT - 1)) + 1)
    P = [(cxx(i), cyy(PRICE[i])) for i in range(n)]
    A = [(cxx(i), cyy(MA50[i])) for i in range(n)]; B = [(cxx(i), cyy(MA200[i])) for i in range(n)]
    d.line(P, fill=(120, 130, 145, 200), width=3, joint="curve")
    gl = Image.new("RGBA", (CW_, CH_), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    gd.line(A, fill=GOLD + (200,), width=14, joint="curve"); gd.line(B, fill=WHITE + (150,), width=14, joint="curve")
    im = Image.alpha_composite(im, gl.filter(ImageFilter.GaussianBlur(9))); d = ImageDraw.Draw(im)
    d.line(A, fill=GOLD + (255,), width=6, joint="curve"); d.line(B, fill=WHITE + (255,), width=6, joint="curve")
    # legenda
    d.rounded_rectangle([40, 30, 60, 50], 4, fill=GOLD + (255,)); d.text((70, 26), "média 50 dias", font=font(MONT, 24), fill=GOLD)
    d.rounded_rectangle([330, 30, 350, 50], 4, fill=WHITE + (255,)); d.text((360, 26), "média 200 dias", font=font(MONT, 24), fill=WHITE)
    d.text((640, 26), "— preço", font=font(MONT, 24), fill=(140, 150, 160))
    if n - 1 >= XC:
        x, y = cxx(XC), cyy(MA200[XC]); u = ease((t - tc) / 0.4) if t >= tc else 1
        r = 22 + 30 * (1 - u)
        d.ellipse([x - r, y - r, x + r, y + r], outline=RED + (255,), width=6)
        tg = label("DEATH CROSS", 30, WHITE, (40, 8, 10), 245, 16, 8, border=RED)
        im.alpha_composite(Image.fromarray(tg), (int(x - tg.shape[1] / 2 - 60), int(y - 120)))
    if n == NPT:
        hx, hy = P[-1]; d.ellipse([hx - 10, hy - 10, hx + 10, hy + 10], fill=RED + (255,), outline=WHITE + (255,), width=3)
        tg = label("~US$ 62 MIL", 26, (8, 10, 12), RED, 255, 14, 7)
        im.alpha_composite(Image.fromarray(tg), (int(hx - tg.shape[1] + 20), int(hy + 22)))
    d.text((40, 64), "trajetória ilustrativa · preços: Decrypt / KuCoin", font=font(MONTR, 22), fill=(150, 158, 168))
    return np.asarray(im).copy()
def s_chart(fr, t):
    dark(fr, REDG); draw_tape(fr, t)
    slam(fr, text3d("O QUE É?", 110, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 380, SC[2] + 0.1, t)
    k_in = ease((t - SC[2]) / 0.45)
    pv = persp(chart(t), -4 + 6 * clamp01((t - SC[2]) / (SC[3] - SC[2])), 3, 0.9 + 0.08 * k_in)
    blend_c(fr, pv, W / 2, 870)
    tb = K(2, "baixa")
    if t > tb - 0.05:
        slam(fr, label("SINAL DE TENDÊNCIA DE BAIXA", 36, WHITE, (40, 8, 10), 245, 22, 11, border=RED), W / 2, 1255, tb, t, 0.3, 0.3)

# ---------------- cena 3: medo ----------------
def gauge(val, a=1.0):
    S = 820; im = Image.new("RGBA", (S, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy_, R = S / 2, 450, 360
    cols = [(255, 60, 60), (255, 140, 60), (255, 214, 0), (150, 220, 80), (0, 230, 118)]
    for i, c in enumerate(cols):
        a0 = 180 + i * 36; a1 = a0 + 35
        d.arc([cx - R, cy_ - R, cx + R, cy_ + R], a0, a1, fill=c + (255,), width=70)
    f = font(MONT, 24)
    for v, txt in ((0, "0"), (50, "50"), (100, "100")):
        ang = math.radians(180 + v * 1.8); x = cx + (R - 115) * math.cos(ang); y = cy_ + (R - 115) * math.sin(ang)
        l, t_, r, b = f.getbbox(txt); d.text((x - (r + l) / 2, y - (b + t_) / 2), txt, font=f, fill=GREY)
    ang = math.radians(180 + val * 1.8)
    x = cx + (R - 40) * math.cos(ang); y = cy_ + (R - 40) * math.sin(ang)
    d.line([cx, cy_, x, y], fill=WHITE + (255,), width=12); d.ellipse([cx - 26, cy_ - 26, cx + 26, cy_ + 26], fill=WHITE + (255,))
    d.text((40, 470), "MEDO", font=font(MONT, 30), fill=RED); d.text((S - 190, 470), "GANÂNCIA", font=font(MONT, 30), fill=GREEN)
    return pil2np(im)
def s_fear(fr, t):
    dark(fr, REDG); draw_tape(fr, t)
    tm = K(3, "medo"); t10 = K(3, "10")
    slam(fr, text3d("MEDO EXTREMO", 130, (255, 150, 150), RED, (90, 10, 15), None, ANTON, glow=(255, 40, 40)), W / 2, 390, tm, t, 0.2, 0.5)
    blend_c(fr, label("ÍNDICE MEDO & GANÂNCIA (CRIPTO)", 30, (8, 10, 12), ORG, 255, 20, 10), W / 2, 540, clamp01((t - SC[3]) / 0.2))
    tg = K(3, "índice")
    v = 50 - 40 * ease_io((t - tg) / max(0.4, t10 - tg)) if t > tg else 50
    if t > t10: v = 10 + 1.2 * math.sin((t - t10) * 18) * max(0, 1 - (t - t10) / 0.6)
    blend_c(fr, gauge(v), W / 2, 830)
    if t > t10 - 0.05:
        slam(fr, text3d("10", 230, (255, 150, 150), RED, (90, 10, 15), None, ANTON, glow=(255, 40, 40)), W / 2, 1150, t10, t, 0.2, 0.6)

# ---------------- cena 4: Fed + Nasdaq ----------------
def s_fed(fr, t):
    dark(fr, (90, 70, 10)); draw_tape(fr, t)
    t95 = K(4, "95%"); tf = K(4, "Fed"); tn = K(4, "Nasdaq"); t16 = K(4, "1,6%")
    blend_c(fr, label("PANO DE FUNDO", 40, (8, 10, 12), GOLD, 255, 26, 12), W / 2, 400, clamp01((t - SC[4]) / 0.2))
    if t < tn - 0.1:
        if t > t95 - 0.06:
            u = ease((t - t95) / 0.8)
            blend_c(fr, text3d(f"{95 * u:0.0f}%+", 250, (255, 236, 160), GOLD, (90, 55, 5), None, ANTON, glow=(255, 160, 0)), W / 2, 640, clamp01((t - t95 + 0.06) / 0.12))
            blend_c(fr, plain("de chance de ALTA de juros", 44, WHITE, MONT), W / 2, 840, clamp01((t - t95 - 0.3) / 0.3))
        if t > tf - 0.05:
            slam(fr, label("FED · DEZEMBRO", 54, WHITE, (12, 14, 18), 240, 34, 16, border=GOLD), W / 2, 960, tf, t, 0.3, 0.3)
            blend_c(fr, plain("probabilidade CME FedWatch, via Reuters", 26, GREY, MONTR), W / 2, 1060, clamp01((t - tf - 0.3) / 0.3))
    else:
        slam(fr, text3d("NASDAQ FUTURO", 120, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 620, tn, t)
        if t > t16 - 0.05:
            slam(fr, text3d("-1,6%", 230, (255, 150, 150), RED, (90, 10, 15), None, ANTON, glow=(255, 40, 40)), W / 2, 860, t16, t, 0.2, 0.6)
            blend_c(fr, plain("hoje cedo · juros altos pesam em risco", 32, GREY, MONTR), W / 2, 1060, clamp01((t - t16 - 0.3) / 0.3))

# ---------------- cena 5: lição ----------------
def s_lesson(fr, t):
    dark(fr); draw_tape(fr, t)
    ta = K(5, "atrasado"); tno = K(5, "Não"); tp = K(5, "plano"); ts = K(5, "stop"); tpm = K(5, "posição")
    slam(fr, label("LIÇÃO DE TRADER", 44, (8, 10, 12), GOLD, 255, 28, 13), W / 2, 380, SC[5] + 0.05, t, 0.3, 0.3)
    if t < tp - 0.15:
        slam(fr, text3d("INDICADOR", 140, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 580, K(5, "indicador"), t)
        slam(fr, text3d("ATRASADO", 150, YEL, GOLD, (80, 55, 0)), W / 2, 750, ta, t)
        if t > tno - 0.05:
            slam(fr, label("NÃO É ORDEM DE COMPRA NEM DE VENDA", 34, WHITE, (40, 8, 10), 245, 22, 11, border=RED), W / 2, 950, tno, t, 0.3, 0.3)
    else:
        slam(fr, text3d("MEDO EXTREMO PEDE", 100, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 560, tp - 0.1, t)
        for i, (tw, txt) in enumerate([(tp, "✓ PLANO"), (ts, "✓ STOP"), (tpm, "✓ POSIÇÃO MENOR")]):
            if t > tw - 0.05:
                kk = (t - tw + 0.05) / 0.3
                blend_c(fr, label(txt.replace("✓ ", ""), 60, (8, 10, 12), GREEN, 255, 36, 16), W / 2, 760 + i * 150, clamp01(kk * 2), 0.6 + 0.4 * back(kk))

# ---------------- cena 6: CTA ----------------
def s_cta(fr, t):
    dark(fr)
    slam(fr, text3d("SALVA", 150, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 520, WT(6, 0), t)
    slam(fr, text3d("+ SEGUE", 130, YEL, GOLD, (80, 55, 0)), W / 2, 680, K(6, "segue"), t)
    tq = K(6, "Quer")
    if t > tq - 0.05:
        slam(fr, label("APRENDA A OPERAR COM PLANO", 38, WHITE, (12, 14, 18), 235, 24, 11, border=GOLD), W / 2, 880, tq, t, 0.3, 0.3)
    tl_ = K(6, "Link")
    if t > tl_ - 0.05 and t < T_END:
        k5 = (t - tl_ + 0.05) / 0.3
        blend_c(fr, label("LINK NA BIO", 64, (8, 10, 12), GREEN, 255, 44, 20), W / 2, 1060, clamp01(k5 * 2), 0.6 + 0.4 * back(k5))

def end_card(fr, t):
    k = (t - T_END) / 0.5
    fr[:] = cv2.convertScaleAbs(fr, alpha=max(0.0, 1 - ease(k)))
    blend(fr, grid_bg(), 0, 0, clamp01(k))
    blend_c(fr, text3d("CW TRADER", 170, (255, 236, 160), GOLD, (90, 55, 5), None, ANTON, glow=(255, 160, 0)), W / 2, 780, clamp01(k * 1.5 - 0.2), 1 + 0.25 * (1 - ease(k)))
    blend_c(fr, plain("@cwdaytrade", 48, WHITE), W / 2, 930, clamp01(k * 1.5 - 0.5))
    blend_c(fr, label("LINK NA BIO", 50, (8, 10, 12), GREEN, 255, 36, 16), W / 2, 1060, clamp01(k * 1.5 - 0.7), 0.7 + 0.3 * back(k - 0.4))
    blend_c(fr, plain("Conteúdo educativo e informativo. Não é recomendação", 26, GREY, MONTR), W / 2, 1300, clamp01(k * 1.5 - 0.9))
    blend_c(fr, plain("de compra ou venda de ativos. Renda variável envolve risco.", 26, GREY, MONTR), W / 2, 1340, clamp01(k * 1.5 - 0.9))

def frame(t):
    fr = np.zeros((H, W, 3), np.uint8); p = scene_of(t)
    [s_hook, s_price, s_chart, s_fear, s_fed, s_lesson, s_cta][p](fr, t)
    if p == 6 and t >= T_END: end_card(fr, t)
    for q in range(1, NP):
        dtq = t - SC[q]
        if 0 <= dtq < 0.16:
            k = 1 - dtq / 0.16; sh = int((1 if q % 2 else -1) * 160 * k)
            fr = np.roll(fr, sh, axis=1); fr = motion_blur(fr, 60 * k)
            if dtq < 0.04: fr = cv2.convertScaleAbs(fr, alpha=1.0, beta=60 * (1 - dtq / 0.04))
    td = K(0, "death")
    if td - 0.05 <= t < td + 0.25: fr = rgb_split(fr, 18 * (1 - (t - td + 0.05) / 0.3))
    fr = shake(fr, t, td, 0.4, 26); fr = shake(fr, t, K(1, "28%"), 0.35, 18); fr = shake(fr, t, K(3, "10"), 0.35, 18)
    fr = shake(fr, t, K(4, "1,6%"), 0.3, 14)
    draw_caption(fr, t)
    return fr

sfx(WT(0, 0), "hit", 0.6); sfx(K(0, "death"), "impact", 1.0); sfx(K(0, "death"), "buzz", 0.5)
sfx(K(1, "US$ 62"), "rewind", 0.45)
for i in range(7): sfx(K(1, "US$ 62") + i * 0.12, "tick", 0.22)
sfx(K(1, "28%"), "impact", 0.8); sfx(K(1, "US$ 87"), "pop", 0.45)
sfx(K(2, "cruza"), "hit", 0.6); sfx(K(2, "baixa"), "buzz", 0.4)
sfx(K(3, "medo"), "impact", 0.7); sfx(K(3, "10"), "hit", 0.7)
sfx(K(4, "95%"), "ding", 0.5); sfx(K(4, "Fed"), "pop", 0.45); sfx(K(4, "Nasdaq"), "whoosh", 0.4); sfx(K(4, "1,6%"), "impact", 0.7)
sfx(K(5, "atrasado"), "hit", 0.5); sfx(K(5, "Não"), "buzz", 0.35)
for w_ in ("plano", "stop", "posição"): sfx(K(5, w_), "pop", 0.45)
sfx(WT(6, 0), "pop", 0.5); sfx(K(6, "segue"), "pop", 0.5); sfx(K(6, "Link"), "cash", 0.5); sfx(T_END, "impact", 0.7)
for q in range(1, NP): sfx(SC[q], "whoosh", 0.5)

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "info":
        print("DUR", DUR, "SC", [round(s, 2) for s in SC], "T_END", T_END, "NFR", int(DUR * FPS))
        json.dump(dict(DUR=DUR, SFX=SFX, SC=SC, T_END=T_END), open("timeline.json", "w"))
    elif mode == "stills":
        os.makedirs("stills", exist_ok=True)
        for t in [float(x) for x in sys.argv[2].split(",")]:
            Image.fromarray(frame(t)).save(f"stills/t{t:06.2f}.jpg", quality=85)
    elif mode == "render":
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        for i in range(a, b): enc.stdin.write(frame(i / FPS).tobytes())
        enc.stdin.close(); enc.wait()
