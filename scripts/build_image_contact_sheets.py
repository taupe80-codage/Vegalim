"""
Vegalim — Planches-contacts des photos de recettes
==================================================

Toutes les recettes du site sont au moins végétariennes : aucune photo ne doit
montrer de viande ni de poisson. Les filtres de téléchargement ne lisent que
les métadonnées, pas l'image. Ce script assemble donc les photos en planches
numérotées, relues ensuite à l'œil, planche par planche.

Chaque vignette porte son numéro et son slug, pour pouvoir désigner sans
ambiguïté une photo à remplacer.

Usage :
    python scripts/build_image_contact_sheets.py                 # toutes
    python scripts/build_image_contact_sheets.py --cols 5 --rows 4
    python scripts/build_image_contact_sheets.py --only-new       # sans crédits = Unsplash
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "frontend" / "public" / "images" / "recipes"
SHEETS = ROOT / "outputs" / "planches_photos"

CELL_W, CELL_H = 320, 240
LABEL_H = 34
PAD = 6


def font(size: int):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def thumb(path: Path) -> Image.Image | None:
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            # recadrage centré : on garde le plat, pas les bandes vides
            ratio = max(CELL_W / im.width, CELL_H / im.height)
            im = im.resize((max(1, round(im.width * ratio)),
                            max(1, round(im.height * ratio))), Image.LANCZOS)
            left = (im.width - CELL_W) // 2
            top = (im.height - CELL_H) // 2
            return im.crop((left, top, left + CELL_W, top + CELL_H))
    except Exception as exc:
        print(f"  illisible : {path.name} ({exc})")
        return None


def used_slugs() -> set[str]:
    """Slugs réellement affichés par le site : slugify(titres.fr) des recettes."""
    import re
    import unicodedata
    data = json.loads((ROOT / "backend/data/recipes/recipes.json").read_text(encoding="utf-8"))
    recipes = data["recipes"] if isinstance(data, dict) else data
    out = set()
    for r in recipes:
        t = r.get("titles", {})
        name = t.get("fr") or t.get("en") or t.get("original") or ""
        if not name:
            continue
        s = unicodedata.normalize("NFD", name)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        s = s.lower().strip().replace(chr(92), "-")
        s = re.sub(r"[\s_/]+", "-", s)
        s = re.sub(r"[^a-z0-9-]", "", s)
        out.add(re.sub(r"-+", "-", s).strip("-"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--only-new", action="store_true",
                    help="seulement les photos créditées (Commons / Openverse)")
    ap.add_argument("--only-old", action="store_true",
                    help="seulement les photos sans crédit (anciennes, Unsplash)")
    ap.add_argument("--slugs-file",
                    help="fichier texte : un slug par ligne, pour ne relire que ceux-la")
    ap.add_argument("--all", action="store_true",
                    help="inclure les fichiers qu'aucune recette n'utilise")
    args = ap.parse_args()

    credited = set()
    credits_path = IMAGES / "_credits.json"
    if credits_path.exists():
        credited = set(json.loads(credits_path.read_text(encoding="utf-8")))

    # 263 fichiers sont des restes d'anciens titres : ils ne s'affichent nulle
    # part sur le site, inutile de les relire.
    used = used_slugs()
    files = sorted(p for p in IMAGES.glob("*.jpg") if args.all or p.stem in used)
    if args.slugs_file:
        wanted = {l.strip() for l in Path(args.slugs_file).read_text(encoding="utf-8").split()}
        files = [p for p in files if p.stem in wanted]
    if args.only_new:
        files = [p for p in files if p.stem in credited]
    elif args.only_old:
        files = [p for p in files if p.stem not in credited]
    if not files:
        sys.exit("aucune image à assembler")

    SHEETS.mkdir(parents=True, exist_ok=True)
    for old in SHEETS.glob("planche_*.jpg"):
        old.unlink()

    per_sheet = args.cols * args.rows
    f_label = font(15)
    f_num = font(17)
    index = {}

    for sheet_no, start in enumerate(range(0, len(files), per_sheet), 1):
        batch = files[start:start + per_sheet]
        W = args.cols * (CELL_W + PAD) + PAD
        H = args.rows * (CELL_H + LABEL_H + PAD) + PAD + 28
        sheet = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(sheet)
        draw.text((PAD, 6), f"Planche {sheet_no} — photos {start + 1} à "
                            f"{start + len(batch)} sur {len(files)}",
                  fill="black", font=f_num)

        for i, path in enumerate(batch):
            col, row = i % args.cols, i // args.cols
            x = PAD + col * (CELL_W + PAD)
            y = 28 + PAD + row * (CELL_H + LABEL_H + PAD)
            img = thumb(path)
            if img is None:
                draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill="#eeeeee")
            else:
                sheet.paste(img, (x, y))
            num = start + i + 1
            draw.rectangle([x, y, x + 46, y + 24], fill="black")
            draw.text((x + 6, y + 3), str(num), fill="white", font=f_num)
            name = path.stem
            if len(name) > 42:
                name = name[:41] + "…"
            draw.text((x + 2, y + CELL_H + 4), name, fill="#111111", font=f_label)
            mark = "CC" if path.stem in credited else "—"
            draw.text((x + 2, y + CELL_H + 19), f"{mark}", fill="#777777", font=f_label)
            index[str(num)] = path.stem

        out = SHEETS / f"planche_{sheet_no:02d}.jpg"
        sheet.save(out, quality=88, optimize=True)
        print(f"{out.name} — {len(batch)} photos")

    (SHEETS / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print(f"\n{len(files)} photos, {(len(files) - 1) // per_sheet + 1} planches dans {SHEETS}")


if __name__ == "__main__":
    main()
