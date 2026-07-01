"""Make a logo's solid background transparent by flood-filling from the corners.

Removes only the background region *connected to the image border* (the corner
colour), so colour that's enclosed by the logo — e.g. white text inside a badge —
is preserved. Works for any background colour (it samples the corners), not just white.

    # preview first (writes a composite over magenta, doesn't touch the original)
    python make_logo_transparent.py tritonbots.png --preview /tmp/prev

    # apply in place
    python make_logo_transparent.py tritonbots.png

    # several at once
    python make_logo_transparent.py kiks.png luhbots.png er-force.png

Tune --tol up if a pale halo remains, down if it eats into the logo. Intended for
the solid-background logos; skip ones that are already transparent.
"""

import argparse
import os

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

LOGOS = os.path.join(os.path.dirname(__file__), "logos")


def make_transparent(im: Image.Image, tol: float = 50.0, feather: float = 0.6) -> Image.Image:
    im = im.convert("RGBA")
    rgb = np.asarray(im)[:, :, :3].astype(np.int16)
    # background colour = mean of the four corners
    bg = np.stack([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]]).mean(0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(2))
    near_bg = dist <= tol
    # keep only background pixels connected to the border (flood from edges)
    labels, _ = ndimage.label(near_bg)
    border = np.unique(np.concatenate([
        labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]))
    border = border[border != 0]
    remove = np.isin(labels, border)
    alpha = np.where(remove, 0, 255).astype(np.uint8)
    a = Image.fromarray(alpha)  # 2-D uint8 -> mode "L"
    if feather:
        a = a.filter(ImageFilter.GaussianBlur(feather))  # soften jaggies
    im.putalpha(a)
    return im


def main() -> None:
    ap = argparse.ArgumentParser(description="Flood-fill a logo's background to transparent.")
    ap.add_argument("files", nargs="+", help="logo filenames inside logos/")
    ap.add_argument("--tol", type=float, default=50.0, help="background colour tolerance")
    ap.add_argument("--feather", type=float, default=0.6, help="edge softening (px)")
    ap.add_argument("--preview", metavar="DIR",
                    help="write a composite over magenta here instead of overwriting")
    args = ap.parse_args()

    for name in args.files:
        path = os.path.join(LOGOS, name)
        out = make_transparent(Image.open(path), tol=args.tol, feather=args.feather)
        if args.preview:
            os.makedirs(args.preview, exist_ok=True)
            bg = Image.new("RGBA", out.size, (255, 0, 128, 255))
            dst = os.path.join(args.preview, name)
            Image.alpha_composite(bg, out).convert("RGB").save(dst)
            print(f"preview: {dst}")
        else:
            out.save(path)
            print(f"updated: {path}")


if __name__ == "__main__":
    main()
