"""Generate the application icon (app.ico) using Pillow.

Creates a simple but recognisable icon: a rounded box with an up/down arrow,
symbolising stock-in / stock-out flow. The icon is written to the project
root as ``app.ico`` (multi-resolution) and is embedded into the main window
and the .exe by app.spec.

Run once to (re)generate:
    python make_icon.py
"""

from __future__ import annotations

from PIL import Image, ImageDraw

SIZES = [16, 24, 32, 48, 64, 128, 256]


def _draw(size: int) -> Image.Image:
    """Render the icon at a single pixel size."""

    # Render at 4x then downscale for crisp small sizes.
    s = size * 4 if size <= 64 else size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Background: rounded square with the app's primary blue gradient feel.
    pad = int(s * 0.06)
    radius = int(s * 0.22)
    bg_color = (79, 109, 245, 255)  # #4f6df5
    d.rounded_rectangle(
        [pad, pad, s - pad, s - pad],
        radius=radius,
        fill=bg_color,
    )

    # A subtle inner highlight (top-left lighter band).
    d.rounded_rectangle(
        [pad, pad, s - pad, s // 2],
        radius=radius,
        fill=(99, 127, 247, 255),
    )

    # Two arrows: up (stock-in) on the left, down (stock-out) on the right,
    # drawn in white.
    white = (255, 255, 255, 255)
    cx = s // 2
    arrow_w = int(s * 0.16)
    arrow_h = int(s * 0.42)
    thickness = max(2, int(s * 0.07))

    def up_arrow(x_center: int, top: int):
        # Vertical stem.
        d.rectangle(
            [x_center - thickness // 2, top + arrow_w // 2,
             x_center + thickness // 2, top + arrow_h],
            fill=white,
        )
        # Arrowhead (triangle).
        head_top = top
        head_bottom = top + arrow_w // 2 + thickness
        d.polygon(
            [(x_center, head_top),
             (x_center - arrow_w // 2 - thickness // 2, head_bottom),
             (x_center + arrow_w // 2 + thickness // 2, head_bottom)],
            fill=white,
        )

    def down_arrow(x_center: int, top: int):
        # Vertical stem.
        d.rectangle(
            [x_center - thickness // 2, top,
             x_center + thickness // 2, top + arrow_h - arrow_w // 2],
            fill=white,
        )
        # Arrowhead (triangle) at the bottom.
        head_bottom = top + arrow_h
        head_top = head_bottom - arrow_w // 2 - thickness
        d.polygon(
            [(x_center, head_bottom),
             (x_center - arrow_w // 2 - thickness // 2, head_top),
             (x_center + arrow_w // 2 + thickness // 2, head_top)],
            fill=white,
        )

    offset = int(s * 0.17)
    top = int(s * 0.27)
    up_arrow(cx - offset, top)
    down_arrow(cx + offset, top)

    # Downscale for the target size if we rendered supersampled.
    if size <= 64:
        img = img.resize((size, size), Image.LANCZOS)
    return img


def main() -> None:
    frames = [_draw(size) for size in SIZES]
    # Save multi-resolution .ico (Windows reads all sizes).
    frames[0].save(
        "app.ico",
        format="ICO",
        sizes=[(size, size) for size in SIZES],
        append_images=frames[1:],
    )
    # Also save a 256px PNG for embedding in the Tk window (Tk's PhotoImage
    # can read PNG natively on modern builds; Pillow guarantees it).
    _draw(256).save("app.png", format="PNG")
    print("Generated app.ico and app.png")


if __name__ == "__main__":
    main()
