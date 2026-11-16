"""Test the setup validator with synthetic files, without game data or Windows."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('check_setup', ROOT / 'tools/oot/check_setup.py')
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


def pe(machine=0x8664):
    data = bytearray(70)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 64)
    data[64:68] = b'PE\0\0'
    struct.pack_into('<H', data, 68, machine)
    return data


class SetupTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name) / 'Ocarina-Setup-0.0.0'
        self.archive = Path(temporary.name) / 'setup.zip'
        for name in setup.REQUIRED:
            path = self.folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pe() if path.suffix in {'.exe', '.dll'} else b'fixture\n')
        self.pack()

    def pack(self):
        with zipfile.ZipFile(self.archive, 'w') as zipped:
            for path in self.folder.rglob('*'):
                if path.is_file():
                    zipped.write(path, path.relative_to(self.folder.parent))

    def test_valid_setup(self):
        self.assertEqual(setup.validate(self.folder, self.archive), len(setup.REQUIRED))

    def test_missing_tool(self):
        (self.folder / 'ferramentas/bin/totk_xlate.exe').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing setup file'):
            setup.validate(self.folder, self.archive)

    def test_reject_x86_and_arm64(self):
        for machine in (0x14c, 0xaa64):
            with self.subTest(machine=machine):
                (self.folder / 'Instalar-Ocarina.exe').write_bytes(pe(machine))
                self.pack()
                with self.assertRaisesRegex(ValueError, 'not a Windows x64'):
                    setup.validate(self.folder, self.archive)

    def test_reject_non_pe(self):
        (self.folder / 'Instalar-Ocarina.exe').write_bytes(b'not an executable')
        with self.assertRaisesRegex(ValueError, 'missing DOS/PE header'):
            setup.validate(self.folder, self.archive)

    def test_reject_game_generated_content(self):
        from check_content import GENERATED_MARKER
        (self.folder / 'generated.c').write_text(GENERATED_MARKER)
        self.pack()
        with self.assertRaisesRegex(ValueError, 'generated from game code'):
            setup.validate(self.folder, self.archive)

    def test_reject_game_executable_and_package(self):
        for name in ('ocarina.exe', 'copy.nup'):
            with self.subTest(name=name):
                path = self.folder / name
                path.write_bytes(pe())
                self.pack()
                with self.assertRaisesRegex(ValueError, 'game-derived output'):
                    setup.validate(self.folder, self.archive)
                path.unlink()

    def test_reject_extra_zip_member(self):
        with zipfile.ZipFile(self.archive, 'a') as zipped:
            zipped.writestr('unexpected.txt', b'not in validated folder')
        with self.assertRaisesRegex(ValueError, 'ZIP contents differ'):
            setup.validate(self.folder, self.archive)

    def test_reject_changed_zip_content(self):
        (self.folder / 'projeto/VERSION').write_bytes(b'changed\n')
        with self.assertRaisesRegex(ValueError, 'ZIP content mismatch'):
            setup.validate(self.folder, self.archive)


if __name__ == '__main__':
    unittest.main()
