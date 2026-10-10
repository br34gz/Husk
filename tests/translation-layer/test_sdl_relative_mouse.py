#!/usr/bin/env python3
"""Regression contract for SDL's shared Android relative-mouse callbacks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "src/translation-layer-next/husk-tl-sdl.c").read_text()


def require(fragment: str) -> None:
    assert fragment in SOURCE, f"missing SDL relative-mouse contract: {fragment}"


require('M_(SDLA, "supportsRelativeMouse", "()Z", A_supportsRelativeMouse)')
require('M_(SDLA, "setRelativeMouseEnabled", "(Z)Z", A_setRelativeMouseEnabled)')
require("s_relative_mouse = c->args[0].z;")
require("c->ret = vz(1);")
assert 'M_(SDLA, "supportsRelativeMouse", "()Z", A_false)' not in SOURCE
assert 'M_(SDLA, "setRelativeMouseEnabled", "(Z)Z", A_false)' not in SOURCE

print("SDL relative-mouse enable/disable contract: ok")
