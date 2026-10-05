#!/usr/bin/env python3
"""ForeSite social graphic renderer.

Usage:
  python3 tools/render.py spec.json            # render PNGs into weekly/<week>/
  python3 tools/render.py spec.json --check    # render to /tmp only (preview)

spec.json:
{
  "week": "2026-10-12",                      # Monday of the posting week
  "graphics": [
    {
      "slug": "mon-planned-vs-reactive",     # file name (lowercase, hyphens)
      "eyebrow": "Planned maintenance",      # optional small label above headline
      "headline": "Stop firefighting. Plan the work.",   # up to ~10 words
      "lines": ["Point one", "Point two", "Point three"],  # 0-3 short lines
      "cta": "Request a demo at foresite-solutions.com"   # optional, default below
    }
  ]
}
"""
import json, os, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(HERE, "fonts")
STATIC = {"ExtraBold": "PlusJakartaSans-ExtraBold.ttf", "Regular": "Inter-Regular.ttf", "SemiBold": "Inter-SemiBold.ttf"}
FONT_HEAD = FONT_BODY = None  # resolved by weight
LOGO = os.path.join(HERE, "brand", "logo-dark-bg.png")

# Brand colours (from foresite-solutions.com styles.css)
NAVY_950 = (7, 13, 36)
NAVY_900 = (11, 20, 51)
NAVY_800 = (17, 29, 71)
NAVY_700 = (27, 43, 94)
CYAN = (0, 180, 216)
CYAN_2 = (72, 212, 240)
ON_DARK = (238, 243, 255)
MUTED_ON_DARK = (170, 184, 214)

W = H = 1080
PAD = 84
DEFAULT_CTA = "Request a demo at foresite-solutions.com"


def font(_path, size, weight):
    # static instances (Plus Jakarta Sans ExtraBold for headlines, Inter for body)
    return ImageFont.truetype(os.path.join(FONTS, STATIC[weight]), size)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    # avoid a single orphan word on the last line
    if len(lines) > 1 and len(lines[-1].split()) == 1 and len(lines[-2].split()) > 2:
        prev = lines[-2].split()
        lines[-2], lines[-1] = " ".join(prev[:-1]), prev[-1] + " " + lines[-1]
    return lines


def background():
    img = Image.new("RGB", (W, H), NAVY_900)
    d = ImageDraw.Draw(img)
    # vertical gradient navy-900 -> navy-950
    for y in range(H):
        t = y / H
        c = tuple(int(NAVY_800[i] * (1 - t) + NAVY_950[i] * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    # soft cyan glow, top right
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([W - 520, -380, W + 380, 420], fill=110)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img = Image.composite(Image.new("RGB", (W, H), CYAN), img, glow.point(lambda v: int(v * 0.55)))
    # thin grid lines for texture
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, W, 90):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 7))
    for y in range(0, H, 90):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 7))
    return img


def render(g, out_path):
    img = background()
    d = ImageDraw.Draw(img, "RGBA")
    max_w = W - 2 * PAD

    # logo top left
    logo = Image.open(LOGO).convert("RGBA")
    lw = 300
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.paste(logo, (PAD - 10, PAD - 20), logo)

    # CTA pill at the bottom
    cta = (g.get("cta") or DEFAULT_CTA).strip()
    f_cta = font(FONT_BODY, 34, "SemiBold")
    tw = d.textlength(cta, font=f_cta)
    ph = 84
    pw = min(max_w, int(tw + 80))
    py = H - PAD - ph
    d.rounded_rectangle([PAD, py, PAD + pw, py + ph], radius=ph // 2, fill=CYAN)
    d.text((PAD + 40, py + ph / 2), cta, font=f_cta, fill=NAVY_950, anchor="lm")

    # content block: eyebrow, headline, lines, vertically placed in the middle band
    top_limit = PAD + 140
    bottom_limit = py - 60
    eyebrow = (g.get("eyebrow") or "").strip().upper()
    headline = g["headline"].strip()
    lines = [l.strip() for l in g.get("lines", []) if l.strip()][:3]

    for hsize in range(88, 47, -4):
        f_eye = font(FONT_BODY, 28, "SemiBold")
        f_head = font(FONT_HEAD, hsize, "ExtraBold")
        f_line = font(FONT_BODY, max(30, int(hsize * 0.44)), "Regular")
        h_lines = wrap(d, headline, f_head, max_w)
        b_lines = [wrap(d, l, f_line, max_w - 64) for l in lines]
        head_lh = int(hsize * 1.12)
        line_lh = int(f_line.size * 1.35)
        total = (48 if eyebrow else 0) + head_lh * len(h_lines)
        if lines:
            total += 50 + sum(len(b) * line_lh + 26 for b in b_lines)
        if total <= bottom_limit - top_limit:
            break

    y = top_limit + max(0, (bottom_limit - top_limit - total) // 2)
    if eyebrow:
        d.rectangle([PAD, y + 6, PAD + 44, y + 12], fill=CYAN_2)
        d.text((PAD + 60, y), eyebrow, font=f_eye, fill=CYAN_2)
        y += 48
    for hl in h_lines:
        d.text((PAD, y), hl, font=f_head, fill=(255, 255, 255))
        y += head_lh
    if lines:
        y += 50
        for b in b_lines:
            # tick badge
            cy = y + line_lh // 2 - 2
            d.ellipse([PAD, cy - 18, PAD + 36, cy + 18], fill=(0, 180, 216, 46), outline=CYAN, width=2)
            d.line([(PAD + 10, cy), (PAD + 16, cy + 7), (PAD + 27, cy - 8)], fill=CYAN_2, width=4, joint="curve")
            for bl in b:
                d.text((PAD + 64, y), bl, font=f_line, fill=ON_DARK)
                y += line_lh
            y += 26

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


def main():
    spec = json.load(open(sys.argv[1]))
    week = spec["week"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", week), "week must be YYYY-MM-DD"
    check = "--check" in sys.argv
    base = "/tmp/foresite-preview" if check else os.path.join(ROOT, "weekly", week)
    for g in spec["graphics"]:
        slug = re.sub(r"[^a-z0-9-]+", "-", g["slug"].lower()).strip("-")
        p = render(g, os.path.join(base, slug + ".png"))
        print(os.path.relpath(p, ROOT) if not check else p)


if __name__ == "__main__":
    main()
