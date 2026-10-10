"""Export the R-01 texture banks; compose compatible mixed banks without
changing the original atlas, the weapon builder, compiled models or runtime.
"""
import argparse
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BANK = ROOT / "assets/r01/variants"
CONFIG = BANK / "variants.json"
ROLES = [
    ("structure", "Noyau structurel"),
    ("housing", "Carter amovible"),
    ("shell", "Habillage du chassis"),
    ("identity", "Identite / marquage"),
    ("grip", "Prise en main / amortissement"),
    ("contact", "Contacts / bagues / pieces dures"),
    ("heat_release", "Surface de refroidissement"),
    ("conductor", "Conduction / enroulement"),
    ("energy_a", "Reserve d'energie A"),
    ("energy_b", "Reserve d'energie B"),
    ("status", "Indicateur d'etat"),
    ("optic", "Surface optique"),
    ("warning", "Avertissement / securite"),
    ("insulation", "Isolation thermique"),
    ("ammunition", "Coque du chargeur"),
    ("breech", "Culasse / verrou mobile"),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def split_atlas(path, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as original:
        image = original.convert("RGB")
    width, height = image.size
    assert width == height and width >= 1024, (path, image.size)
    records = []
    for index, (role, label) in enumerate(ROLES):
        column, row = index % 4, index // 4
        # Match build_reference_weapon.py exactly, including its 3px inset.
        bounds = [round(column * width / 4) + 3,
                  round(row * height / 4) + 3,
                  round((column + 1) * width / 4) - 3,
                  round((row + 1) * height / 4) - 3]
        tile = image.crop(bounds).resize((256, 256), Image.Resampling.LANCZOS)
        name = f"r01_t{index:02}"
        tile.save(destination / (name + ".png"))
        tile.quantize(256).save(destination / (name + ".bmp"))
        with Image.open(destination / (name + ".bmp")) as exported:
            assert exported.mode == "P" and exported.size == (256, 256)
            assert len(exported.getcolors(maxcolors=256)) <= 256
        records.append(dict(index=index, row=row + 1, column=column + 1,
                            role=role, label=label, source_bounds=bounds,
                            png=f"tiles/{name}.png", bmp=f"tiles/{name}.bmp",
                            bmp_sha256=sha(destination / (name + ".bmp"))))
    return image.size, records


def weapon_usage():
    source = ROOT / "build_reference_weapon.py"
    if not source.exists():
        return None, {}
    spec = importlib.util.spec_from_file_location("r01_usage", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    usage = {}
    for slot in module.KEYS:
        for variant in range(4):
            name = f"r01_{slot}_{'abcd'[variant]}"
            usage[name] = sorted({int(material[5:7])
                                 for material, _ in module.part(slot, variant)})
    for key,mount in [('side',1),('top',2)]:
        usage['r01_receiver_'+key]=sorted({int(material[5:7])for material,_ in module.part('receiver',0 if mount==1 else 1,mount)})
    for key in module.chassis.CHASSIS:
        usage['r01_receiver_'+key]=sorted({int(material[5:7])for material,_ in module.chassis.part(key,module.Mesh)})
    for slot,specs in module.themes.PARTS.items():
        for spec in specs:
            usage[f"r01_{slot}_{spec['key']}"]=sorted({int(material[5:7])for material,_ in module.themes.part(slot,spec['key'],module.Mesh)})
    return sha(source), usage


def font(size):
    for candidate in ["C:/Windows/Fonts/segoeui.ttf",
                      "C:/Windows/Fonts/arial.ttf"]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def previews(themes):
    background, ink, muted = "#171b20", "#f1eee6", "#afb7bf"
    sheet = Image.new("RGB", (1536, 574*((len(themes)+2)//3)), background)
    draw = ImageDraw.Draw(sheet)
    for n, theme in enumerate(themes):
        x, y = (n % 3) * 512, (n // 3) * 574
        draw.text((x + 16, y + 9), theme["title"], fill=ink, font=font(25))
        with Image.open(BANK / theme["id"] / "texture-atlas.png") as atlas:
            sheet.paste(atlas.convert("RGB").resize((480, 480),
                        Image.Resampling.LANCZOS), (x + 16, y + 51))
        draw.text((x + 16, y + 539), theme["id"], fill=muted, font=font(17))
    sheet.save(BANK / "apercu-toutes-variantes.jpg", quality=94, subsampling=0)

    rows = [(4, "Poignee"), (6, "Refroidissement"),
            (8, "Energie"), (11, "Optique"), (14, "Chargeur")]
    labels = [t["title"] for t in themes]
    comparison = Image.new("RGB", (188+220*len(themes), 1190), background)
    draw = ImageDraw.Draw(comparison)
    draw.text((16, 16), "Meme fonction, conceptions differentes",
              fill=ink, font=font(28))
    for column, label in enumerate(labels):
        draw.text((188 + 220 * column, 68), label, fill=ink, font=font(17))
    for row, (index, label) in enumerate(rows):
        y = 110 + row * 214
        draw.text((12, y + 80), label, fill=ink, font=font(19))
        draw.text((12, y + 108), f"r01_t{index:02}", fill=muted, font=font(17))
        for column, theme in enumerate(themes):
            tile = BANK / theme["id"] / "tiles" / f"r01_t{index:02}.png"
            with Image.open(tile) as image:
                comparison.paste(image.resize((204, 204),
                                 Image.Resampling.LANCZOS),
                                 (188 + column * 220, y))
    comparison.save(BANK / "comparaison-fonctions.jpg", quality=94, subsampling=0)


def export_all():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    source_sha, usage = weapon_usage()
    records = []
    for theme in config["variants"]:
        folder = BANK / theme["id"]
        folder.mkdir(parents=True, exist_ok=True)
        atlas = folder / "texture-atlas.png"
        if not atlas.exists():
            shutil.copy2(theme["generated_source"], atlas)
        else:
            generated = Path(theme["generated_source"])
            if generated.exists():
                assert sha(atlas) == sha(generated), "Existing atlas differs; preserve it."
        (folder / "prompt.txt").write_text(theme["prompt"] + "\n", encoding="utf-8")
        size, tiles = split_atlas(atlas, folder / "tiles")
        for tile in tiles:
            tile["used_by_models"] = [
                name for name, indices in usage.items() if tile["index"] in indices]
            tile["used_in_current_builder"] = bool(tile["used_by_models"]) if usage else None
        entry = dict(id=theme["id"], title=theme["title"],
                     description=theme["description"], approach=theme["approach"],
                     atlas="texture-atlas.png", atlas_dimensions=list(size),
                     atlas_sha256=sha(atlas), generation_tool="built-in image_gen",
                     prompt="prompt.txt", output_size=[256, 256],
                     bmp_format="8-bit indexed RGB palette, 256 colors maximum",
                     tiles=tiles)
        save_json(folder / "manifest.json", entry)
        records.append(dict(id=theme["id"], title=theme["title"],
                            description=theme["description"],
                            manifest=f"{theme['id']}/manifest.json"))
        print(f"EXPORTED {theme['id']}: {size}, 16 PNG + 16 indexed BMP")
    save_json(BANK / "manifest.json",
              dict(version=1, reference="../texture-atlas.png",
                   reference_sha256=sha(BANK.parent / "texture-atlas.png"),
                   generation_tool="built-in image_gen",
                   builder="vector-fields/build_reference_weapon.py",
                   builder_sha256=source_sha, model_material_usage=usage,
                   layout="4x4 row-major, zero-based IDs, 3px crop inset",
                   themes=records, atlases=len(records),
                   tile_count=len(records) * 16,
                   integration="Texture banks exported; active MDL/runtime unchanged. "
                               "GoldSrc embeds textures in compiled MDL files: "
                               "a material-bank change requires recompile or skin import."))
    previews(config["variants"])
    print(f"PASS: {len(records)} atlases, {len(records)*16} compatible material IDs.")
    if usage:
        unused = sorted(set(range(16)) - {i for ids in usage.values() for i in ids})
        print("Available but unused by current weapon builder:", unused)


def compose(args):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    themes = {item["id"] for item in config["variants"]}
    choices = [args.theme] * 16
    for override in args.tile:
        index, theme = override.split("=", 1)
        index = int(index)
        if index not in range(16) or theme not in themes | {"original"}:
            raise ValueError(f"Invalid tile selection: {override}")
        choices[index] = theme
    destination = Path(args.output).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Choose an empty output directory to preserve existing banks.")
    destination.mkdir(parents=True, exist_ok=True)
    for index, theme in enumerate(choices):
        if theme == "original":
            with Image.open(BANK.parent / "texture-atlas.png") as source:
                w, h = source.size
                x, y = index % 4, index // 4
                tile = source.convert("RGB").crop(
                    (round(x*w/4)+3, round(y*h/4)+3,
                     round((x+1)*w/4)-3, round((y+1)*h/4)-3))
                tile = tile.resize((256, 256), Image.Resampling.LANCZOS)
            tile.save(destination / f"r01_t{index:02}.png")
            tile.quantize(256).save(destination / f"r01_t{index:02}.bmp")
        else:
            if theme not in themes:
                raise ValueError(f"Unknown theme: {theme}")
            for ext in ("png", "bmp"):
                name = f"r01_t{index:02}.{ext}"
                shutil.copy2(BANK / theme / "tiles" / name, destination / name)
    save_json(destination / "selection.json",
              {f"r01_t{i:02}": theme for i, theme in enumerate(choices)})
    print(f"COMPOSED 16 PNG + 16 BMP: {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", help="Base theme, or original.")
    parser.add_argument("--tile", action="append", default=[],
                        metavar="INDEX=THEME", help="Override one zero-based material ID.")
    parser.add_argument("--output", help="Empty destination directory for a composed bank.")
    args = parser.parse_args()
    if args.theme:
        if not args.output:
            parser.error("--theme requires --output")
        compose(args)
    else:
        if args.tile or args.output:
            parser.error("--tile and --output require --theme")
        export_all()
