#!/usr/bin/env python3
"""Invariants of the Grafana Git Sync tree that a linter cannot express.

    python3 scripts/check-dashboards.py

Grafana syncs every file under Dashboards/ as a resource. A hand edit that
breaks one of these rules fails to sync, or collides with another resource
without an error:

1. Dashboards/ holds at least one dashboard, so a pass means files were read.
2. Every tracked file under Dashboards/ is a README.md or a .json file.
3. Each .json file is UTF-8 JSON whose top level is an object.
4. Each is a Dashboard (apiVersion dashboard.grafana.app/<version>) or a
   Folder (folder.grafana.app/<version>), and a file is a Folder exactly
   when it is named _folder.json.
5. metadata.name is a non-empty string, unique among resources of its kind;
   Grafana uses it as the resource's UID.
6. spec.title is a non-empty string.
7. Every directory under Dashboards/ holds a _folder.json, as Grafana writes
   one for every folder it creates.

JSON formatting is not checked: Grafana writes its own. Standard library
only; needs git and Python 3.9 or later.
"""

import json
import os
import re
import subprocess
import sys

ROOT = "Dashboards"
FOLDER_FILE = "_folder.json"
VERSION = r"v[0-9]+(?:(?:alpha|beta)[0-9]+)?"
KINDS = {
    "Dashboard": re.compile(r"dashboard\.grafana\.app/" + VERSION + r"\Z"),
    "Folder": re.compile(r"folder\.grafana\.app/" + VERSION + r"\Z"),
}


def tracked_files():
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    os.chdir(top)
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", ROOT],
        check=True, capture_output=True, text=True,
    ).stdout
    return sorted(p for p in out.split("\0") if p)


def nonempty_string(value):
    return isinstance(value, str) and value.strip() != ""


def main():
    failures = []

    def fail(message):
        failures.append(message)
        print("FAIL  " + message, file=sys.stderr)

    names = {kind: {} for kind in KINDS}
    directories = set()
    folder_dirs = set()

    for path in tracked_files():
        directory = os.path.dirname(path)
        if directory != ROOT:
            directories.add(directory)
        base = os.path.basename(path)

        # 2. The file types Grafana is given.
        if base == "README.md":
            continue
        if not base.endswith(".json"):
            fail(path + ": not a .json file or README.md")
            continue

        # 3. Parses as a JSON object.
        try:
            with open(path, encoding="utf-8") as handle:
                resource = json.load(handle)
        except (OSError, UnicodeDecodeError, ValueError) as error:
            fail(path + ": unreadable JSON: " + str(error))
            continue
        if not isinstance(resource, dict):
            fail(path + ": top level is not a JSON object")
            continue

        # 4. A known kind and API version, and Folders only in _folder.json.
        kind = resource.get("kind")
        api_version = resource.get("apiVersion")
        if kind not in KINDS:
            fail(path + ": kind " + repr(kind) + " is not Dashboard or Folder")
            continue
        if not isinstance(api_version, str) or not KINDS[kind].match(api_version):
            fail(path + ": apiVersion " + repr(api_version) + " does not match kind " + kind)
        if (kind == "Folder") != (base == FOLDER_FILE):
            fail(path + ": a " + kind + " must " + ("" if kind == "Folder" else "not ")
                 + "be named " + FOLDER_FILE)
        if kind == "Folder" and base == FOLDER_FILE:
            folder_dirs.add(directory)

        # 5. A unique, non-empty name.
        metadata = resource.get("metadata")
        name = metadata.get("name") if isinstance(metadata, dict) else None
        if not nonempty_string(name):
            fail(path + ": metadata.name is missing or empty")
        elif name in names[kind]:
            fail(path + ": metadata.name " + repr(name) + " is also used by "
                 + names[kind][name])
        else:
            names[kind][name] = path

        # 6. A title.
        spec = resource.get("spec")
        title = spec.get("title") if isinstance(spec, dict) else None
        if not nonempty_string(title):
            fail(path + ": spec.title is missing or empty")

    # 7. Folder metadata for every directory.
    for directory in sorted(directories - folder_dirs):
        fail(directory + "/: no " + FOLDER_FILE)

    # 1. Something was read.
    dashboards = len(names["Dashboard"])
    if dashboards == 0:
        fail(ROOT + "/ holds no dashboard")

    if failures:
        print("check-dashboards: %d failure(s)" % len(failures), file=sys.stderr)
        return 1
    print("check-dashboards: PASS, %d dashboards and %d folders"
          % (dashboards, len(names["Folder"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
