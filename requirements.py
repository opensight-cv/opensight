#!/usr/bin/python3

import argparse
import json
import pathlib
import subprocess
import sys

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
    "-l",
    "--list",
    dest="list",
    action="store_true",
    help="list packages to be installed and exit",
)
parser.add_argument(
    "-r",
    "--requirements",
    dest="requirements",
    default=None,
    help="specify alternative requirements.txt",
)
parser.add_argument(
    "-f",
    "--filename",
    dest="requirements_extra",
    default=None,
    help="specify alternative requirements_extra.json",
)
parser.add_argument(
    "-n",
    "--no-requirements",
    dest="exclude_requirements",
    action="store_true",
    help="exclude requirements.txt",
)
parser.add_argument(
    "-e", "--exclude", dest="excludes", action="append", help="exclude features",
)
parser.add_argument(
    "-p",
    "--print",
    dest="print_overlays",
    action="store_true",
    help="print available overlays and exit",
)


def get_default_overlays():
    defaults = ["base"]
    if sys.platform.startswith("linux"):
        defaults.append("linux")
    return defaults


parser.add_argument(
    "overlays",
    action="append",
    nargs="*",
    help="overlays to install",
    default=get_default_overlays(),
)


def parse_args(*args, **kwargs):
    args = parser.parse_args(*args, **kwargs)

    args.excludes = args.excludes or []

    # the format is [*defaults, [*items]]
    args.overlays = args.overlays[-1]

    return args


def open_file(filename_arg, default, **kwargs):
    if filename_arg is None:
        # open file with default name, from the script's dir, not cwd
        return open(pathlib.Path(__file__).parent.absolute() / default, **kwargs)
    return open(filename_arg, **kwargs)


def prompt_user(prompt, default=False, autoconfirm=False):
    if autoconfirm:
        return True

    if default:
        query = "[Y/n]"
    else:
        query = "[y/N]"
    prompt = f"{prompt} {query} "

    while True:
        out = input(prompt).strip().lower()

        if not out:
            return default

        if out.startswith("y"):
            return True
        if out.startswith("n"):
            return False


def process_overlay(data, overlay):
    features = set()
    parent = overlay.get("extends")

    if parent:
        features.update(process_overlay(data, data["overlays"][parent]))

    if overlay.get("add"):
        features.update(overlay.get("add"))

    if overlay.get("remove"):
        features.difference_update(overlay.get("remove"))

    return features


def process_requirements(data, overlays, excludes):
    features = set()

    for overlay in overlays:
        features.update(process_overlay(data, data["overlays"][overlay]))

    features.difference_update(excludes)

    packages = set()
    descriptions = {}

    for feature in features:
        feature_data = data["features"][feature]

        packages.update(feature_data["packages"])
        descriptions[feature] = feature_data["description"]

    return packages, descriptions


def check_args_exist(data, overlays, excludes):
    for overlay in overlays:
        if overlay not in data["overlays"]:
            return f"overlay '{overlay}' to be added does not exist"

    for exclude in excludes:
        if exclude not in data["features"]:
            return f"feature '{exclude}' to be excluded does not exist"


def print_descriptions(descriptions):
    for description, values in sorted(descriptions.items()):
        print(f"    {description}:")
        for line in values:
            print(f"        {line}")


def install_requirements(packages):
    subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])


def main(*args, **kwargs):
    args = parse_args(*args, **kwargs)

    with open_file(args.requirements_extra, "requirements_extra.json") as f:
        data = json.load(f)

    if args.print_overlays:
        print("Available overlays:")
        for overlay in data["overlays"].keys():
            print("   ", overlay)
        print()
        return

    error = check_args_exist(data, args.overlays, args.excludes)
    if error:
        return error

    packages, descriptions = process_requirements(data, args.overlays, args.excludes)

    if not args.exclude_requirements:
        with open_file(args.requirements, "requirements.txt") as f:
            for line in f:
                requirement = line.split("#")[0].strip()
                if requirement:
                    packages.add(requirement)

    # sort ignoring case, like `pip freeze`
    packages = sorted(packages, key=str.casefold)

    if args.list:
        print("\n".join(packages))
        return

    print("Features to be installed:")
    print_descriptions(descriptions)
    if not args.exclude_requirements:
        print("    All minimal requirements from requirements.txt")
    print()
    print(f"Packages to be installed: {' '.join(packages)}")
    print()

    if prompt_user("Install packages?", autoconfirm=args.autoconfirm):
        install_requirements(packages)


if __name__ == "__main__":
    error = main()
    if error:
        exit(f"Error: {error}")
