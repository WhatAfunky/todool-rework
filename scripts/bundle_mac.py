#!/usr/bin/env python3
"""Package target/todool into a self-contained target/Todool.app (macOS).

Usage: python3 scripts/bundle_mac.py [path/to/todool-binary]

Copies the Homebrew dylibs the binary needs (recursively) into
Contents/Frameworks, rewrites their install names to @rpath, builds the
icon from src/assets/logo.png and ad-hoc signs the result.
"""
import os
import plistlib
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARY = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "target", "todool")
APP = os.path.join(os.path.dirname(BINARY), "Todool.app")
BUNDLE_ID = "de.todool.app"
EXTRA_LIB_DIRS = ["/opt/homebrew/lib"]

# sdl2-compat loads SDL3 with dlopen, so otool cannot see it. It tries
# @loader_path/libSDL3.dylib first, so ship it next to libSDL2.
DLOPENED = {"libSDL2-2.0.0.dylib": ["/opt/homebrew/opt/sdl3/lib/libSDL3.dylib"]}


def run(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def is_system(dep):
    return dep.startswith(("/usr/lib/", "/System/"))


def rpaths(path):
    out = run("otool", "-l", path)
    return re.findall(r"cmd LC_RPATH\n\s+cmdsize \d+\n\s+path (.+) \(offset", out)


def resolve(dep, owner):
    """Absolute, real path of dependency `dep` as seen from the file `owner`."""
    here = os.path.dirname(owner)
    if dep.startswith("@loader_path/"):
        cands = [os.path.join(here, dep[len("@loader_path/"):])]
    elif dep.startswith("@rpath/"):
        name = dep[len("@rpath/"):]
        dirs = [r.replace("@loader_path", here) for r in rpaths(owner)] + EXTRA_LIB_DIRS
        cands = [os.path.join(d, name) for d in dirs]
    else:
        cands = [dep]
    for c in cands:
        if os.path.exists(c):
            return os.path.realpath(c)
    sys.exit(f"cannot resolve {dep} (needed by {owner})")


def deps(path):
    """(install name, resolved path) for each non-system dependency."""
    lines = run("otool", "-L", path).splitlines()[1:]
    result = []
    for line in lines:
        dep = line.strip().split(" (compatibility")[0]
        if is_system(dep):
            continue
        real = resolve(dep, path)
        if real == os.path.realpath(path):  # the dylib's own id
            continue
        result.append((dep, real))
    return result


def collect(binary):
    """Map real path -> bundled file name, for the whole dependency tree."""
    found = {}
    names = {}  # real path -> name it must have to be found by dlopen
    todo = [binary]
    while todo:
        cur = todo.pop()
        wanted = [real for _, real in deps(cur)]
        for extra in DLOPENED.get(os.path.basename(cur), []):
            real = os.path.realpath(extra)
            names[real] = os.path.basename(extra)  # keep the symlink's name
            wanted.append(real)
        for real in wanted:
            if real in found:
                continue
            name = names.get(real, os.path.basename(real))
            if name in found.values():
                sys.exit(f"two different libraries named {name}")
            found[real] = name
            todo.append(real)
    return found


def make_icon(resources):
    logo = os.path.join(ROOT, "src", "assets", "logo.png")
    iconset = os.path.join(os.path.dirname(APP), "Todool.iconset")
    shutil.rmtree(iconset, ignore_errors=True)
    os.makedirs(iconset)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            px = size * scale
            suffix = "" if scale == 1 else "@2x"
            run("sips", "-z", str(px), str(px), logo,
                "--out", os.path.join(iconset, f"icon_{size}x{size}{suffix}.png"))
    run("iconutil", "-c", "icns", iconset, "-o", os.path.join(resources, "Todool.icns"))
    shutil.rmtree(iconset)


def version():
    src = open(os.path.join(ROOT, "src", "main.odin")).read()
    return re.search(r'VERSION :: "(\d[^"]*)"', src).group(1)


def main():
    if not os.path.isfile(BINARY):
        sys.exit(f"{BINARY} not found; build it first")

    shutil.rmtree(APP, ignore_errors=True)
    macos = os.path.join(APP, "Contents", "MacOS")
    frameworks = os.path.join(APP, "Contents", "Frameworks")
    resources = os.path.join(APP, "Contents", "Resources")
    for d in (macos, frameworks, resources):
        os.makedirs(d)

    exe = os.path.join(macos, "todool")
    shutil.copy2(BINARY, exe)

    libs = collect(BINARY)
    for real, name in libs.items():
        dest = os.path.join(frameworks, name)
        shutil.copy2(real, dest)
        os.chmod(dest, 0o755)

    # Point every reference at the bundled copy.
    targets = [(exe, BINARY)] + [(os.path.join(frameworks, n), r) for r, n in libs.items()]
    for bundled, original in targets:
        cmd = ["install_name_tool"]
        if bundled != exe:
            cmd += ["-id", f"@rpath/{os.path.basename(bundled)}"]
        for dep, real in deps(original):
            cmd += ["-change", dep, f"@rpath/{libs[real]}"]
        if bundled == exe:
            cmd += ["-add_rpath", "@executable_path/../Frameworks"]
        if len(cmd) > 1:
            run(*cmd, bundled)

    make_icon(resources)

    plist = {
        "CFBundleName": "Todool",
        "CFBundleDisplayName": "Todool",
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleExecutable": "todool",
        "CFBundleIconFile": "Todool",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": version(),
        "CFBundleVersion": version(),
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
    }
    with open(os.path.join(APP, "Contents", "Info.plist"), "wb") as f:
        plistlib.dump(plist, f)

    # install_name_tool invalidates signatures; arm64 refuses unsigned code.
    for name in libs.values():
        run("codesign", "--force", "--sign", "-", os.path.join(frameworks, name))
    run("codesign", "--force", "--sign", "-", APP)

    size = run("du", "-sh", APP).split()[0]
    print(f"{APP}: {len(libs)} bundled libraries, {size}")


main()
