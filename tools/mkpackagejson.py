#!/bin/env python

import argparse
import json
from pathlib import Path


def repo_url(remote):
    """The owner/repo of a GitHub remote, given over SSH, over HTTPS or as owner/repo."""
    repo = remote.removeprefix("git@github.com:").removeprefix("https://github.com/")
    repo = repo.removesuffix(".git")
    if len(repo.split("/")) != 2:
        raise argparse.ArgumentTypeError(f"\"{remote}\" is not a valid GitHub URL")
    return repo

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--repo", type=repo_url)
parser.add_argument("-v", "--ver")
# Each package installs under its own folder name, from where it sits in the repository
parser.add_argument("packages", type=Path, nargs="+")

args = parser.parse_args()

try:
    data = json.load(open("package.json", "r"))
    print("package.json found: updating!")
except FileNotFoundError:
    data = {}
    print("package.json not found: creating!")

data.update({
    "version": args.ver,
    "urls": [],
})

for package in args.packages:
    for path in sorted(package.rglob("*.py")):
        installed = path.relative_to(package.parent).as_posix()
        url = f"github:{args.repo}/{path.as_posix()}"
        print(f"Adding {installed} as {url}")
        data["urls"].append([installed, url])

open("package.json","w").write(json.dumps(data, indent=True))
