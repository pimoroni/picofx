import argparse
import os
import subprocess
from collections import namedtuple

Package = namedtuple("Package", ["name", "url", "ref"])


def dest_name(url):
    return os.path.basename(url.rstrip("/")).removesuffix("-micropython")


def read_packages(list_path):
    packages = []
    with open(list_path) as f:
        for number, line in enumerate(f, 1):
            fields = line.split("#", 1)[0].split()
            if not fields:
                continue
            if len(fields) != 2:
                raise ValueError(f"{list_path}:{number}: expected 'url ref', got {line.strip()!r}")
            url, ref = fields
            packages.append(Package(dest_name(url), url, ref))
    return packages


def fetch(list_path, dest_dir):
    for pkg in read_packages(list_path):
        dest = os.path.join(dest_dir, pkg.name)
        if not os.path.isdir(os.path.join(dest, ".git")):
            subprocess.run(
                ["git", "clone", "--filter=blob:none", f"https://github.com/{pkg.url}", dest],
                check=True,
            )
        subprocess.run(["git", "-C", dest, "fetch", "--tags", "--force", "origin"], check=True)
        subprocess.run(
            ["git", "-C", dest, "-c", "advice.detachedHead=false", "checkout", "--force", pkg.ref],
            check=True,
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["fetch"])
    ap.add_argument("--list", required=True)
    ap.add_argument("--dest", required=True)
    args = ap.parse_args()
    fetch(args.list, args.dest)


if __name__ == "__main__":
    main()
