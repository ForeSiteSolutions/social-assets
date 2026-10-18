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
      "cta": "Request a demo at foresite-solutions.com",  # optional, default below
      "layout": "classic"                    # optional: classic | light | question | compare | portal | numbered
    }

Layouts (vary them week to week so the feed doesn't look the same every time):
  classic   navy, headline + up to 3 ticked lines (the original look)
  light     white background, navy headline, cyan side bar, ticked lines
  question  bold cyan background, one big question as the headline, optional "answer" line
  compare   two panels: "before" (the usual way) vs "after" (with ForeSite); needs "before": [..] and "after": [..], up to 3 each
  portal    headline over a mock portal panel; "rows": [{"label": "...", "status": "..."}] up to 4 (status: a short word e.g. Done, Booked, Due, Chased)
  numbered  light grey background, headline + up to 3 numbered steps (01, 02, 03): good for "how it works"

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


LIGHT_BG = (246, 248, 252)
SLATE = (90, 104, 132)
MINT = (16, 185, 129)
AMBER = (245, 158, 11)
CORAL = (239, 99, 81)


def logo_for(light):
    logo = Image.open(LOGO).convert("RGBA")
    if light == "mono":  # whole logo in navy, for coloured backgrounds
        px = logo.load()
        for x in range(logo.width):
            for y in range(logo.height):
                r, g, b, a = px[x, y]
                if a:
                    px[x, y] = (*NAVY_950, a)
    elif light:
        px = logo.load()
        for x in range(logo.width):
            for y in range(logo.height):
                r, g, b, a = px[x, y]
                if a and r > 180 and g > 180 and b > 180:  # white / pale text -> navy
                    px[x, y] = (*NAVY_700, a)
    return logo


def paste_logo(img, light, x=PAD - 10, y=PAD - 20, lw=300):
    logo = logo_for(light)
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.paste(logo, (x, y), logo)


def cta_pill(d, g, fill, text_fill, y=None):
    cta = (g.get("cta") or DEFAULT_CTA).strip()
    f_cta = font(FONT_BODY, 34, "SemiBold")
    tw = d.textlength(cta, font=f_cta)
    ph = 84
    pw = min(W - 2 * PAD, int(tw + 80))
    py = H - PAD - ph if y is None else y
    d.rounded_rectangle([PAD, py, PAD + pw, py + ph], radius=ph // 2, fill=fill)
    d.text((PAD + 40, py + ph / 2), cta, font=f_cta, fill=text_fill, anchor="lm")
    return py


def fit_headline(d, text, max_w, max_h, sizes=range(96, 47, -4), lh=1.1):
    for s in sizes:
        f = font(FONT_HEAD, s, "ExtraBold")
        ls = wrap(d, text, f, max_w)
        if int(s * lh) * len(ls) <= max_h:
            return f, ls, int(s * lh)
    return f, ls, int(s * lh)


def tick(d, x, cy, ring, check, bg=None):
    d.ellipse([x, cy - 18, x + 36, cy + 18], fill=bg, outline=ring, width=2)
    d.line([(x + 10, cy), (x + 16, cy + 7), (x + 27, cy - 8)], fill=check, width=4, joint="curve")


def render_light(g, out_path):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, 22, H], fill=CYAN)
    d.ellipse([W - 360, H - 360, W + 200, H + 200], fill=(0, 180, 216, 22))
    paste_logo(img, True)
    py = cta_pill(d, g, NAVY_700, (255, 255, 255))
    max_w = W - 2 * PAD
    eyebrow = (g.get("eyebrow") or "").strip().upper()
    lines = [l.strip() for l in g.get("lines", []) if l.strip()][:3]
    f_line = font(FONT_BODY, 36, "Regular")
    lines_h = sum(len(wrap(d, l, f_line, max_w - 64)) * 48 + 26 for l in lines) + (40 if lines else 0)
    top, bottom = PAD + 150, py - 60
    f_head, h_lines, hlh = fit_headline(d, g["headline"].strip(), max_w, bottom - top - lines_h - (48 if eyebrow else 0))
    total = (48 if eyebrow else 0) + hlh * len(h_lines) + lines_h
    y = top + max(0, (bottom - top - total) // 2)
    if eyebrow:
        d.text((PAD, y), eyebrow, font=font(FONT_BODY, 28, "SemiBold"), fill=(0, 140, 170))
        y += 48
    for hl in h_lines:
        d.text((PAD, y), hl, font=f_head, fill=NAVY_900)
        y += hlh
    if lines:
        y += 40
        for l in lines:
            tick(d, PAD, y + 22, CYAN, (0, 140, 170), (0, 180, 216, 30))
            for bl in wrap(d, l, f_line, max_w - 64):
                d.text((PAD + 64, y), bl, font=f_line, fill=SLATE)
                y += 48
            y += 26
    return save(img, out_path)


def render_question(g, out_path):
    img = Image.new("RGB", (W, H), CYAN)
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(H):  # cyan -> deeper teal
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(CYAN[i] * (1 - t) + (0, 120, 160)[i] * t) for i in range(3)))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((W + 40, H - 40), "?", font=font(FONT_HEAD, 760, "ExtraBold"), fill=(255, 255, 255, 34), anchor="rd")
    img.paste(layer, (0, 0), layer)
    d = ImageDraw.Draw(img, "RGBA")
    paste_logo(img, "mono")
    py = cta_pill(d, g, NAVY_900, (255, 255, 255))
    max_w = W - 2 * PAD
    answer = (g.get("answer") or "").strip()
    f_ans = font(FONT_BODY, 38, "SemiBold")
    a_lines = wrap(d, answer, f_ans, max_w) if answer else []
    ans_h = (len(a_lines) * 52 + 50) if a_lines else 0
    eyebrow = (g.get("eyebrow") or "").strip().upper()
    top, bottom = PAD + 150, py - 60
    f_head, h_lines, hlh = fit_headline(d, g["headline"].strip(), max_w, bottom - top - ans_h - (48 if eyebrow else 0), sizes=range(104, 47, -4))
    total = (48 if eyebrow else 0) + hlh * len(h_lines) + ans_h
    y = top + max(0, (bottom - top - total) // 2)
    if eyebrow:
        d.text((PAD, y), eyebrow, font=font(FONT_BODY, 28, "SemiBold"), fill=NAVY_900)
        y += 48
    for hl in h_lines:
        d.text((PAD, y), hl, font=f_head, fill=NAVY_950)
        y += hlh
    if a_lines:
        y += 50
        d.rectangle([PAD, y + 6, PAD + 6, y + len(a_lines) * 52 - 10], fill=(255, 255, 255))
        for al in a_lines:
            d.text((PAD + 28, y), al, font=f_ans, fill=(255, 255, 255))
            y += 52
    return save(img, out_path)


def render_compare(g, out_path):
    img = background()
    d = ImageDraw.Draw(img, "RGBA")
    paste_logo(img, False)
    py = cta_pill(d, g, CYAN, NAVY_950)
    max_w = W - 2 * PAD
    f_head, h_lines, hlh = fit_headline(d, g["headline"].strip(), max_w, 200, sizes=range(76, 39, -4))
    y = PAD + 150
    for hl in h_lines:
        d.text((PAD, y), hl, font=f_head, fill=(255, 255, 255))
        y += hlh
    y += 40
    gap = 28
    cw = (max_w - gap) // 2
    ch = py - 50 - y
    f_lab = font(FONT_BODY, 26, "SemiBold")
    f_item = font(FONT_BODY, 30, "Regular")
    panels = [
        ("THE USUAL WAY", g.get("before", [])[:3], (255, 255, 255, 14), CORAL, MUTED_ON_DARK, "x"),
        ("WITH FORESITE", g.get("after", [])[:3], (0, 180, 216, 40), CYAN_2, ON_DARK, "tick"),
    ]
    for i, (label, items, fill, accent, txt, mark) in enumerate(panels):
        x0 = PAD + i * (cw + gap)
        d.rounded_rectangle([x0, y, x0 + cw, y + ch], radius=28, fill=fill, outline=accent if i else None, width=2)
        d.text((x0 + 32, y + 32), label, font=f_lab, fill=accent)
        iy = y + 92
        for it in items:
            cy = iy + 20
            if mark == "x":
                d.ellipse([x0 + 32, cy - 16, x0 + 64, cy + 16], outline=accent, width=2)
                d.line([(x0 + 41, cy - 7), (x0 + 55, cy + 7)], fill=accent, width=3)
                d.line([(x0 + 55, cy - 7), (x0 + 41, cy + 7)], fill=accent, width=3)
            else:
                d.ellipse([x0 + 32, cy - 16, x0 + 64, cy + 16], outline=accent, width=2)
                d.line([(x0 + 40, cy), (x0 + 46, cy + 6), (x0 + 56, cy - 7)], fill=accent, width=3)
            for bl in wrap(d, it.strip(), f_item, cw - 120):
                d.text((x0 + 84, iy), bl, font=f_item, fill=txt)
                iy += 40
            iy += 30
    return save(img, out_path)


STATUS_COLOURS = {"done": MINT, "complete": MINT, "approved": MINT, "in date": MINT, "booked": CYAN, "scheduled": CYAN,
                  "chased": AMBER, "due": AMBER, "awaiting": AMBER, "overdue": CORAL, "missing": CORAL}


def render_portal(g, out_path):
    img = background()
    d = ImageDraw.Draw(img, "RGBA")
    paste_logo(img, False)
    py = cta_pill(d, g, CYAN, NAVY_950)
    max_w = W - 2 * PAD
    eyebrow = (g.get("eyebrow") or "").strip().upper()
    y = PAD + 150
    if eyebrow:
        d.rectangle([PAD, y + 6, PAD + 44, y + 12], fill=CYAN_2)
        d.text((PAD + 60, y), eyebrow, font=font(FONT_BODY, 28, "SemiBold"), fill=CYAN_2)
        y += 48
    f_head, h_lines, hlh = fit_headline(d, g["headline"].strip(), max_w, 190, sizes=range(76, 39, -4))
    for hl in h_lines:
        d.text((PAD, y), hl, font=f_head, fill=(255, 255, 255))
        y += hlh
    y += 36
    rows = g.get("rows", [])[:4]
    ph = py - 46 - y
    d.rounded_rectangle([PAD, y, W - PAD, y + ph], radius=26, fill=(255, 255, 255))
    # window bar
    for i, c in enumerate([CORAL, AMBER, MINT]):
        d.ellipse([PAD + 28 + i * 30, y + 24, PAD + 46 + i * 30, y + 42], fill=c)
    d.line([(PAD, y + 66), (W - PAD, y + 66)], fill=(226, 232, 240), width=2)
    f_row = font(FONT_BODY, 30, "SemiBold")
    f_pill = font(FONT_BODY, 24, "SemiBold")
    rh = (ph - 66) // max(1, len(rows))
    ry = y + 66
    for i, r in enumerate(rows):
        cy = ry + rh // 2
        label = r.get("label", "").strip()
        status = r.get("status", "").strip()
        lab = label
        while d.textlength(lab, font=f_row) > max_w - 290 and len(lab) > 4:
            lab = lab[:-2]
        if lab != label:
            lab = lab.rstrip() + "…"
        d.text((PAD + 36, cy), lab, font=f_row, fill=NAVY_900, anchor="lm")
        col = STATUS_COLOURS.get(status.lower(), CYAN)
        tw = d.textlength(status, font=f_pill)
        x1 = W - PAD - 36
        d.rounded_rectangle([x1 - tw - 40, cy - 24, x1, cy + 24], radius=24, fill=(*col, 38))
        d.text((x1 - tw / 2 - 20, cy), status, font=f_pill, fill=col, anchor="mm")
        if i < len(rows) - 1:
            d.line([(PAD + 36, ry + rh), (W - PAD - 36, ry + rh)], fill=(237, 241, 246), width=2)
        ry += rh
    return save(img, out_path)


def render_numbered(g, out_path):
    img = Image.new("RGB", (W, H), LIGHT_BG)
    d = ImageDraw.Draw(img, "RGBA")
    paste_logo(img, True)
    py = cta_pill(d, g, CYAN, NAVY_950)
    max_w = W - 2 * PAD
    eyebrow = (g.get("eyebrow") or "").strip().upper()
    y = PAD + 150
    if eyebrow:
        d.text((PAD, y), eyebrow, font=font(FONT_BODY, 28, "SemiBold"), fill=(0, 140, 170))
        y += 48
    f_head, h_lines, hlh = fit_headline(d, g["headline"].strip(), max_w, 200, sizes=range(80, 39, -4))
    for hl in h_lines:
        d.text((PAD, y), hl, font=f_head, fill=NAVY_900)
        y += hlh
    y += 44
    steps = [l.strip() for l in g.get("lines", []) if l.strip()][:3]
    avail = py - 50 - y
    sh = (avail - 20 * (len(steps) - 1)) // max(1, len(steps))
    f_num = font(FONT_HEAD, 54, "ExtraBold")
    f_step = font(FONT_BODY, 34, "SemiBold")
    for i, s in enumerate(steps):
        d.rounded_rectangle([PAD, y, W - PAD, y + sh], radius=22, fill=(255, 255, 255), outline=(226, 232, 240), width=2)
        d.text((PAD + 36, y + sh / 2), f"{i + 1:02d}", font=f_num, fill=CYAN, anchor="lm")
        sl = wrap(d, s, f_step, max_w - 200)
        ty = y + sh / 2 - len(sl) * 22
        for bl in sl:
            d.text((PAD + 150, ty), bl, font=f_step, fill=NAVY_900)
            ty += 44
        y += sh + 20
    return save(img, out_path)


def save(img, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


LAYOUTS = {"light": render_light, "question": render_question, "compare": render_compare,
           "portal": render_portal, "numbered": render_numbered}



def main():
    spec = json.load(open(sys.argv[1]))
    week = spec["week"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", week), "week must be YYYY-MM-DD"
    check = "--check" in sys.argv
    base = "/tmp/foresite-preview" if check else os.path.join(ROOT, "weekly", week)
    for g in spec["graphics"]:
        slug = re.sub(r"[^a-z0-9-]+", "-", g["slug"].lower()).strip("-")
        p = LAYOUTS.get(g.get("layout", "classic"), render)(g, os.path.join(base, slug + ".png"))
        print(os.path.relpath(p, ROOT) if not check else p)


if __name__ == "__main__":
    main()
