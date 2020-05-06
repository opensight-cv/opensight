import subprocess
import sys
import json
import argparse

parser = argparse.ArgumentParser(
    description="Install OpenSight dependencies based on required feature-sets"
)
parser.add_argument(
    "-y",
    "--yes",
    dest="autoconfirm",
    action="store_true",
    help="automatically confirm all prompts",
)
parser.add_argument(
    "-l", "--list", dest="list", action="store_true", help="only list packages",
)
parser.add_argument(
    "-f",
    "--filename",
    dest="filename",
    default="requirements_extra.json",
    action="store_true",
    help="change filename",
)
parser.add_argument(
    "--exclude", dest="exclude", action="append", nargs="+", help="exclude overlays",
)
parser.add_argument(
    "overlays", action="append", nargs="+", help="overlays to install",
)

args = parser.parse_args()
exclude = args.exclude[0] if args.exclude else []


def install(packages):
    subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])


def process_overlay(data, overlay):
    features = []
    parent = overlay.get("extends")
    if parent and parent not in exclude:
        features += process_overlay(data, data["overlays"][parent])
    if overlay.get("add"):
        features += overlay.get("add")
    if overlay.get("remove"):
        to_remove = overlay.get("remove")
        features = [item for item in features if item not in to_remove]
    return features


def process_feature(data, feature):
    feature = data["features"][feature]
    return feature["packages"], feature["description"]


def prompt_user(prompt, default=False, autoconfirm=False):
    if autoconfirm:
        return True
    if default:
        query = "[Y/n]"
    else:
        query = "[y/N]"
    out = input(f"{prompt} {query} ")
    if not out:
        return default
    out = out.lower()
    if out == "y":
        return True
    if out == "n":
        return False
    return prompt_user()


with open(args.filename) as f:
    data = json.load(f)

features = set()
for overlay in args.overlays[0]:
    overlay_features = process_overlay(data, data["overlays"][overlay])
    features.update(set(overlay_features))

descriptions = {}
packages = set()
for feature in features:
    pkgs, description = process_feature(data, feature)
    descriptions[feature] = description
    packages.update(set(pkgs))

if not args.list:
    for description, values in sorted(descriptions.items()):
        print(f"{description}:")
        for line in values:
            print(f"    {line}")
    prompt = prompt_user("Install packages?", autoconfirm=args.autoconfirm)
    if not prompt:
        raise SystemExit
    install(packages)
else:
    print("\n".join(packages))
