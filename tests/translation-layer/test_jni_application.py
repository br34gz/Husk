#!/usr/bin/env python3
"""Regression coverage for the shared ActivityThread/Application contract.

The JNI HLE is arm64/Darwin code and cannot execute in the existing Linux test
runner.  This test therefore validates the registration graph and the identity
implementation directly: SDL only installs the shared table, all application
entry points must use its one handler, and UE4 must not override those entries.

Reproduced by Husk 1.1.0 (61), 0698e4f-dirty on iPhone18,1 / iOS 27.0.1
with an SDL game:
  UNIMPLEMENTED:
  android/app/ActivityThread.currentApplication()Landroid/app/Application;
  abort() called from libAPKVISION.so
  Java_com_android_support_Main_resolveConfig+0xb62c
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SHARED = (ROOT / "src/translation-layer-next/husk-tl-jni-hle.c").read_text()
UE4 = (ROOT / "src/translation-layer-next/husk-tl-jni-ue4.c").read_text()
SDL = (ROOT / "src/translation-layer-next/husk-tl-sdl.c").read_text()


def require(pattern: str, text: str, message: str) -> None:
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        raise AssertionError(message)


# SDL's engine path must install the shared HLE table containing this support.
require(r"tl_jni_init\(\);\s*tl_hle_configure\([^;]+;\s*tl_jni_hle_install\(\);",
        SDL, "SDL does not install the shared JNI HLE")

# One process-wide object backs every way native code asks for the Application.
require(r"static void Application_get\([^)]*\)\s*\{[^}]*H\.application",
        SHARED, "Application_get is not backed by the shared Application")
require(r'H\.application\s*=\s*make\("android/app/Application"\)',
        SHARED, "shared HLE does not construct the process Application")
require(r'\{\s*"android/app/Application",\s*"android/content/Context"\s*\}',
        SHARED, "Application no longer inherits Context")

expected = (
    ("android/app/ActivityThread", "currentApplication",
     "()Landroid/app/Application;"),
    ("android/app/ActivityThread", "getApplication",
     "()Landroid/app/Application;"),
    ("android/app/Activity", "getApplication",
     "()Landroid/app/Application;"),
    ("android/content/Context", "getApplicationContext",
     "()Landroid/content/Context;"),
)
for cls, name, sig in expected:
    require(
        rf'M\("{re.escape(cls)}",\s*"{name}",\s*"{re.escape(sig)}",\s*'
        r'(?:Application_get|Context_getApplicationContext)\)',
        SHARED,
        f"missing shared registration for {cls}.{name}{sig}",
    )

require(r"static void Context_getApplicationContext\([^)]*\)\s*\{\s*Application_get\(c\);\s*\}",
        SHARED, "getApplicationContext does not return the same Application")
require(r'currentActivityThread",\s*"\(\)Landroid/app/ActivityThread;",\s*ActivityThread_current',
        SHARED, "currentActivityThread is not registered in the shared HLE")

# Engine-specific installation happens after the shared table.  A duplicate
# registration would replace the shared method, recreating the SDL/UE4 split.
if 'M_("android/app/ActivityThread"' in UE4:
    raise AssertionError("UE4 still overrides shared ActivityThread methods")

print("shared SDL ActivityThread/Application context contract: ok")
