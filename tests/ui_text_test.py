"""Host-only menu localization regression; no game files, GPU or window required.

Compile the real catalog and configuration store. Only platform I/O, locking
(single-threaded fixture), system locale and game language are supplied here.
"""
import ctypes
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "platform/platform.h"
#include "ui_text.h"
#include "cfg.h"
const char *test_menu_values(void) { return cfg_meta("TOTK_MENU_LANG")->values; }
static char locale[64];
void test_locale(const char *s) { snprintf(locale, sizeof locale, "%s", s); }
const char *plat_ui_language(void) { return locale; }
const char *ov_language(void) { return "ja"; }
void plat_mutex_lock(PlatMutex *m) { (void)m; }
void plat_mutex_unlock(PlatMutex *m) { (void)m; }
void rt_log(const char *fmt, ...) { (void)fmt; }
void rt_fatal(const char *fmt, ...) { (void)fmt; abort(); }
int plat_exe_path(char *out, size_t cap) { (void)out; (void)cap; return 0; }
int64_t plat_file_size(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fclose(f);
    return n;
}
int plat_file_exists(const char *path) { return plat_file_size(path) >= 0; }
uint8_t *plat_file_read(const char *path, uint64_t *size) {
    int64_t n = plat_file_size(path);
    if (n < 0) return NULL;
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    uint8_t *p = malloc((size_t)n + 1);
    if (!p) abort();
    *size = fread(p, 1, (size_t)n, f);
    p[*size] = 0;
    fclose(f);
    return p;
}
int plat_file_write_atomic(const char *path, const void *data, size_t n) {
    char tmp[4096];
    snprintf(tmp, sizeof tmp, "%s.tmp", path);
    FILE *f = fopen(tmp, "wb");
    if (!f) return 0;
    int ok = fwrite(data, 1, n, f) == n;
    if (fclose(f)) ok = 0;
    return ok && !rename(tmp, path);
}
int test_first(void) { return UI_MENU_FIRST; }
int test_last(void) { return UI_MENU_LAST_ID; }
int test_title(void) { return UI_MENU_TITLE; }
int test_desc_bytes(void) { return UI_DESC_BYTES; }
// These IDs are passed as format strings by the menu, binds page and overlay.
int test_is_format(int id) {
    switch (id) {
    case UI_MENU_VERSION: case UI_MENU_PRESENT_IN_USE: case UI_PERF_LINE_FPS:
    case UI_MENU_FPS_DISPLAY_HZ: case UI_MENU_PAD_LAYOUT_IN_USE:
    case UI_BINDS_PRESS_KEY: case UI_BINDS_PRESS_PAD: case UI_BINDS_CANCEL_HINT:
    case UI_BINDS_TAKEN: case UI_BINDS_SWAPPED: case UI_KEY_NUM_FMT:
    case UI_MENU_OV_FPS: case UI_MENU_OV_FRAME_MS: case UI_MENU_OV_GAME_PCT:
    case UI_MENU_OV_MAX_MS: case UI_MENU_OV_FMT_PCT: case UI_MENU_OV_FMT_TEMP:
    case UI_MENU_OV_FMT_POWER: case UI_MENU_OV_FMT_MHZ: case UI_MENU_OV_FMT_GB:
    case UI_MENU_OV_FMT_GB_OF: case UI_MENU_OV_GAME_GB: case UI_MENU_OV_FMT_MS:
    case UI_MENU_OV_PER_FRAME: case UI_MENU_OV_FMT_SIZE: case UI_MENU_OV_FMT_SCENE:
    case UI_MENU_OV_FMT_FSR: return 1;
    default: return 0;
    }
}
'''
FORMAT = re.compile(r'%(?:%|[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|ll|[hljztL])?[diouxXfFeEgGaAcspn])')


class MenuTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='menu-text-')
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        source = directory / 'providers.c'
        source.write_text(PROVIDERS)
        library = directory / ('catalog.dylib' if sys.platform == 'darwin' else 'catalog.so')
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-dynamiclib' if sys.platform == 'darwin' else '-shared', '-fPIC',
                        '-I', str(ROOT / 'runtime'), str(ROOT / 'runtime/ui_text.c'),
                        str(ROOT / 'runtime/cfg.c'), str(source), '-o', str(library)], check=True)
        cls.lib = ctypes.CDLL(str(library))
        for name, args, result in [
            ('ui_text_in', [ctypes.c_char_p, ctypes.c_int], ctypes.c_char_p),
            ('ui_text_defined', [ctypes.c_char_p, ctypes.c_int], ctypes.c_int),
            ('menu_text', [ctypes.c_int], ctypes.c_char_p),
            ('cfg_set', [ctypes.c_char_p, ctypes.c_char_p], None),
            ('cfg_value', [ctypes.c_char_p], ctypes.c_char_p),
            ('cfg_save_to', [ctypes.c_char_p], ctypes.c_int),
            ('cfg_load', [ctypes.c_char_p], ctypes.c_int),
            ('test_locale', [ctypes.c_char_p], None),
            ('test_menu_values', [], ctypes.c_char_p),
        ]:
            fn = getattr(cls.lib, name)
            fn.argtypes, fn.restype = args, result

    def setUp(self):
        self.saved_env = {key: os.environ.pop(key) for key in
                          ('TOTK_MENU_LANG', 'DKB_MENU_LANG') if key in os.environ}
        self.addCleanup(os.environ.update, self.saved_env)

    def test_complete_catalogs_and_formats(self):
        for lang in (b'en', b'ru', b'zh-Hans', b'zh-Hant'):
            for text_id in range(self.lib.test_first(), self.lib.test_last() + 1):
                with self.subTest(language=lang, text_id=text_id):
                    self.assertTrue(self.lib.ui_text_defined(lang, text_id))
                    text = self.lib.ui_text_in(lang, text_id).decode('utf-8')
                    english = self.lib.ui_text_in(b'en', text_id).decode('utf-8')
                    if self.lib.test_is_format(text_id):
                        self.assertEqual(FORMAT.findall(text), FORMAT.findall(english))
                    self.assertLess(len(text.encode('utf-8')) + 256, self.lib.test_desc_bytes())

    def test_menu_choices(self):
        self.assertEqual(self.lib.test_menu_values(), b'en|ru|zh-Hans|zh-Hant')

    def test_live_switch_and_explicit_override(self):
        self.lib.test_locale(b'zh-TW')
        for lang, title in [(b'zh-Hans', '设置'), (b'zh-Hant', '設定'),
                            (b'ru', 'Настройки'), (b'en', 'Settings')]:
            self.lib.cfg_set(b'TOTK_MENU_LANG', lang)
            self.assertEqual(self.lib.menu_text(self.lib.test_title()).decode(), title)

    def test_system_locales(self):
        cases = {'zh': 'zh-Hans', 'zh-CN': 'zh-Hans', 'zh-SG': 'zh-Hans',
                 'zh-TW': 'zh-Hant', 'zh-HK': 'zh-Hant', 'zh-MO': 'zh-Hant',
                 'zh-Hans': 'zh-Hans', 'zh-Hant': 'zh-Hant',
                 'zh-Hans-TW': 'zh-Hans', 'zh-Hant-CN': 'zh-Hant',
                 'ZH_hk.UTF-8': 'zh-Hant', 'zh_CN.UTF-8': 'zh-Hans',
                 'ru-RU': 'ru', 'ru': 'ru', 'en-US': 'en', 'fr-FR': 'en',
                 'zhx': 'en', '': 'en', 'C': 'en'}
        for locale, expected in cases.items():
            with self.subTest(locale=locale):
                self.lib.test_locale(locale.encode())
                self.lib.cfg_set(b'TOTK_MENU_LANG', b'')
                self.assertEqual(self.lib.menu_text(self.lib.test_title()),
                                 self.lib.ui_text_in(expected.encode(), self.lib.test_title()))

    def test_save_reload_and_environment_override(self):
        path = Path(self.temp.name) / 'totk.ini'
        path.write_text('# keep this comment\n[language]\nlang = ja\nmenu_lang = en\n')
        for lang in (b'zh-Hans', b'zh-Hant'):
            self.assertEqual(self.lib.cfg_load(os.fsencode(path)), 1)
            self.lib.cfg_set(b'TOTK_MENU_LANG', lang)
            self.assertEqual(self.lib.cfg_save_to(os.fsencode(path)), 1)
            self.assertIn('# keep this comment\n', path.read_text())
            self.assertIn('lang = ja\n', path.read_text())
            self.lib.cfg_set(b'TOTK_MENU_LANG', b'en')
            self.assertEqual(self.lib.cfg_load(os.fsencode(path)), 1)
            self.assertEqual(self.lib.cfg_value(b'TOTK_MENU_LANG'), lang)
        os.environ['TOTK_MENU_LANG'] = 'zh-Hans'
        self.addCleanup(os.environ.pop, 'TOTK_MENU_LANG', None)
        self.lib.cfg_set(b'TOTK_MENU_LANG', b'en')
        self.assertEqual(self.lib.menu_text(self.lib.test_title()).decode(), '设置')


if __name__ == '__main__':
    unittest.main()
