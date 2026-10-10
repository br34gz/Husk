#!/usr/bin/env python3
"""Regression contract for APK-defined native Runnables on SDL's HLE path."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDL = (ROOT / "src/translation-layer-next/husk-tl-sdl.c").read_text()
LOOP = (ROOT / "src/translation-layer-next/husk-tl-jni-loop.c").read_text()

assert '"com/android/support/NativeProxy", "<init>", "(Landroid/content/Context;Landroid/app/Dialog;)V", NativeProxy_init' in SDL
assert '"ctx", "Landroid/content/Context;", vl(c->args[0].l)' in SDL
assert '"dialog", "Landroid/app/Dialog;", vl(c->args[1].l)' in SDL
assert 'tl_jni_native(tl_jni_class_name(run), "run", "()V")' in LOOP
assert "native_run(tl_jni_env(), run);" in LOOP

print("SDL APK native Runnable contract: ok")
