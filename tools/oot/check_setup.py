"""Validate the Windows setup folder and its ZIP before uploading a CI artifact.

Uses only the standard library and original host tools; no game copy is needed.
"""
import argparse
import hashlib
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_content import problems_for

REQUIRED = (
    'Instalar-Ocarina.exe',
    'instalador/Instalar-Ocarina.ps1',
    'projeto/VERSION',
    'projeto/runtime/ui_text.c',
    'ferramentas/python/python.exe',
    'ferramentas/llvm/bin/clang.exe',
    'ferramentas/deps/bin/SDL3.dll',
    'ferramentas/deps/bin/libopus-0.dll',
    'ferramentas/bin/ninja.exe',
    'ferramentas/bin/unzbic.exe',
    'ferramentas/bin/totk_xlate.exe',
    'ferramentas/bin/totk_xlate.id',
)


def check_x64(path: Path) -> None:
    with path.open('rb') as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b'MZ':
            raise ValueError(f'{path}: missing DOS/PE header')
        offset = struct.unpack_from('<I', header, 60)[0]
        stream.seek(offset)
        pe = stream.read(6)
        if len(pe) != 6 or pe[:4] != b'PE\0\0' or struct.unpack_from('<H', pe, 4)[0] != 0x8664:
            raise ValueError(f'{path}: not a Windows x64 PE binary')


def digest(stream) -> str:
    result = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        result.update(chunk)
    return result.hexdigest()


def validate(folder: Path, archive: Path) -> int:
    for name in REQUIRED:
        if not (folder / name).is_file():
            raise ValueError(f'Missing setup file: {name}')
    files = {p.relative_to(folder).as_posix(): p for p in folder.rglob('*') if p.is_file()}
    for name, path in files.items():
        problems = problems_for(path, allow_large=True)
        if path.suffix.lower() in {'.nup', '.spv'} or path.name.lower() in {'ocarina.exe', 'totk.exe'}:
            problems.append('game-derived output is not part of a setup package')
        if problems:
            raise ValueError(f'{name}: {", ".join(problems)}')
        if path.suffix.lower() in {'.exe', '.dll', '.pyd'}:
            check_x64(path)
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        expected = {f'{folder.name}/{name}': path for name, path in files.items()}
        if len(entries) != len(expected) or {entry.filename for entry in entries} != expected.keys():
            raise ValueError('ZIP contents differ from the validated setup folder')
        for entry in entries:
            path = expected[entry.filename]
            if entry.file_size != path.stat().st_size:
                raise ValueError(f'ZIP size mismatch: {entry.filename}')
            with zipped.open(entry) as member, path.open('rb') as original:
                if digest(member) != digest(original):
                    raise ValueError(f'ZIP content mismatch: {entry.filename}')
    return len(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    args = parser.parse_args()
    try:
        count = validate(args.folder, args.archive)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Setup validation failed: {error}\n')
    print(f'Validated {count} setup files, Windows x64 binaries and matching ZIP contents.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
