#!/usr/bin/python3

# i tried ok

import subprocess, sys
import random
import pywal, wpgtk

from PIL import Image
from string import Template
from pathlib import Path

CONFIG_TEMPLATE_PATH = Path("~/.dotfiles/config").expanduser()
CONFIG_PATH = Path("~/.config").expanduser()
PYWAL_BACKEND = "colorthief"
WALLPAPER_FOLDER = Path(sys.argv[1]).absolute().expanduser() if len(sys.argv) > 1 else Path("~/Pictures/wallpapers/").expanduser()

class Configs:
    def __init__(self, mappings: dict) -> None:
        self.mappings = mappings

    def write(self, template_path: Path, config_path: Path):
        # create a dir with the contents of config dir if not exist
        if not template_path.exists():
            template_path.mkdir()

            for conf in config_path.iterdir():
                if not conf.is_file():
                    continue
                with open(conf) as f:
                    stream = f.read()
                with open(template_path.joinpath(conf.name), "w") as f:
                    f.write(stream)
            return

        for conf in template_path.iterdir():
            if not conf.is_file() and conf.is_dir():
                config_path.joinpath(conf.name).mkdir(exist_ok=True)
                self.write(template_path.joinpath(conf.name), config_path.joinpath(conf.name))
                continue

            with open(conf, "r") as f:
                try:
                    # use the built-in template module to replace strings
                    stream = Template(f.read()).substitute(self.mappings)
                except KeyError as e:
                    print(f"Invalid key {e.args[0]} in {conf}. Skipping...")
                    continue

            with open(config_path.joinpath(conf.name), "w") as f:
                print(f"Writing to path {config_path.joinpath(conf.name)}")
                f.write(stream)


    def reload(self):
        for template in CONFIG_TEMPLATE_PATH.iterdir():
            config = Path(CONFIG_PATH).joinpath(template.name)

            self.write(template, config)
            getattr(self, template.name.lower(), lambda: None)()

    def swaylock(self):
        subprocess.Popen("echo $(killall swayidle) && swayidle", shell=True)

    def hypr(self):
        if subprocess.check_output("echo $(pidof obs)", shell=True).strip(): # hyprland crashes if configs get updated while obs is running
            return
        subprocess.Popen("hyprctl reload", shell=True)

    def waybar(self):
        subprocess.Popen("echo $(killall waybar) && waybar", shell=True)

    def dunst(self):
        subprocess.Popen("echo $(killall dunst) && dunst", shell=True)

    def kvantum(self):
        subprocess.Popen("kvantummanager --set Layan-pywal", shell=True)

        # weird hack to theme gtk and also to ignore it theming terminals
        wpgtk.data.config.settings.setdefault("backend", "colortheif")
        wpgtk.data.themer.pywal.sequences.send = lambda *args, **kwargs: None
        wpgtk.data.themer.set_pywal_theme(str(Path("~/.cache/wal/colors").expanduser()), False)

    def wlogout(self):
        colors = tuple(int((self.mappings["accent"] + "FF")[i : i + 2], 16) for i in (0, 2, 4, 6))
        path = CONFIG_PATH.joinpath("wlogout/icons")
        path.mkdir(exist_ok=True)

        for file in Path("/usr/share/wlogout/icons").iterdir():
            img = Image.open(file).convert("RGBA")
            img.putdata([colors if pixel[3] != 0 else pixel for pixel in img.getdata()])
            img.save(path.joinpath(f"pywal-{file.name}"))

    def rofi(self):
        # a 512x512 image centered on the wallpaper
        img = Image.open(self.mappings["wallpaper"])
        box = (
            *((ax - 512) // 2 for ax in img.size),
            *((ax + 512) // 2 for ax in img.size))
        img.crop(box).save(CONFIG_PATH.joinpath("rofi/image.png"))


# https://stackoverflow.com/questions/6027558/flatten-nested-dictionaries-compressing-keys
def flatten_dict(dictionary: dict, parent_key: str = '', separator: str = '_'):
    items = []
    for key, value in dictionary.items():
        new_key = parent_key + separator + key if parent_key else key
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, separator=separator).items())
        else:
            items.append((new_key, value))
    return dict(items)

def random_wallpaper(path: Path):
    file_types = (".gif", ".jpeg", ".png", ".tga", ".tiff", ".webp", ".bmp", ".jpg")
    if path.is_file():
        return path  # a file was specified
    try:
        current_wallpaper = str(subprocess.check_output(["swww", "query"])).split('"')[-2]
    except IndexError:
        current_wallpaper = None  # if no wallpaper is set

    wallpapers = list(filter(lambda wallpaper: wallpaper.name.endswith(file_types) and wallpaper.name != current_wallpaper, path.iterdir()))
    return random.choice(wallpapers)

if __name__ == "__main__":
    wallpaper = random_wallpaper(WALLPAPER_FOLDER)
    subprocess.Popen(["swww", "img", wallpaper,
            "--transition-type=grow",
            "--transition-fps=120",
            "--transition-pos=top-right"])

    image = pywal.image.get(wallpaper)
    colors = pywal.colors.get(image, backend=PYWAL_BACKEND)
    pywal.export.every(colors)

    Configs({
        # load all colors from pywal (and remove the # symbol before each color)
        **{k: v[1:] for k, v in flatten_dict(colors).items()},

        # dirs
        "HOME": str(Path("~").expanduser()),
        "wallpaper": wallpaper,

        # colors
        "primary": colors["colors"]["color3"][1:],
        "secondary": colors["colors"]["color2"][1:],
        "accent": colors["colors"]["color5"][1:],
        "bad": "cc4f4f",
        "good": "26a65b",
        "text": "d2d2d2",

        # waybar
        "waybar_bluetooth": "0a3b8c",
    }).reload()