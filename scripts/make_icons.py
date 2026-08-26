"""Generate ALICE's PWA icons (no design tools needed).

Draws the Alice hexagon + glowing core onto a deep-space background at a
high resolution, then downsamples for crisp pixels. Run once:

    python scripts/make_icons.py

Writes frontend/icons/icon-192.png, icon-512.png and maskable-512.png.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "icons"

BG = (4, 12, 29)
PANEL = (10, 26, 48)
CYAN = (79, 217, 255)
ICE = (169, 237, 255)
TEAL = (56, 230, 196)


def hexagon(cx, cy, r):
    import math

    return [
        (
            cx + r * math.cos(math.radians(60 * i - 90)),
            cy + r * math.sin(math.radians(60 * i - 90)),
        )
        for i in range(6)
    ]


def draw_icon(size, maskable=False):
    # supersample 4x for antialiasing
    scale = 4
    S = size * scale
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # radial background
    bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    radial = Image.new("L", (S, S), 0)
    dr = ImageDraw.Draw(radial)
    for i in range(S, 0, -8):
        dr.ellipse((S / 2 - i / 2, S / 2 - i / 2, S / 2 + i / 2, S / 2 + i / 2), fill=255 - int(255 * (i / S) ** 1.4))
    radial = radial.filter(ImageFilter.GaussianBlur(S * 0.04))
    col = Image.new("RGBA", (S, S), BG + (255,))
    bg.paste(col, (0, 0), radial)
    img = Image.alpha_composite(img, bg)

    # subtle grid
    grid = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dg = ImageDraw.Draw(grid)
    step = S / 12
    for i in range(13):
        p = i * step
        dg.line((p, 0, p, S), fill=(CYAN + (14,)), width=1)
        dg.line((0, p, S, p), fill=(CYAN + (14,)), width=1)
    grid = grid.filter(ImageFilter.GaussianBlur(1))
    img = Image.alpha_composite(img, grid)

    d = ImageDraw.Draw(img)

    cx, cy = S / 2, S / 2
    outer_r = S * (0.36 if maskable else 0.42)
    inner_r = outer_r * 0.66

    # outer hexagon glow
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.polygon(hexagon(cx, cy, outer_r), outline=CYAN + (255,), width=int(S * 0.035))
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.02))
    img = Image.alpha_composite(img, glow)

    d = ImageDraw.Draw(img)
    d.polygon(hexagon(cx, cy, outer_r), outline=CYAN + (255,), width=int(S * 0.028))
    d.polygon(hexagon(cx, cy, inner_r), outline=TEAL + (210,), width=int(S * 0.02))

    # core
    core_r = S * 0.075
    d.ellipse(
        (cx - core_r, cy - core_r, cx + core_r, cy + core_r),
        fill=ICE + (255,),
    )
    # core glow
    core_glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dgc = ImageDraw.Draw(core_glow)
    dgc.ellipse(
        (cx - core_r * 3, cy - core_r * 3, cx + core_r * 3, cy + core_r * 3),
        fill=CYAN + (90,),
    )
    core_glow = core_glow.filter(ImageFilter.GaussianBlur(S * 0.03))
    img = Image.alpha_composite(img, core_glow)
    d = ImageDraw.Draw(img)
    d.ellipse(
        (cx - core_r, cy - core_r, cx + core_r, cy + core_r),
        fill=ICE + (255,),
    )

    # white background needed? iOS likes no transparency for apple touch; we keep png.
    out = img.resize((size, size), Image.LANCZOS)
    return out.convert("RGBA")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    icon_512 = draw_icon(512, maskable=False)
    icon_192 = icon_512.resize((192, 192), Image.LANCZOS)
    maskable = draw_icon(512, maskable=True)

    icon_512.save(OUT_DIR / "icon-512.png")
    icon_192.save(OUT_DIR / "icon-192.png")
    maskable.save(OUT_DIR / "maskable-512.png")

    print(f"Wrote icons to {OUT_DIR}")


if __name__ == "__main__":
    main()
