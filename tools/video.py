#!/usr/bin/env python3
"""ForeSite short video renderer (square 1080x1080, 30fps, ~15s, silent with on-screen text).

Usage: python3 tools/video.py video.json out.mp4

video.json: {"scenes": [ ... ]}, each scene has "type" and "seconds":
  {"type": "hook",   "seconds": 3,   "text": "Something breaks at 2am.", "bg": "cyan"|"navy"}
  {"type": "lines",  "seconds": 4,   "eyebrow": "...", "headline": "...", "lines": ["a", "b", "c"]}
  {"type": "portal", "seconds": 5,   "headline": "...", "rows": [{"label": "...", "status": "Done"}]}
  {"type": "end",    "seconds": 3.5, "headline": "Every call logged."}
"""
import json, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R

FPS = 30
W = H = 1080
PAD = R.PAD


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def put(img, lyr, alpha, dy):
    if alpha <= 0:
        return
    a = lyr.split()[3].point(lambda v: int(v * alpha))
    lyr.putalpha(a)
    img.alpha_composite(lyr, (0, int(dy)))


def anim(t, start, dur=0.45):
    p = ease((t - start) / dur)
    return p, (1 - p) * 40


def cyan_bg():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(R.CYAN[i] * (1 - k) + (0, 120, 160)[i] * k) for i in range(3)))
    return img


BG_CACHE = {}


def bg(kind):
    if kind not in BG_CACHE:
        BG_CACHE[kind] = (cyan_bg() if kind == "cyan" else R.background()).convert("RGBA")
    return BG_CACHE[kind].copy()


def logo_layer(mode):
    l = layer()
    logo = R.logo_for(mode)
    lw = 300
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    l.paste(logo, (PAD - 10, PAD - 20), logo)
    return l


def scene_hook(s, t):
    kind = s.get("bg", "cyan")
    img = bg(kind)
    put(img, logo_layer("mono" if kind == "cyan" else False), 1, 0)
    words = s["text"].split()
    d0 = ImageDraw.Draw(img)
    f, lines, lh = fit_text(d0, s["text"], W - 2 * PAD, 600, sizes=range(120, 59, -6))
    y = (H - lh * len(lines)) // 2
    i = 0
    col = R.NAVY_950 if kind == "cyan" else (255, 255, 255)
    for ln in lines:
        x = PAD
        for w in ln.split():
            p, dy = anim(t, 0.2 + i * 0.12, 0.35)
            l = layer()
            ImageDraw.Draw(l).text((x, y), w, font=f, fill=col)
            put(img, l, p, dy)
            x += d0.textlength(w + " ", font=f)
            i += 1
        y += lh
    return img


def scene_lines(s, t):
    img = bg("navy")
    put(img, logo_layer(False), 1, 0)
    d0 = ImageDraw.Draw(img)
    y = PAD + 190
    if s.get("eyebrow"):
        p, dy = anim(t, 0.1)
        l = layer(); dl = ImageDraw.Draw(l)
        dl.rectangle([PAD, y + 6, PAD + 44, y + 12], fill=R.CYAN_2)
        dl.text((PAD + 60, y), s["eyebrow"].upper(), font=R.font(None, 28, "SemiBold"), fill=R.CYAN_2)
        put(img, l, p, dy); y += 52
    f, hl, lh = fit_text(d0, s["headline"], W - 2 * PAD, 260, sizes=range(84, 47, -4))
    p, dy = anim(t, 0.25)
    l = layer(); dl = ImageDraw.Draw(l)
    for ln in hl:
        dl.text((PAD, y), ln, font=f, fill=(255, 255, 255)); y += lh
    put(img, l, p, dy)
    y += 50
    fl = R.font(None, 40, "Regular")
    for i, line in enumerate(s.get("lines", [])[:3]):
        p, dy = anim(t, 0.9 + i * 0.55)
        l = layer(); dl = ImageDraw.Draw(l)
        R.tick(dl, PAD, y + 26, R.CYAN, R.CYAN_2, (0, 180, 216, 46))
        dl.text((PAD + 64, y), line, font=fl, fill=R.ON_DARK)
        put(img, l, p, dy)
        y += 84
    return img


