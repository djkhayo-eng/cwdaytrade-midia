import sys, os, time, random
PIPE = os.environ.get("PIPELINE", "/home/claude/cwdaytrade-midia/pipeline")  # pasta pipeline/ do repo
sys.path.insert(0, PIPE)
from lib import *
from seg import mask as segmask

U = "/mnt/user-data/uploads/Documents/CWTrader-Instagram/"
O = U + "05-Videos-originais/"; BM = U + "04-Banco-de-midia/"
SFX = []
def sfx(t, name, g=1.0): SFX.append((round(t, 3), name, g))
NP = 7
SC = [0.0] + [WT(p, 0) - 0.12 for p in range(1, NP)]
T_END = WE(6, len(PARA[6]) - 1) + 0.45
DUR = T_END + 2.6
def scene_of(t):
    for p in range(NP - 1, -1, -1):
        if t >= SC[p]: return p
    return 0
def K(p, word):
    for k, w in enumerate(PARA[p]):
        if w["w"].lower().strip(".,:?!").startswith(word.lower()): return w["S"]
    raise KeyError(word)

# ---------------- captions ----------------
SEM_G = {"comprar", "acima", "34%", "boa", "salva", "segue", "link", "bio"}
SEM_R = {"prejuízo", "abaixo", "13%", "hype", "caro", "festa", "não"}
SEM_Y = {"us$", "ipo", "anthropic", "nasdaq", "spacex", "anth34", "b3", "bdr", "história", "claude"}
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
            base = y + (LH - CAP) / 2 - (8 if k == act else 0); cw = clean(w); first = cw.split()[0] if cw else cw
            col = WHITE
            if k == act:
                col = GREEN if cw in SEM_G else RED if cw in SEM_R else GOLD if (cw in SEM_Y or first in SEM_Y) else YEL
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
def view(img, s, cx=0.5, cy=0.5, dx=0, dy=0, rgba=False):
    ih, iw = img.shape[:2]; sc = max(W / iw, H / ih) * s
    M = np.array([[sc, 0, W / 2 - cx * iw * sc + dx], [0, sc, H / 2 - cy * ih * sc + dy]], np.float32)
    if rgba: return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
def comp_full(dst, fg):
    a = fg[..., 3:4].astype(np.float32) / 255
    np.copyto(dst, (dst.astype(np.float32) * (1 - a) + fg[..., :3].astype(np.float32) * a).astype(np.uint8))
