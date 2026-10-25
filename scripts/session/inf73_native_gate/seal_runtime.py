#!/usr/bin/env python3
"""Model-free closure inventory; hashes installed interpreter/stdlib/site files, imports none."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

def elf_dependencies(path):
    """Read ELF64 little-endian dynamic strings; never dlopen/execute an object."""
    body = Path(path).read_bytes()
    if body[:4] != b"\x7fELF":
        return [], []
    if body[4:6] != b"\x02\x01":
        raise ValueError("unsupported ELF encoding: " + str(path))
    offset = struct.unpack_from("<Q", body, 40)[0]
    size, count = struct.unpack_from("<HH", body, 58)
    sections = [struct.unpack_from("<IIQQQQIIQQ", body, offset + i * size) for i in range(count)]
    dependencies, search = [], []
    for section in sections:
        if section[1] != 6:  # SHT_DYNAMIC
            continue
        strings = sections[section[6]]
        table = body[strings[4]:strings[4] + strings[5]]
        for entry in range(section[4], section[4] + section[5], section[9] or 16):
            tag, value = struct.unpack_from("<qQ", body, entry)
            if tag == 0:
                break
            if tag in (1, 15, 29):
                text = table[value:].split(b"\0", 1)[0].decode()
                (dependencies if tag == 1 else search).append(text)
    return dependencies, [part for text in search for part in text.split(":")]

def elf_closure(paths):
    queue = list(paths)
    seen = set()
    libraries = {}
    while queue:
        path = Path(queue.pop()).resolve(strict=True)
        if str(path) in seen:
            continue
        seen.add(str(path))
        dependencies, rpaths = elf_dependencies(path)
        directories = [Path(part.replace("${ORIGIN}", str(path.parent)).replace("$ORIGIN", str(path.parent)))
            for part in rpaths]
        directories += [path.parent, Path("/lib/x86_64-linux-gnu"), Path("/usr/lib/x86_64-linux-gnu"), Path("/lib64")]
        for needed in dependencies:
            if "/" in needed:
                raise ValueError("non-SONAME ELF dependency requires explicit review: " + needed)
            found = next((directory / needed for directory in directories if (directory / needed).is_file()), None)
            if found is None:
                raise ValueError("unresolved ELF dependency: " + needed + " from " + str(path))
            libraries[str(found)] = {"resolved": str(found.resolve()), "sha256": hashlib.sha256(found.read_bytes()).hexdigest()}
            queue.append(found)
    loader = Path("/lib64/ld-linux-x86-64.so.2")
    libraries[str(loader)] = {"resolved": str(loader.resolve()), "sha256": hashlib.sha256(loader.read_bytes()).hexdigest()}
    return libraries

def inventory(roots):
    files = {}
    symlinks = {}
    for root in roots:
        root_path = Path(root)
        for path in ([root_path] if root_path.is_file() else sorted(root_path.rglob("*"))):
            if "__pycache__" in path.parts:
                continue
            if path.is_symlink():
                symlinks[str(path)] = {"target": str(path.resolve(strict=True))}
                if path.is_file():
                    symlinks[str(path)]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif path.is_file():
                files[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    elf_paths = [path for path in files if ".so" in Path(path).name]
    elf_paths.append("/usr/bin/python3.13")
    return {"roots": roots, "files": files, "symlinks": symlinks,
            "elf_libraries": elf_closure(elf_paths),
            "pth_policy": "no site processing; -S and explicit import_roots", "imports_performed": False}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("roots", nargs="+")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise SystemExit("refuse overwrite")
    output.write_text(json.dumps(inventory(args.roots), sort_keys=True, indent=2) + "\n")
