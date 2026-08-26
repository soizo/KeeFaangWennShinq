#!/usr/bin/env python3
"""Generate zh-Hant-CN strictly with OpenCC s2t followed by t2gov."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DEFAULT_REPO = (
    Path.home()
    / "Local/Cloned/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards"
)
EXPECTED_REPO_COMMIT = "58fdb693db755cf060d4794514a9bc84b8e6ceeb"
EXPECTED_OPENCC_VERSION = "Version: 1.4.0"
STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"')
LOCALES = re.compile(
    r'^(?P<indent>[ \t]*)"zh-CN": \{\n'
    r"(?P<cn>.*?)"
    r"^(?P=indent)\},\n"
    r'^(?P=indent)"zh-Hant-CN": \{\n'
    r"(?P<hant>.*?)"
    r"^(?P=indent)\},\n"
    r"^(?P=indent)ja: \{",
    re.MULTILINE | re.DOTALL,
)


def run(command: list[str], *, text: str | None = None) -> str:
    return subprocess.run(
        command,
        input=text,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def verify_tools(repo: Path) -> tuple[Path, Path]:
    opencc = shutil.which("opencc")
    if not opencc:
        raise RuntimeError("opencc is not installed")
    if EXPECTED_OPENCC_VERSION not in run([opencc, "--version"]):
        raise RuntimeError(
            f"OpenCC {EXPECTED_OPENCC_VERSION.removeprefix('Version: ')} required"
        )
    if (
        run(["git", "-C", str(repo), "rev-parse", "HEAD"]).strip()
        != EXPECTED_REPO_COMMIT
    ):
        raise RuntimeError(
            f"OpenCC government-standard repository must be at {EXPECTED_REPO_COMMIT}"
        )
    if run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"]):
        raise RuntimeError(
            "OpenCC government-standard repository has tracked modifications"
        )
    s2t = repo / "t2gov/s2t.json"
    t2gov = repo / "t2gov/t2gov.json"
    if not s2t.is_file() or not t2gov.is_file():
        raise FileNotFoundError("Required s2t.json or t2gov.json is missing")
    return s2t, t2gov


def convert(value: str, s2t: Path, t2gov: Path) -> str:
    traditional = run(["opencc", "-c", str(s2t)], text=value)
    return run(["opencc", "-c", str(t2gov)], text=traditional)


def generated_body(source: str, s2t: Path, t2gov: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        try:
            value = json.loads(match.group())
        except json.JSONDecodeError as error:
            raise RuntimeError("Invalid string in zh-CN dictionary") from error
        return json.dumps(convert(value, s2t, t2gov), ensure_ascii=False)

    return STRING_LITERAL.sub(replace, source)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    args = parser.parse_args()

    s2t, t2gov = verify_tools(args.repo)
    original = INDEX.read_text(encoding="utf-8")
    match = LOCALES.search(original)
    if not match:
        raise RuntimeError("Could not locate zh-CN and zh-Hant-CN dictionaries")
    expected = generated_body(match.group("cn"), s2t, t2gov)
    current = match.group("hant")

    if args.check:
        if current != expected:
            print(
                "".join(
                    difflib.unified_diff(
                        current.splitlines(keepends=True),
                        expected.splitlines(keepends=True),
                        fromfile="current zh-Hant-CN",
                        tofile="generated s2t -> t2gov",
                    )
                )
            )
            raise SystemExit(1)
        print("zh-Hant-CN matches strict OpenCC s2t -> t2gov output")
        return

    INDEX.write_text(
        original[: match.start("hant")] + expected + original[match.end("hant") :],
        encoding="utf-8",
    )
    print("Generated zh-Hant-CN with strict OpenCC s2t -> t2gov")


if __name__ == "__main__":
    main()
