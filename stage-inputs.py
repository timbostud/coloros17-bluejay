#!/usr/bin/env python3
"""Stage a local build using an existing patched system and original app files."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from installer import LOGICAL, require


def copy_checked(source, target, expected_hash):
    if source.is_file():
        opener = source.open
    else:
        source = source.with_suffix(source.suffix + '.gz')
        opener = lambda mode: gzip.open(source, mode)
    temporary = target.with_suffix(target.suffix + '.partial')
    digest = hashlib.sha256()
    try:
        with opener('rb') as incoming, temporary.open('xb') as outgoing:
            for block in iter(lambda: incoming.read(8 * 1024 * 1024), b''):
                digest.update(block)
                outgoing.write(block)
        if expected_hash:
            require(digest.hexdigest() == expected_hash, f'Wrong checksum for {source.name}')
        temporary.rename(target)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--system', type=Path, required=True, help='raw ext4 image of the patched port')
    parser.add_argument('--hardware', type=Path, required=True, help='directory containing the eight .img files')
    parser.add_argument('--oppo', type=Path, required=True, help='root containing extracted OPPO my_* partitions')
    parser.add_argument('--google', type=Path, required=True, help='root containing Google app/ and priv-app/')
    parser.add_argument('--agc', type=Path, required=True, help='original AGC Camera 1.8.6 APK')
    args = parser.parse_args()
    require(args.system.stat().st_size == LOGICAL['system'], 'Unexpected input system image size')
    catalog = json.loads(Path(__file__).with_name('sources.json').read_text(encoding='utf-8'))
    args.bundle.mkdir()
    for directory in ('images', 'apps', 'staging'):
        (args.bundle / directory).mkdir()

    copy_checked(args.system, args.bundle / 'images/system.img', None)
    for name, digest in catalog['hardware_sha256'].items():
        copy_checked(args.hardware / f'{name}.img', args.bundle / f'images/{name}.img', digest)
    for app in catalog['apps']:
        placement = app['placement']
        if placement == 'base-system':
            continue
        source = app['source']
        origin = args.agc if source == 'agc' else getattr(args, source) / app['source_path']
        target = (args.bundle / 'staging' / app['staged_filename'] if placement == 'system'
                  else args.bundle / 'apps' / f"{app['package']}.apk")
        copy_checked(origin, target, app['sha256'])
    print('Inputs staged. Apply prepare-system.sh to the new system image, then generate the manifest.')


if __name__ == '__main__':
    main()
