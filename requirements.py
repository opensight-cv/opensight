import json
from argparse import ArgumentParser
from subprocess import check_call
from sys import executable

parser = ArgumentParser(
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
    "-r",
    "--requirements",
    dest="requirements",
    default="requirements.txt",
    action="store_true",
    help="filename for requirements.txt",
)
parser.add_argument(
    "-f",
    "--filename",
    dest="filename",
    default="requirements_extra.json",
    action="store_true",
    help="filename for requirements extra",
)
parser.add_argument(
    "-n",
    "--no-requirements",
    dest="exclude_requirements",
    action="store_true",
    help="exclude requirements.txt",
)
parser.add_argument(
    "--exclude", dest="exclude", action="append", nargs="+", help="exclude overlays",
)
parser.add_argument(
    "overlays", action="append", nargs="+", help="overlays to install",
)

args = parser.parse_args()
exclude = args.exclude[0] if args.exclude else []


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
    f = data["features"][feature]
    return f["packages"], f["description"]


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


def process_requirements(data):
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
    return packages, descriptions


def print_descriptions(descriptions):
    for description, values in sorted(descriptions.items()):
        print(f"{description}:")
        for line in values:
            print(f"    {line}")


def install_requirements(packages):
    prompt = prompt_user("Install packages?", autoconfirm=args.autoconfirm)
    if not prompt:
        raise SystemExit
    check_call([executable, "-m", "pip", "install", *packages])


with open(args.filename) as f:
    data = json.load(f)


packages, descriptions = process_requirements(data)

if not args.exclude_requirements:
    with open(args.requirements) as f:
        requirements = f.read().split("\n")
        requirements = [item for item in requirements if "#" not in item and item]
        packages.update(requirements)

if args.list:
    print("\n".join(sorted(packages)))
    raise SystemExit

print_descriptions(descriptions)
install_requirements(packages)
