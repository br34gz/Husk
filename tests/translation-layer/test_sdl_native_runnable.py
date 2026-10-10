#!/usr/bin/env python3
"""Regression contract for APK-defined native Runnables on SDL's HLE path."""

from pathlib import Path
import subprocess
import tempfile
import os

ROOT = Path(__file__).resolve().parents[2]
SDL = (ROOT / "src/translation-layer-next/husk-tl-sdl.c").read_text()
LOOP = (ROOT / "src/translation-layer-next/husk-tl-jni-loop.c").read_text()

assert '"com/android/support/NativeProxy", "<init>", "(Landroid/content/Context;Landroid/app/Dialog;)V", NativeProxy_init' in SDL
assert 'tl_jni_native(tl_jni_class_name(run), "run", "()V")' in LOOP
assert "native_run(tl_jni_env(), run);" in LOOP

def function(source, name):
    start = source.index("static void " + name + "(")
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]

# Compile the actual constructor/destructor against a reference-counting test
# double. Dropping the caller's JNI references must not invalidate its fields;
# destroying the proxy must return both objects to their original reference count.
harness = r'''
#include "husk-tl-jni.h"
#include <assert.h>
#include <string.h>
#include <pthread.h>
static pthread_once_t native_proxy_once = PTHREAD_ONCE_INIT;
static int loads, registrations;
static bool registered;
static jobj entry_class;
void tl_log_line(const char *fmt, ...) { (void)fmt; }
bool tl_jni_pending(void) { return false; }
bool tl_jni_load_library(const char *base) {
    assert(!strcmp(base, "libstub.so")); ++loads; return true;
}
void *tl_jni_env(void) { return &entry_class; }
jobj *tl_jni_class_object(const char *name) {
    assert(!strcmp(name, "np/dcc/protect/EntryPoint")); return &entry_class;
}
static void stub(void *env, void *cls, int32_t index) {
    assert(env == &entry_class && cls == &entry_class && index == 6);
    ++registrations; registered = true;
}
void *tl_jni_native(const char *cls, const char *name, const char *sig) {
    if (!strcmp(cls, "np/dcc/protect/EntryPoint")) {
        assert(loads && !strcmp(name, "stub") && !strcmp(sig, "(I)V"));
        return (void *)stub;
    }
    assert(!strcmp(cls, "com/android/support/NativeProxy"));
    assert(!strcmp(name, "run") && !strcmp(sig, "()V"));
    return registered ? (void *)stub : NULL;
}
static jvalue vl(void *p) { jvalue v = {0}; v.l = p; return v; }
jobj *tl_jni_ref(jobj *o) { if (o) ++o->refs; return o; }
void tl_jni_unref(jobj *o) { if (o) { assert(o->refs); --o->refs; } }
void tl_jni_set_field(jobj *o, const char *name, const char *sig, jvalue v) {
    (void)sig; o->fields[!strcmp(name, "dialog")] = v;
}
jvalue tl_jni_get_field(jobj *o, const char *name, const char *sig) {
    (void)sig; return o->fields[!strcmp(name, "dialog")];
}
'''
harness += function(SDL, "NativeProxy_register") + '\n'
harness += function(SDL, "NativeProxy_destroy") + '\n' + function(SDL, "NativeProxy_init")
harness += r'''
int main(void) {
    jobj context = {.refs = 1}, dialog = {.refs = 1};
    jvalue fields[2] = {0}, args[2] = {vl(&context), vl(&dialog)};
    jobj proxy = {.refs = 1, .fields = fields};
    tl_jcall call = {.self = &proxy, .args = args};
    NativeProxy_init(&call);
    tl_jni_unref(&context); tl_jni_unref(&dialog);
    assert(context.refs == 1 && dialog.refs == 1);
    assert(fields[0].l == &context && fields[1].l == &dialog);
    assert(proxy.destroy); proxy.destroy(&proxy);
    assert(context.refs == 0 && dialog.refs == 0);
    args[0].l = args[1].l = 0;
    NativeProxy_init(&call); proxy.destroy(&proxy);
    assert(loads == 1 && registrations == 1);
    NativeProxy_register();
    assert(loads == 1 && registrations == 1);
    return 0;
}
'''
with tempfile.TemporaryDirectory() as directory:
    source = Path(directory) / "ownership.c"
    binary = Path(directory) / "ownership"
    source.write_text(harness)
    subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-pthread", "-I" + str(ROOT / "src/translation-layer-next"), str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)

print("SDL native Runnable registration and proxy ownership: ok")
