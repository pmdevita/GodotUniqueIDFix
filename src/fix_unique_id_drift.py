#!/bin/env python3

import argparse
import difflib
import re
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Restore old unique_ids that are changed due to Godot #117605"
)
parser.add_argument("file", nargs="*")

BASE = Path()

NODE_LINE = re.compile(r"^\[node .*?]$")
GET_UNIQUE_ID = re.compile(r"unique_id=(\d+)")


def main():
    args = parser.parse_args()

    for file_path in args.file:
        if process_file(BASE / file_path):
            print(f"Modified {file_path}")
        else:
            print(f"........ {file_path}")


def process_file(file_path: Path) -> bool:
    if file_path.suffix == ".tscn":
        return process_tscn(file_path)
    return False


def get_original_file(file_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{file_path}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        if "exists on disk, but not in 'HEAD'" in e.stderr:
            return None
        raise
    return result.stdout


def process_tscn(file_path: Path) -> bool:
    a = get_original_file(file_path)
    if a is None:
        return False

    with open(file_path) as f:
        b = f.read()
    diff = difflib.ndiff(a.split("\n"), b.split("\n"))

    CODES = ["- ", "? ", "+ ", "? "]
    sequence = []
    replacements: list[tuple[str, str]] = []

    for change in diff:
        if change.startswith("  "):
            continue

        if change.startswith(CODES[len(sequence)]):
            sequence.append(change)
        else:
            sequence = []

        if len(sequence) == len(CODES):
            replacement = process_sequence(sequence)
            if replacement:
                replacements.append(replacement)
            sequence = []

    if not replacements:
        return False

    for replacement in replacements:
        b = b.replace(replacement[1], replacement[0])

    with open(file_path, "w") as f:
        f.write(b)
    return True


def process_sequence(sequence: list[str]) -> tuple[str, str] | None:
    before = sequence[0][2:]
    after = sequence[2][2:]
    # Is this a node line?

    if (not NODE_LINE.match(before)) or (not NODE_LINE.match(after)):
        return None

    before_id = GET_UNIQUE_ID.findall(before)[0]
    after_id = GET_UNIQUE_ID.findall(after)[0]

    return f"unique_id={before_id}", f"unique_id={after_id}"


if __name__ == "__main__":
    main()