def scene_portal(s, t):
    img = bg("navy")
    put(img, logo_layer(False), 1, 0)
    d0 = ImageDraw.Draw(img)
    y = PAD + 170
    f, hl, lh = fit_text(d0, s["headline"], W - 2 * PAD, 190, sizes=range(76, 39, -4))
    p, dy = anim(t, 0.1)
    l = layer(); dl = ImageDraw.Draw(l)
    for ln in hl:
        dl.text((PAD, y), ln, font=f, fill=(255, 255, 255)); y += lh
    put(img, l, p, dy)
    y += 40
    rows = s.get("rows", [])[:4]
    ph = H - PAD - 60 - y
    p, dy = anim(t, 0.4)
    l = layer(); dl = ImageDraw.Draw(l)
    dl.rounded_rectangle([PAD, y, W - PAD, y + ph], radius=26, fill=(255, 255, 255))
    for i, c in enumerate([R.CORAL, R.AMBER, R.MINT]):
        dl.ellipse([PAD + 28 + i * 30, y + 24, PAD + 46 + i * 30, y + 42], fill=c)
    dl.line([(PAD, y + 66), (W - PAD, y + 66)], fill=(226, 232, 240), width=2)
    put(img, l, p, dy)
    rh = (ph - 66) // max(1, len(rows))
    fr = R.font(None, 32, "SemiBold"); fp = R.font(None, 26, "SemiBold")
    times = s.get("row_times") or [0.9 + i * 0.6 for i in range(len(rows))]
    for i, r in enumerate(rows):
        cy = y + 66 + i * rh + rh // 2
        p, dy = anim(t, times[i])
        l = layer(); dl = ImageDraw.Draw(l)
        dl.text((PAD + 36, cy), r["label"], font=fr, fill=R.NAVY_900, anchor="lm")
        put(img, l, p, dy * 0.5)
        sp = ease((t - (times[i] + 0.35)) / 0.25)
        if sp > 0:
            st = r["status"]; col = R.STATUS_COLOURS.get(st.lower(), R.CYAN)
            l = layer(); dl = ImageDraw.Draw(l)
            tw = dl.textlength(st, font=fp); x1 = W - PAD - 36
            dl.rounded_rectangle([x1 - tw - 44, cy - 26, x1, cy + 26], radius=26, fill=(*col, 40))
            dl.text((x1 - tw / 2 - 22, cy), st, font=fp, fill=col, anchor="mm")
            put(img, l, sp, 0)
    return img


def scene_end(s, t):
    img = bg("navy")
    d0 = ImageDraw.Draw(img)
    p, dy = anim(t, 0.0, 0.5)
    l = layer()
    logo = R.logo_for(False); lw = 520
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    l.paste(logo, ((W - lw) // 2, 250), logo)
    put(img, l, p, dy)
    f, hl, lh = fit_text(d0, s.get("headline", ""), W - 2 * PAD, 200, sizes=range(64, 35, -4))
    y = 470
    p, dy = anim(t, 0.35)
    l = layer(); dl = ImageDraw.Draw(l)
    for ln in hl:
        dl.text((W // 2, y), ln, font=f, fill=(255, 255, 255), anchor="ma"); y += lh
    put(img, l, p, dy)
    p, dy = anim(t, 0.8)
    l = layer(); dl = ImageDraw.Draw(l)
    cta = s.get("cta", R.DEFAULT_CTA); fc = R.font(None, 36, "SemiBold")
    tw = dl.textlength(cta, font=fc); pw, ph = tw + 90, 92
    x0 = (W - pw) / 2; y0 = 760
    dl.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=46, fill=R.CYAN)
    dl.text((W / 2, y0 + ph / 2), cta, font=fc, fill=R.NAVY_950, anchor="mm")
    put(img, l, p, dy)
    return img


def fit_text(d, text, max_w, max_h, sizes, lh=1.1):
    """Like R.fit_headline but honours explicit line breaks (\n)."""
    for sz in sizes:
        f = R.font(R.FONT_HEAD, sz, "ExtraBold")
        ls = [ln for para in text.split("\n") for ln in R.wrap(d, para, f, max_w)]
        if int(sz * lh) * len(ls) <= max_h:
            break
    return f, ls, int(sz * lh)


SCENES = {"hook": scene_hook, "lines": scene_lines, "portal": scene_portal, "end": scene_end}


def main():
    spec = json.load(open(sys.argv[1])); out = sys.argv[2]
    tmp = tempfile.mkdtemp()
    n = 0
    for s in spec["scenes"]:
        frames = int(s["seconds"] * FPS)
        for k in range(frames):
            t = k / FPS
            img = SCENES[s["type"]](s, t).convert("RGB")
            fade = min(1.0, (frames - k) / 6)  # quick dip at scene end
            if fade < 1:
                img = Image.blend(Image.new("RGB", (W, H), R.NAVY_950), img, fade)
            img.save(os.path.join(tmp, f"f{n:05d}.png")); n += 1
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", out], check=True)
    print(out, f"{n / FPS:.1f}s")


if __name__ == "__main__":
    main()
