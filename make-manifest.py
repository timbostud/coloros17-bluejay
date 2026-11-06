#!/usr/bin/env python3
"""Index a flash bundle assembled from local, authorized source files."""

import argparse
import hashlib
import json
from pathlib import Path

from installer import BUILD, LOGICAL, PHYSICAL, require


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    root = args.bundle.resolve()
    catalog = json.loads(Path(__file__).with_name('sources.json').read_text(encoding='utf-8'))
    manifest = {'build': BUILD, 'device': 'bluejay', 'images': [], 'apps': []}
    for partition in (*PHYSICAL, *LOGICAL):
        path = root / 'images' / f'{partition}.img'
        size = path.stat().st_size
        checksum = digest(path)
        if partition in LOGICAL:
            require(size == LOGICAL[partition], f'Wrong logical size for {partition}')
        if partition != 'system':
            require(checksum == catalog['hardware_sha256'][partition],
                    f'{partition} is different from the tested Pixel hardware image')
        else:
            with path.open('rb') as system:
                system.seek(1080)
                require(system.read(2) == b'\x53\xef', 'Expected a raw ext4 system image')
        manifest['images'].append({'partition': partition, 'bytes': size, 'sha256': checksum})
    expected = [app for app in catalog['apps'] if app['placement'] == 'post-setup']
    files = {p.name for p in (root / 'apps').glob('*.apk')}
    require(files == {f"{app['package']}.apk" for app in expected}, 'Unexpected set of add-on APKs')
    for app in expected:
        package = app['package']
        path = root / 'apps' / f'{package}.apk'
        require(digest(path) == app['sha256'], f'Wrong original APK for {package}')
        manifest['apps'].append({'package': package, 'bytes': path.stat().st_size,
                                 'sha256': app['sha256']})
    output = root / 'manifest.json'
    output.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
