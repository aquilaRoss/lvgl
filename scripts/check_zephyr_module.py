#!/usr/bin/env python3
"""Check that the package URL in zephyr/module.yml matches the LVGL version.

Zephyr's `west spdx` copies this package URL into the SBOMs it generates, and
vulnerability scanners match on it, so a stale version silently misreports
which LVGL a Zephyr build contains.

The package URL names a release tag, so like library.json it only moves on
releases (scripts/update_version.py rewrites it). On a release the version
must equal lv_version.h; between releases it must still equal library.json,
the last release.

Usage:
    python3 scripts/check_zephyr_module.py
"""

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PURL_PREFIX = "pkg:github/lvgl/lvgl@v"


def read_text(*path_segments):
    with open(os.path.join(REPO_ROOT, *path_segments), encoding="utf-8") as fh:
        return fh.read()


def read_header_version():
    """Return (version, info) from lv_version.h, e.g. ('9.6.0', 'dev')."""
    text = read_text("include", "lvgl", "lv_version.h")

    def grab(macro):
        m = re.search(r"#define\s+%s\s+\"?([^\"\n]*)\"?" % macro, text)
        return m.group(1).strip() if m else None

    version = "%s.%s.%s" % (grab("LVGL_VERSION_MAJOR"),
                            grab("LVGL_VERSION_MINOR"),
                            grab("LVGL_VERSION_PATCH"))
    return version, grab("LVGL_VERSION_INFO") or ""


def read_purl_versions():
    """Return every version named by an LVGL package URL in module.yml."""
    text = read_text("zephyr", "module.yml")
    return re.findall(r"^\s*-\s*" + re.escape(PURL_PREFIX) + r"(\S+)\s*$",
                      text, re.MULTILINE)


def main():
    purl_versions = read_purl_versions()
    if len(purl_versions) != 1:
        print("zephyr/module.yml must list exactly one '%s<version>' entry, found %d"
              % (PURL_PREFIX, len(purl_versions)))
        return 1
    purl_version = purl_versions[0]

    header_version, header_info = read_header_version()
    library_version = json.loads(read_text("library.json"))["version"]

    if header_info:
        expected, source = library_version, "library.json (last release)"
    else:
        expected, source = header_version, "include/lvgl/lv_version.h"

    if purl_version != expected:
        print("zephyr/module.yml names LVGL %s but %s is %s; "
              "run scripts/update_version.py" % (purl_version, source, expected))
        return 1

    print("zephyr/module.yml matches %s (%s)" % (source, expected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