def layers25(path, fx=0.5):
    im = load_img(path); ih, iw = im.shape[:2]
    if iw / ih > 9 / 16:
        cw = int(ih * 9 / 16); x0 = int((iw - cw) * fx); im = im[:, x0:x0 + cw]
    BW, BH = 1296, 2304; im = cv2.resize(im, (BW, BH), interpolation=cv2.INTER_CUBIC)
    m = segmask(Image.fromarray(im))
    mb = (m > 0.5).astype(np.uint8); nlab, lab, stats, _ = cv2.connectedComponentsWithStats(mb)
    if nlab > 1:
        big = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA]); keep = (lab == big).astype(np.float32)
        keep = cv2.dilate(keep, np.ones((15, 15), np.uint8)); m = m * cv2.GaussianBlur(keep, (0, 0), 4)
    m = cv2.GaussianBlur(m, (0, 0), 1.2); g = grade(im)
    fg = np.dstack([g, (m * 255).astype(np.uint8)])
    sm = cv2.resize(g, (BW // 4, BH // 4)); mm = cv2.resize((m > 0.15).astype(np.uint8) * 255, (BW // 4, BH // 4))
    mm = cv2.dilate(mm, np.ones((9, 9), np.uint8)); inp = cv2.GaussianBlur(cv2.inpaint(sm, mm, 7, cv2.INPAINT_TELEA), (0, 0), 3)
    inpL = cv2.resize(inp, (BW, BH), interpolation=cv2.INTER_CUBIC)
    mmL = cv2.GaussianBlur(cv2.resize(mm, (BW, BH)).astype(np.float32) / 255, (0, 0), 6)[..., None]
    bg = cv2.GaussianBlur((g * (1 - mmL) + inpL * mmL).astype(np.uint8), (0, 0), 1.6)
    return dict(bg=bg, fg=fg)
_c = {}
def vid(key, path, start, w=W, h=H):
    if key not in _c: _c[key] = Vid(path, start, w, h)
    return _c[key]
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
_grid = None
def grid_bg(col=(0, 120, 70)):
    global _grid
    if _grid is None:
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for x in range(0, W, 90): d.line([x, 0, x, H], fill=(255, 255, 255, 12))
        for y in range(0, H, 90): d.line([0, y, W, y], fill=(255, 255, 255, 12))
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([-200, 500, W + 200, 1500], fill=col + (60,))
        _grid = pil2np(Image.alpha_composite(g.filter(ImageFilter.GaussianBlur(160)), im))
    return _grid
def dark(fr, glow=None):
    fr[:] = (8, 10, 14); blend(fr, grid_bg(), 0, 0)

# ticker tape
TAPE = "  NASDAQ: ANT   •   IPO US$ 83   •   ABERTURA US$ 111,50   •   MÁXIMA US$ 115,10   •   FECHAMENTO US$ 97,17   •   B3: ANTH34   •   US$ 81,3 BI CAPTADOS   "
_tape = None
def tape_img():
    global _tape
    if _tape is None:
        fo = font(MONT, 30)
        tl = int(fo.getlength(TAPE)) + 40; one = Image.new("RGBA", (tl, 62), (0, 0, 0, 0)); ImageDraw.Draw(one).text((10, 12), TAPE, font=fo, fill=GOLD)
        bb = one.getbbox(); one = one.crop((bb[0], 0, bb[2] + 60, 62)); w = one.size[0]
        im = Image.new("RGBA", (w * 3, 62), (12, 14, 18, 230)); d = ImageDraw.Draw(im)
        for k in range(3): im.alpha_composite(one, (k * w, 0))
        d = ImageDraw.Draw(im)
        d.line([0, 0, w * 2, 0], fill=GOLD + (255,), width=2); d.line([0, 61, w * 2, 61], fill=GOLD + (255,), width=2)
        _tape = (pil2np(im), w)
    return _tape
def draw_tape(fr, t, y=215, a=1.0):
    img, w = tape_img(); off = int((t * 140) % w)
    blend(fr, img[:, off:off + W], 0, y, a)

def ticker_card(up, txt):
    col = GREEN if up else RED; arrow_ = "▲" if up else "▼"
    im = Image.new("RGBA", (760, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    gl = Image.new("RGBA", (760, 330), (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle([30, 30, 730, 300], 40, fill=col + (150,))
    im = Image.alpha_composite(im, gl.filter(ImageFilter.GaussianBlur(26))); d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 40, 720, 290], 36, fill=(10, 12, 16, 245), outline=col + (255,), width=5)
    f1 = font(ANTON, 92); f2 = font(ANTON, 150)
    d.text((80, 60), "ANT", font=f1, fill=WHITE); d.text((80, 160), "NASDAQ", font=font(MONT, 34), fill=GREY)
    s = ("+" if up else "-") + txt; l, t_, r, b = f2.getbbox(s)
    x0 = 690 - r; d.text((x0, 165 - (b + t_) / 2), s, font=f2, fill=col)
    ax = x0 - 70; ay = 165
    if up: d.polygon([(ax - 34, ay + 26), (ax + 34, ay + 26), (ax, ay - 34)], fill=col)
    else: d.polygon([(ax - 34, ay - 26), (ax + 34, ay - 26), (ax, ay + 34)], fill=col)
    return pil2np(im)
CARD_UP = ticker_card(True, "34%"); CARD_DN = ticker_card(False, "13%")

# ---------------- scenes ----------------
def s_hook(fr, t):
    v = vid("hook", O + "1b4c3ef2a3c248848e378dd9fab6c9ae.mov", 1.0, 540, 960).get(t)
    np.copyto(fr, blur_bg(v, 0.42, 1.5))
    fr[:] = vignette(fr)
    tf = K(0, "prejuízo")
    # counter
    t1 = WT(0, 0)
    if t < K(0, "E") - 0.1:
        slam(fr, text3d("MAIOR IPO", 168, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 470, t1, t)
        slam(fr, text3d("DA HISTÓRIA", 128, (255, 236, 160), GOLD, (90, 55, 5), None, ANTON, glow=(255, 160, 0)), W / 2, 640, K(0, "história"), t)
        if t > t1:
            u = ease((t - t1) / 1.1); val = 81.3 * u
            blend_c(fr, text3d(f"US$ {val:0.1f} BI".replace(".", ","), 120, GREEN, GREEN2, (0, 60, 30), None, ANTON, glow=(0, 200, 100)), W / 2, 900, 1.0)
    else:
        ta = K(0, "abertura")
        if t < tf - 0.05:
            slam(fr, text3d("QUEM COMPROU", 120, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 420, K(0, "E"), t)
            slam(fr, text3d("NA ABERTURA...", 120, YEL, GOLD, (80, 55, 0)), W / 2, 560, ta, t)
            slam(fr, CARD_UP, W / 2, 900, ta, t, 0.25, 0.3)
        else:
            k = (t - tf + 0.05) / 0.18
            if k < 1:
                sq = abs(math.cos(k * math.pi))
                card = CARD_UP if k < 0.5 else CARD_DN
                c2 = cv2.resize(card, (card.shape[1], max(2, int(card.shape[0] * sq))))
                blend_c(fr, c2, W / 2, 900)
            else:
                blend_c(fr, CARD_DN, W / 2, 900, 1, 1 + 0.15 * (1 - ease((k - 1) / 2)))
            slam(fr, text3d("SAIU NO", 120, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 420, K(0, "saiu"), t)
            slam(fr, text3d("PREJUÍZO", 150, (255, 150, 150), RED, (90, 10, 15), None, ANTON, glow=(255, 40, 40)), W / 2, 575, tf, t, 0.2, 0.6)
            if t > tf: fr[:] = (fr.astype(np.float32) * np.array([1.08, 0.86, 0.86])).clip(0, 255).astype(np.uint8)

def s_context(fr, t):
    dark(fr); p = 1
    draw_tape(fr, t)
    tA = WT(1, 0); t83 = K(1, "US$ 83"); t81 = K(1, "US$ 81"); tsx = K(1, "Mais")
    if t < t83 - 0.1:
        slam(fr, text3d("ANTHROPIC", 150, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 560, K(1, "Anthropic"), t)
        if t > K(1, "dona") - 0.05:
            blend_c(fr, label("DONA DO CLAUDE", 46, (8, 10, 12), GOLD, 255, 30, 14), W / 2, 720, clamp01((t - K(1, "dona")) / 0.2) , 0.7 + 0.3 * back((t - K(1, "dona")) / 0.35))
        if t > K(1, "estreou") - 0.05:
            kk = (t - K(1, "estreou")) / 0.3
            blend_c(fr, label("NASDAQ · ANT", 54, WHITE, (12, 14, 18), 240, 34, 16, border=GREEN), W / 2, 900, clamp01(kk * 2), 0.7 + 0.3 * back(kk))
            blend_c(fr, label("19/11/2026", 34, GREY, (12, 14, 18), 200, 22, 10), W / 2, 1010, clamp01(kk * 2 - 0.5))
    elif t < t81 - 0.1:
        blend_c(fr, label("PREÇO DO IPO", 40, (8, 10, 12), GOLD, 255, 26, 12), W / 2, 480, clamp01((t - t83 + 0.1) / 0.2))
        slam(fr, text3d("US$ 83", 230, (255, 236, 160), GOLD, (90, 55, 5), None, ANTON, glow=(255, 160, 0)), W / 2, 720, t83, t)
        blend_c(fr, plain("faixa prevista: US$ 70–78", 34, GREY, MONTR), W / 2, 930, clamp01((t - t83 - 0.3) / 0.3))
    elif t < tsx - 0.1:
        blend_c(fr, label("CAPTADOS", 40, (8, 10, 12), GREEN, 255, 26, 12), W / 2, 480, clamp01((t - t81 + 0.1) / 0.2))
        u = ease((t - t81) / 1.0); val = 81.3 * u
        blend_c(fr, text3d(f"US$ {val:0.1f} BI".replace(".", ","), 170, GREEN, GREEN2, (0, 60, 30), None, ANTON, glow=(0, 200, 100)), W / 2, 720, clamp01((t - t81 + 0.06) / 0.12), 1 + 0.3 * (1 - ease((t - t81) / 0.25)))
    else:
        k = (t - tsx + 0.1)
        blend_c(fr, text3d("RECORDE", 140, (255, 236, 160), GOLD, (90, 55, 5), None, ANTON, glow=(255, 160, 0)), W / 2, 420, clamp01(k / 0.2), 1 + 0.3 * (1 - ease(k / 0.25)))
        for i, (name, val, col, y) in enumerate([("SPACEX", 75.0, (110, 120, 132), 700), ("ANTHROPIC", 81.3, GOLD, 900)]):
            kk = clamp01((k - 0.05 - i * 0.15) / 0.4); u = ease(kk)
            im = Image.new("RGBA", (900, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.text((0, 0), name, font=font(MONT, 34), fill=WHITE)
            bw = int(820 * (val / 81.3) * u); d.rounded_rectangle([0, 56, max(20, bw), 126], 16, fill=col + (255,))
            txt = f"US$ {val * u:0.1f} BI".replace(".", ","); f = font(ANTON, 50); l, t_, r, b = f.getbbox(txt)
            tx = max(10, bw - (r - l) - 20) if bw > (r - l) + 40 else bw + 16
            d.text((tx, 91 - (b + t_) / 2), txt, font=f, fill=(10, 12, 16) if bw > (r - l) + 40 else WHITE)
            blend(fr, pil2np(im), 90, y, clamp01(kk * 3))

# chart
PATH = [(0.12, 111.5), (0.15, 109.8), (0.18, 113.0), (0.22, 111.6), (0.26, 114.2), (0.30, 115.1), (0.34, 112.0), (0.40, 108.5),
        (0.46, 109.6), (0.52, 104.8), (0.58, 106.0), (0.64, 101.5), (0.70, 102.8), (0.76, 99.0), (0.82, 100.4), (0.88, 97.6), (0.92, 98.4), (0.95, 97.17)]
CW_, CH_ = 980, 880; PMIN, PMAX = 76, 121
def cy(p): return 60 + (PMAX - p) / (PMAX - PMIN) * (CH_ - 140)
def cx(x): return 40 + x * (CW_ - 80)
def path_until(xr):
    pts = []
    for (x, p) in PATH:
        if x <= xr: pts.append((cx(x), cy(p)))
        else:
            if pts:
                (x0, p0) = [q for q in PATH if q[0] <= xr][-1]; f = (xr - x0) / (x - x0)
                pts.append((cx(xr), cy(p0 + (p - p0) * f)))
            break
    return pts
def price_at(xr):
    prev = PATH[0]
    for q in PATH:
        if q[0] >= xr:
            if q[0] == prev[0]: return q[1]
            f = (xr - prev[0]) / (q[0] - prev[0]); return prev[1] + (q[1] - prev[1]) * f
        prev = q
    return PATH[-1][1]
def chart(t):
    im = Image.new("RGBA", (CW_, CH_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, CW_ - 1, CH_ - 1], 38, fill=(10, 13, 19, 215), outline=(255, 255, 255, 46), width=2)
    for p in (80, 90, 100, 110, 120):
        y = cy(p); d.line([30, y, CW_ - 30, y], fill=(255, 255, 255, 16)); d.text((CW_ - 80, y - 30), f"{p}", font=font(MONTR, 22), fill=(140, 150, 160))
    tO = K(2, "abriu"); tB = WT(3, 0); tF = K(3, "fechou"); t13 = K(3, "13%"); tS = SC[2]
    # IPO line
    a = clamp01((t - tS) / 0.3)
    dashed_line(d, (30, cy(83)), (CW_ - 30, cy(83)), GOLD + (int(220 * a),), 3)
    if a > 0: im.alpha_composite(Image.fromarray(label("IPO US$ 83", 26, (8, 10, 12), GOLD, 255, 14, 7)), (50, int(cy(83) - 52)))
    # pre-open stub
    d.line([cx(0.02), cy(83), cx(0.10), cy(83)], fill=GOLD + (int(255 * a),), width=6)
    # reveal
    if t < tO: xr = 0
    elif t < tB - 0.05: xr = 0.12 + 0.10 * ease_io((t - tO - 0.3) / max(0.5, (tB - tO - 0.6)))
    elif t < tF: xr = 0.22 + 0.08 * ease((t - tB + 0.05) / 0.6)
    else: xr = 0.30 + 0.65 * ease_io((t - tF) / 1.4)
    if t >= tO:
        # gap
        ug = ease((t - tO) / 0.3); yg = cy(83) + (cy(111.5) - cy(83)) * ug
        dashed_line(d, (cx(0.11), cy(83)), (cx(0.11), yg), GREEN + (255,), 4, 10, 7)
        if ug > 0.95: im.alpha_composite(Image.fromarray(label("GAP +34%", 28, (8, 10, 12), GREEN, 255, 14, 7)), (int(cx(0.11) + 14), int((cy(83) + cy(111.5)) / 2 - 22)))
    if xr >= 0.12:
        pts = path_until(xr)
        if t >= t13 - 0.05:
            ov = Image.new("RGBA", (CW_, CH_), (0, 0, 0, 0)); u = ease((t - t13 + 0.05) / 0.3)
            ImageDraw.Draw(ov).rectangle([cx(0.12), cy(111.5), cx(0.12) + (cx(0.95) - cx(0.12)) * u, cy(97.17)], fill=(255, 60, 60, 60))
            im = Image.alpha_composite(im, ov); d = ImageDraw.Draw(im)
            dashed_line(d, (cx(0.12), cy(111.5)), (cx(0.97), cy(111.5)), (255, 255, 255, 160), 2)
        gl = Image.new("RGBA", (CW_, CH_), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
        hi = [i for i, q in enumerate(pts) if True]
        # split color at the high
        xh = cx(0.30); up_pts = [q for q in pts if q[0] <= xh + 0.1]; dn_pts = [q for q in pts if q[0] >= xh - 0.1]
        if len(up_pts) > 1: gd.line(up_pts, fill=GREEN + (200,), width=16, joint="curve");
        if len(dn_pts) > 1: gd.line(dn_pts, fill=RED + (200,), width=16, joint="curve")
        im = Image.alpha_composite(im, gl.filter(ImageFilter.GaussianBlur(10))); d = ImageDraw.Draw(im)
        if len(up_pts) > 1: d.line(up_pts, fill=GREEN + (255,), width=6, joint="curve")
        if len(dn_pts) > 1: d.line(dn_pts, fill=RED + (255,), width=6, joint="curve")
        hx, hy = pts[-1]; cp = price_at(xr); col = GREEN if xr <= 0.30 else RED
        d.ellipse([hx - 11, hy - 11, hx + 11, hy + 11], fill=col + (255,), outline=WHITE + (255,), width=3)
        tag = label(f"US$ {cp:0.2f}".replace(".", ","), 28, (8, 10, 12), col, 255, 14, 7)
        im.alpha_composite(Image.fromarray(tag), (int(min(hx + 18, CW_ - tag.shape[1] - 10)), int(hy - tag.shape[0] - 14)))
        if t >= tB + 0.4:
            tg = label("MÁX US$ 115,10", 26, WHITE, (12, 14, 18), 235, 14, 7, border=GREEN)
            im.alpha_composite(Image.fromarray(tg), (int(cx(0.30) - tg.shape[1] / 2), int(cy(115.1) - 70)))
        if t >= tF + 1.4:
            tg = label("FECHAMENTO US$ 97,17", 26, WHITE, (12, 14, 18), 235, 14, 7, border=RED)
            im.alpha_composite(Image.fromarray(tg), (int(cx(0.95) - tg.shape[1] + 10), int(cy(97.17) + 26)))
    d.text((40, CH_ - 46), "trajetória ilustrativa · preços: Forbes/NBC", font=font(MONTR, 20), fill=(120, 128, 138))
    return np.asarray(im).copy()

BTN = label("COMPRAR", 40, (8, 10, 12), GREEN, 255, 30, 14)
random.seed(3)
RAIN = [(random.uniform(120, 960), random.uniform(0, 1.5), random.uniform(-14, 14), random.uniform(0.7, 1.15)) for _ in range(16)]
def s_chart(fr, t):
    p = scene_of(t); dark(fr); draw_tape(fr, t)
    tS = SC[2]; k_in = ease((t - tS) / 0.45)
    title = "ABERTURA" if p == 2 else "FECHAMENTO"
    colt = GREEN if p == 2 else RED
    slam(fr, text3d(title, 120, tuple(int(255 - (255 - c) * 0.2) for c in colt), colt, tuple(int(c * 0.3) for c in colt), None, ANTON, glow=colt), W / 2, 360, SC[p] + 0.1, t)
    ch = chart(t)
    pv = persp(ch, -5 + 8 * clamp01((t - tS) / (SC[4] - tS)), 3, 0.9 + 0.08 * k_in)
    blend_c(fr, pv, W / 2, 880)
    if p == 2:
        t34 = K(2, "34%")
        if t > t34 - 0.05: slam(fr, text3d("+34%", 170, (170, 255, 200), GREEN, (0, 60, 30), None, ANTON, glow=(0, 220, 110)), 790, 610, t34, t, 0.25, 0.6)
        tm = K(2, "manada")
        if t > tm - 0.05:
            for i, (x, dl, rot, s) in enumerate(RAIN):
                tt = t - tm - dl * 0.8
                if tt < 0: continue
                y = 300 + tt * 900 * s
                if y > 1500: continue
                blend_c(fr, BTN, x, y, clamp01(tt / 0.1) * 0.95, 0.75 * s * (1 + 0.3 * (1 - ease(tt / 0.2))), rot)
    else:
        t13 = K(3, "13%")
        if t > t13 - 0.05:
            slam(fr, text3d("-13%", 190, (255, 150, 150), RED, (90, 10, 15), None, ANTON, glow=(255, 40, 40)), 760, 640, t13, t, 0.2, 0.7)
            blend_c(fr, label("PRA QUEM COMPROU NA ABERTURA", 30, WHITE, (12, 14, 18), 235, 18, 9, border=RED), 700, 770, clamp01((t - t13 - 0.15) / 0.2))
        if t > t13 + 0.9:
            blend_c(fr, plain("(ainda +17% sobre o preço do IPO)", 28, GREY, MONTR), W / 2, 1255, clamp01((t - t13 - 0.9) / 0.3))

_les = None
def lesson_img():
    global _les
    if _les is None:
        img = grade(load_img("lesson_src_c.jpg"))
        x = np.arange(img.shape[1], dtype=np.float32)
        g = np.clip(0.5 + 0.5 * x / (img.shape[1] * 0.6), 0.5, 1.0)[None, :, None]
        _les = (img.astype(np.float32) * g).astype(np.uint8)
    return _les
def s_lesson(fr, t):
    tS = SC[4]; dur = SC[5] - tS; u = (t - tS) / dur
    np.copyto(fr, view(lesson_img(), 1.03 + 0.07 * ease_io(u), cx=0.515, cy=0.46, dy=-6 * u))
    tn = K(4, "Mas"); th = K(4, "Quem"); X = 300
    if t < tn - 0.1:
        slam(fr, text3d("A EMPRESA", 92, WHITE, (210, 215, 225), (35, 38, 48)), X, 300, WT(4, 0), t)
        slam(fr, text3d("É BOA?", 128, YEL, GOLD, (80, 55, 0)), X, 425, K(4, "boa"), t)
        slam(fr, label("PODE SER.", 44, (8, 10, 12), WHITE, 255, 26, 12), X, 560, K(4, "Pode"), t, 0.3, 0.3)
    elif t < th - 0.1:
        slam(fr, text3d("NOTÍCIA", 124, WHITE, (210, 215, 225), (35, 38, 48)), X, 290, K(4, "notícia"), t)
        slam(fr, text3d("NÃO É", 104, (255, 150, 150), RED, (90, 10, 15), None, ANTON), X, 420, K(4, "não"), t)
        slam(fr, text3d("ENTRADA", 124, (255, 236, 160), GOLD, (90, 55, 5), None, ANTON, glow=(255, 160, 0)), X, 550, K(4, "entrada"), t)
    if t >= th - 0.1:
        for i, (w_, txt) in enumerate([("hype", "HYPE"), ("região", "SEM REGIÃO"), ("plano", "SEM PLANO")]):
            tw = K(4, w_)
            if t > tw - 0.05:
                kk = (t - tw + 0.05) / 0.3
                blend_c(fr, label(txt, 52, WHITE, (40, 8, 10), 245, 32, 15, border=RED), X, 290 + i * 120, clamp01(kk * 2), 0.6 + 0.4 * back(kk))
        if t > K(4, "paga") - 0.1:
            slam(fr, label("PAGA O PREÇO", 42, WHITE, (40, 8, 10), 245, 26, 12, border=RED), X, 660, K(4, "paga"), t, 0.3, 0.3)
            confetti(fr, t - K(4, "caro"))
    tc = K(4, "caro")
    if t > tc - 0.1: slam(fr, text3d("MAIS CARO", 124, (255, 150, 150), RED, (90, 10, 15), None, ANTON, glow=(255, 40, 40)), 380, 800, tc, t)

random.seed(11)
CONF = [(random.uniform(0, W), random.uniform(-600, 0), random.uniform(0.6, 1.4), random.choice([GOLD, RED, GREEN, WHITE]), random.uniform(0, 6.28)) for _ in range(60)]
def confetti(fr, tt):
    for (x, y0, s, col, ph) in CONF:
        y = y0 + tt * 700 * s; xx = x + 30 * math.sin(tt * 3 + ph)
        if 0 < y < H:
            w = int(14 * s); h = int(8 * s); ang = tt * 6 + ph
            c, sn = math.cos(ang), math.sin(ang)
            pts = np.array([[xx + c * -w - sn * -h, y + sn * -w + c * -h], [xx + c * w - sn * -h, y + sn * w + c * -h],
                            [xx + c * w - sn * h, y + sn * w + c * h], [xx + c * -w - sn * h, y + sn * -w + c * h]], np.int32)
            cv2.fillConvexPoly(fr, pts, col, lineType=cv2.LINE_AA)

ST = {}
def st(key, path, fx=0.5):
    if key not in ST: ST[key] = layers25(path, fx)
    return ST[key]

def s_bdr(fr, t):
    v = vid("bdr", O + "c4cf8640d78f460cb7130ecb55f778f6.MOV", 2.0, 270, 480).get(t - SC[5])
    np.copyto(fr, blur_bg(v, 0.42, 2.2))
    tb = K(5, "BDR"); ta = K(5, "ANTH34")
    slam(fr, label("TAMBÉM NO BRASIL", 40, (8, 10, 12), GOLD, 255, 26, 12), W / 2, 420, tb, t, 0.3, 0.3)
    slam(fr, text3d("ANTH34", 210, WHITE, (210, 215, 225), (35, 38, 48), None, ANTON, glow=(0, 160, 90)), W / 2, 640, ta, t)
    if t > ta + 0.3:
        blend_c(fr, label("B3 · BDR", 52, WHITE, (12, 14, 18), 240, 32, 15, border=GREEN), W / 2, 850, clamp01((t - ta - 0.3) / 0.2))
        blend_c(fr, plain("1 ação = 8 BDRs", 34, GREY, MONTR), W / 2, 950, clamp01((t - ta - 0.5) / 0.3))
    tl_ = K(5, "lição")
    if t > tl_ - 0.05:
        slam(fr, text3d("MESMA LIÇÃO", 110, (255, 236, 160), GOLD, (90, 55, 5), None, ANTON, glow=(255, 160, 0)), W / 2, 1130, tl_, t)

_gr = None
def grads():
    global _gr
    if _gr is None:
        y = np.arange(H, dtype=np.float32)[:, None]
        top = np.clip(1 - y / 520, 0, 1) * 0.65; bot = np.clip((y - 1050) / 700, 0, 1) * 0.7
        _gr = (1 - np.maximum(top, bot))[..., None]
    return _gr
def s_cta(fr, t):
    v = vid("cta", "/mnt/user-data/uploads/Documents/CWTrader-Instagram/05-Videos-originais/RPReplay_Final1692063704.mov", 19.5, 886, 1440).get(t - SC[6])
    u = clamp01((t - SC[6]) / (DUR - SC[6]))
    vv = view(v, 1.35 + 0.05 * u, cx=0.5, cy=0.25)
    np.copyto(fr, (grade(vv, 0.95).astype(np.float32) * grads()).astype(np.uint8))
    slam(fr, text3d("SALVA", 130, WHITE, (210, 215, 225), (35, 38, 48)), W / 2, 200, WT(6, 0), t)
    slam(fr, text3d("+ SEGUE", 112, YEL, GOLD, (80, 55, 0)), W / 2, 330, K(6, "segue"), t)
    ta = K(6, "aprender")
    if t > ta - 0.05:
        slam(fr, label("LEIA O GRÁFICO ANTES DE APERTAR O BOTÃO", 32, WHITE, (12, 14, 18), 235, 20, 10, border=GOLD), W / 2, 1075, ta, t, 0.3, 0.3)
    tl_ = K(6, "link")
    if t > tl_ - 0.05 and t < T_END:
        k5 = (t - tl_ + 0.05) / 0.3
        blend_c(fr, label("LINK NA BIO", 58, (8, 10, 12), GREEN, 255, 40, 18), W / 2, 1190, clamp01(k5 * 2), 0.6 + 0.4 * back(k5))

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
    if p == 0: s_hook(fr, t)
    elif p == 1: s_context(fr, t)
    elif p in (2, 3): s_chart(fr, t)
    elif p == 4: s_lesson(fr, t)
    elif p == 5: s_bdr(fr, t)
    else:
        s_cta(fr, t)
        if t >= T_END: end_card(fr, t)
    for q in range(1, NP):
        dtq = t - SC[q]
        if q == 3: continue  # chart continues
        if 0 <= dtq < 0.16:
            k = 1 - dtq / 0.16; sh = int((1 if q % 2 else -1) * 160 * k)
            fr = np.roll(fr, sh, axis=1); fr = motion_blur(fr, 60 * k)
            if dtq < 0.04: fr = cv2.convertScaleAbs(fr, alpha=1.0, beta=60 * (1 - dtq / 0.04))
    tf = K(0, "prejuízo")
    if tf - 0.05 <= t < tf + 0.25: fr = rgb_split(fr, 18 * (1 - (t - tf + 0.05) / 0.3))
    fr = shake(fr, t, tf, 0.4, 26)
    fr = shake(fr, t, K(3, "13%"), 0.35, 20)
    if t < 0.1 + 0.12: fr = cv2.convertScaleAbs(fr, alpha=1.0, beta=max(0, 120 * (1 - (t - 0.1) / 0.12))) if t >= 0.1 else fr
    draw_caption(fr, t)
    return fr

# sfx
sfx(WT(0, 0), "impact", 1.0); sfx(K(0, "história"), "hit", 0.6)
for i in range(8): sfx(WT(0, 0) + i * 0.12, "tick", 0.25)
sfx(K(0, "abertura"), "whoosh", 0.5); sfx(K(0, "prejuízo"), "impact", 0.9); sfx(K(0, "prejuízo"), "buzz", 0.5)
sfx(K(1, "Anthropic"), "hit", 0.45); sfx(K(1, "estreou"), "pop", 0.5); sfx(K(1, "US$ 83"), "hit", 0.6)
sfx(K(1, "US$ 81"), "cash", 0.6)
for i in range(6): sfx(K(1, "US$ 81") + i * 0.15, "tick", 0.22)
sfx(K(1, "Mais"), "ding", 0.5)
sfx(K(2, "abriu"), "whoosh", 0.6); sfx(K(2, "34%"), "hit", 0.6)
for i, (x, dl, rot, s) in enumerate(RAIN): sfx(K(2, "manada") + dl * 0.8, "pop", 0.35)
sfx(WT(3, 0), "whoosh_s", 0.4); sfx(K(3, "fechou"), "rewind", 0.5); sfx(K(3, "13%"), "impact", 0.85)
sfx(K(4, "boa"), "pop", 0.4); sfx(K(4, "notícia"), "hit", 0.5); sfx(K(4, "entrada"), "hit", 0.6)
for w_ in ("hype", "região", "plano"): sfx(K(4, w_), "buzz", 0.35)
sfx(K(4, "caro"), "impact", 0.7)
sfx(K(5, "ANTH34"), "hit", 0.55); sfx(K(5, "lição"), "ding", 0.45)
sfx(WT(6, 0), "pop", 0.5); sfx(K(6, "segue"), "pop", 0.5); sfx(K(6, "link"), "cash", 0.45); sfx(T_END, "impact", 0.7)
for q in range(1, NP):
    if q != 3: sfx(SC[q], "whoosh", 0.5)

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "info":
        print("DUR", DUR, "SC", [round(s, 2) for s in SC], "T_END", T_END)
        json.dump(dict(DUR=DUR, SFX=SFX, SC=SC, T_END=T_END), open("timeline.json", "w"))
    elif mode == "stills":
        os.makedirs("stills", exist_ok=True)
        for t in [float(x) for x in sys.argv[2].split(",")]:
            t0 = time.time(); Image.fromarray(frame(t)).save(f"stills/t{t:06.2f}.jpg", quality=85); print(t, round(time.time() - t0, 2))
    elif mode == "render":
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        t0 = time.time()
        for i in range(a, b):
            enc.stdin.write(frame(i / FPS).tobytes())
            if (i - a) % 150 == 0: print(out, i, round(time.time() - t0, 1), flush=True)
        enc.stdin.close(); enc.wait()
