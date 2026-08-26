#!/usr/bin/env python3
"""Build the bundled Vietnamese and Korean WOFF2 subsets from local fonts."""

from __future__ import annotations

import hashlib
import unicodedata
from copy import deepcopy
from pathlib import Path

from fontTools import __version__ as fonttools_version
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "fonts"
INDEX = ROOT / "index.html"

ARIAL_BLACK = Path("/System/Library/Fonts/Supplemental/Arial Black.ttf")
ARIAL_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
BAEKMUK = Path("/usr/local/texlive/2025/texmf-dist/fonts/truetype/public/baekmuk")
USER_FONTS = Path.home() / "Library/Fonts"

KOREAN_SOURCES = {
    "baekmuk-headline-ko.woff2": BAEKMUK / "hline.ttf",
    "baekmuk-gulim-ko.woff2": BAEKMUK / "gulim.ttf",
    "baekmuk-dotum-ko.woff2": BAEKMUK / "dotum.ttf",
    "baekmuk-batang-ko.woff2": BAEKMUK / "batang.ttf",
    "kp-kwangmyeong-bold-ko.woff2": USER_FONTS
    / "KCC-KP-KwangMyeong-Bold-KP-2011KPS.ttf",
    "kp-cheonrima-ko.woff2": USER_FONTS / "KCC-KP-CheonRiMa-Normal-KP-2011KPS.ttf",
    "kp-cheongpong-ko.woff2": USER_FONTS / "KCC-KP-CheongPong-Medium-KP-2011KPS.ttf",
}

EXPECTED_FONTTOOLS_VERSION = "4.63.0"
SOURCE_SHA256 = {
    ARIAL_BLACK: "7d7db3ad96a31373c1437c6ab14266f6605495544c8e663558b047521174c42e",
    ARIAL_BOLD: "d72db21f9242aedd6b917d8549ad5921766b24d5f8d0becfda2ff4c620b3c2e0",
    BAEKMUK
    / "hline.ttf": "346d802287c2e39f72a439dfda939b7cd979b7fe35344696b9375409f55de091",
    BAEKMUK
    / "gulim.ttf": "7db4c7c96c1a873953ef0abfdb413b07e200aa66493ddff9451f879f9ba11393",
    BAEKMUK
    / "dotum.ttf": "62b65ca0067cf7e7f40e853e047f8e0ad33e33bd71655f912fabf3a1f67096fc",
    BAEKMUK
    / "batang.ttf": "0f418065f3cbbe5724823dc1aaf439755c8d0a6e5f323d8aee93ce4d069b8367",
    KOREAN_SOURCES[
        "kp-kwangmyeong-bold-ko.woff2"
    ]: "65460bb1fae575a2346637e74fe1138ee2d2dba254271793c8adf31970a51e0f",
    KOREAN_SOURCES[
        "kp-cheonrima-ko.woff2"
    ]: "5881005af40c125b914b6956cf73298f9f9f39d6c3147bac9ecc6e6261d400f6",
    KOREAN_SOURCES[
        "kp-cheongpong-ko.woff2"
    ]: "3898acaf96c2223442e93ef1e4b0923733f9f45f62ed0462ba63a2422d3c0a8e",
}
VIETNAMESE_LATIN1 = "ÀÁÃÈÉÌÍÒÓÕÙÚÝàáãèéìíòóõùúý"


def verify_sources() -> None:
    if fonttools_version != EXPECTED_FONTTOOLS_VERSION:
        raise RuntimeError(
            f"fontTools {EXPECTED_FONTTOOLS_VERSION} required; found {fonttools_version}"
        )
    for path, expected in SOURCE_SHA256.items():
        if not path.exists():
            raise FileNotFoundError(path)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Unexpected source font checksum: {path}")


def unicode_cmap(font: TTFont) -> dict[int, str]:
    result: dict[int, str] = {}
    for table in font["cmap"].tables:
        if table.isUnicode():
            result.update(table.cmap)
    return result


