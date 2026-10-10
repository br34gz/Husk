#!/usr/bin/env python3
"""Execute the shared HLE Toast/Uri implementations with JNI test doubles."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / "src/translation-layer-next/husk-tl-jni-hle.c").read_text()

def function(name):
    start = source.index("static void " + name + "(")
    end = source.index("{", start) + 1
    depth = 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]

assert '"makeText", "(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;", Toast_makeText' in source
assert '"parse", "(Ljava/lang/String;)Landroid/net/Uri;", Uri_parse' in source
harness = r'''
#define _POSIX_C_SOURCE 200809L
#include "husk-tl-jni.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
static bool pending;
static char message[200];
static jvalue vl(void *p) { jvalue v = {0}; v.l = p; return v; }
static jobj *make(const char *name) { (void)name; jobj *o = calloc(1, sizeof(*o)); o->refs=1; return o; }
jobj *tl_jni_new_string(const char *s) { jobj *o=make(""); o->kind=TL_K_STRING; o->str.utf8=strdup(s); return o; }
const char *tl_jni_string(const jobj *o) { return o && o->kind==TL_K_STRING ? o->str.utf8 : NULL; }
static const char *S(const jobj *o) { const char *s=tl_jni_string(o); return s ? s : ""; }
#define STR(s) tl_jni_new_string(s)
bool tl_jni_pending(void) { return pending; }
void tl_jni_throw(const char *cls, const char *s) { (void)s; assert(!strcmp(cls,"java/lang/NullPointerException")); pending=true; }
void tl_jni_unref(jobj *o) { if (!o || --o->refs) return; if (o->destroy) o->destroy(o); if(o->kind==TL_K_STRING) free(o->str.utf8); free(o); }
jvalue tl_jni_call(jobj *o,const char *n,const char *s,const jvalue *a) {
    (void)o; (void)a; assert(!strcmp(n,"toString") && !strcmp(s,"()Ljava/lang/String;"));
    return vl(STR("char sequence"));
}
void tl_log_line(const char *fmt,...) { va_list a; va_start(a,fmt); vsnprintf(message,sizeof(message),fmt,a); va_end(a); }
'''
for name in ("TextObject_destroy", "Toast_setText", "Toast_makeText", "Toast_show", "Uri_parse", "Uri_toString"):
    harness += function(name) + "\n"
harness += r'''
int main(void) {
    jobj context={0};
    jvalue args[3]={vl(&context),vl(STR("configuration failed")),{.i=1}};
    tl_jcall c={.args=args}; Toast_makeText(&c);
    jobj *toast=c.ret.l; assert(toast && !pending);
    tl_jni_unref(args[1].l); c.self=toast; Toast_show(&c);
    assert(!strcmp(message,"android: Toast: configuration failed"));
    jvalue sequence=vl(&context); c.args=&sequence; Toast_setText(&c); Toast_show(&c);
    assert(!strcmp(message,"android: Toast: char sequence")); tl_jni_unref(toast);
    jvalue uri_arg=vl(STR("https://example.test/a%20b?q=1#fragment"));
    c=(tl_jcall){.args=&uri_arg}; Uri_parse(&c); jobj *uri=c.ret.l;
    assert(uri && !pending); tl_jni_unref(uri_arg.l);
    c.self=uri; Uri_toString(&c);
    assert(!strcmp(S(c.ret.l),"https://example.test/a%20b?q=1#fragment"));
    tl_jni_unref(c.ret.l); tl_jni_unref(uri);
    uri_arg.l=NULL; c=(tl_jcall){.args=&uri_arg}; Uri_parse(&c);
    assert(pending && !c.ret.l); pending=false;
    args[0].l=NULL; c=(tl_jcall){.args=args}; Toast_makeText(&c);
    assert(pending && !c.ret.l);
    return 0;
}
'''
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    (path / "test.c").write_text(harness)
    subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-I" + str(ROOT / "src/translation-layer-next"), str(path / "test.c"),
                    "-o", str(path / "test")], check=True)
    subprocess.run([str(path / "test")], check=True)
print("shared Toast/Uri text lifetime, forwarding and null handling: ok")