def save_subset(font: TTFont, output: Path, codepoints: set[int]) -> None:
    for table in ("hdmx", "LTSH", "VDMX"):
        if table in font:
            del font[table]
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = list(range(26))
    options.name_legacy = True
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=codepoints)
    subsetter.subset(font)
    font.flavor = "woff2"
    font.recalcTimestamp = False
    font.save(output)


def vietnamese_codepoints() -> set[int]:
    alphabet = "AĂÂBCDĐEÊGHIKLMNOÔƠPQRSTUƯVXYaăâbcdđeêghiklmnoôơpqrstuưvxy"
    vowels = "AĂÂEÊIOÔƠUƯYaăâeêioôơuưy"
    tones = "\u0300\u0301\u0309\u0303\u0323"
    toned = "".join(
        unicodedata.normalize("NFC", vowel + tone) for vowel in vowels for tone in tones
    )
    precomposed = alphabet + toned
    if not set(VIETNAMESE_LATIN1) <= set(precomposed):
        raise RuntimeError("Vietnamese Latin-1 repertoire is incomplete")
    decomposed = "".join(unicodedata.normalize("NFD", char) for char in precomposed)
    return set(range(0x20, 0x7F)) | {ord(char) for char in precomposed + decomposed}


def build_vietnamese() -> None:
    black = TTFont(ARIAL_BLACK)
    donor = TTFont(ARIAL_BOLD)
    required = vietnamese_codepoints()
    black_cmap = unicode_cmap(black)
    donor_cmap = unicode_cmap(donor)
    black_glyf = black["glyf"]
    donor_glyf = donor["glyf"]
    black_hmtx = black["hmtx"]
    donor_hmtx = donor["hmtx"]

    def copy_glyph(name: str) -> None:
        if name in black_glyf or name not in donor_glyf:
            return
        black_glyf[name] = deepcopy(donor_glyf[name])
        black_hmtx[name] = donor_hmtx[name]
        glyph = donor_glyf[name]
        if glyph.isComposite():
            for component in glyph.components:
                copy_glyph(component.glyphName)

    for codepoint in sorted(required - black_cmap.keys()):
        donor_name = donor_cmap.get(codepoint)
        if not donor_name:
            raise RuntimeError(f"Arial Bold lacks U+{codepoint:04X}")
        copy_glyph(donor_name)
        for table in black["cmap"].tables:
            if table.isUnicode():
                table.cmap[codepoint] = donor_name

    glyph_order = list(black_glyf.glyphs)
    black_glyf.glyphOrder = glyph_order
    black.setGlyphOrder(glyph_order)
    save_subset(black, FONTS / "arial-black-vietnamese.woff2", required)

    built = TTFont(FONTS / "arial-black-vietnamese.woff2")
    missing = required - unicode_cmap(built).keys()
    if missing:
        raise RuntimeError(
            "Vietnamese subset missing: "
            + ", ".join(f"U+{cp:04X}" for cp in sorted(missing))
        )


def hangul_codepoints() -> set[int]:
    text = INDEX.read_text(encoding="utf-8")
    return {
        ord(char)
        for char in text
        if 0x1100 <= ord(char) <= 0x11FF
        or 0x3130 <= ord(char) <= 0x318F
        or 0xAC00 <= ord(char) <= 0xD7A3
    }


def build_korean() -> None:
    codepoints = hangul_codepoints()
    if not codepoints:
        raise RuntimeError("No Hangul found in index.html")
    for filename, source in KOREAN_SOURCES.items():
        if not source.exists():
            raise FileNotFoundError(source)
        font = TTFont(source)
        missing = codepoints - unicode_cmap(font).keys()
        if missing:
            raise RuntimeError(
                f"{source.name} lacks {len(missing)} required Hangul characters"
            )
        output = FONTS / filename
        save_subset(font, output, codepoints)
        built = TTFont(output)
        missing = codepoints - unicode_cmap(built).keys()
        if missing:
            raise RuntimeError(
                f"{filename} missing {len(missing)} required Hangul characters"
            )


if __name__ == "__main__":
    verify_sources()
    FONTS.mkdir(exist_ok=True)
    build_vietnamese()
    build_korean()
    for path in sorted(FONTS.glob("*.woff2")):
        print(f"{path.relative_to(ROOT)}\t{path.stat().st_size} bytes")
