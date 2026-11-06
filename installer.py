#!/usr/bin/env python3
"""Verify and install a locally assembled ColorOS 17 package for Pixel 6a."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time


BUILD = 'coloros17-bluejay-rc1'
SLOT = 'b'
BOOTLOADER = 'bluejay-17.0-15199431'
BASEBAND = 'g5123b-145971-260414-B-15201439'
SUPER_BYTES = 8531214336
PHYSICAL = ('boot', 'vendor_boot', 'dtbo', 'vbmeta_system', 'vbmeta_vendor', 'vbmeta')
LOGICAL = {'system': 7516192768, 'vendor': 805306368, 'vendor_dlkm': 53657600}
EMPTY_LOGICAL = ('product', 'system_ext')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(command, *, timeout=30, show=False):
    if show:
        print(subprocess.list2cmdline([str(arg) for arg in command]), flush=True)
        subprocess.run(command, check=True, timeout=timeout)
        return ''
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, errors='replace', timeout=timeout)
    require(result.returncode == 0, f'{command[0]} {command[-1]} failed:\n{result.stdout.strip()}')
    return result.stdout.strip()


def verify_file(root, path, record):
    file = root / path
    require(file.is_file() and not file.is_symlink(), f'Missing regular file {path}')
    require(file.stat().st_size == record['bytes'], f'Wrong size for {path}')
    digest = hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    require(digest.hexdigest() == record['sha256'], f'SHA-256 mismatch for {path}')
    return file


def read_bundle(root, *, images=True, apps=True):
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    require(manifest['build'] == BUILD and manifest['device'] == 'bluejay', 'Wrong bundle')
    image_paths = {}
    if images:
        records = manifest['images']
        require(len(records) == len(PHYSICAL) + len(LOGICAL) and
                {record['partition'] for record in records} == set(PHYSICAL) | set(LOGICAL),
                'Unexpected image set')
        for record in records:
            name = record['partition']
            if name in LOGICAL:
                require(record['bytes'] == LOGICAL[name], f'Wrong logical size for {name}')
            path = f'images/{name}.img'
            image_paths[name] = verify_file(root, path, record)
            print(f'Verified {path}', flush=True)

    app_paths = {}
    if apps:
        require(manifest['apps'], 'The add-on app list is empty')
        for record in manifest['apps']:
            name = record['package']
            require(re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+', name) and
                    name not in app_paths, 'Invalid or duplicate package name')
            path = f'apps/{name}.apk'
            app_paths[name] = verify_file(root, path, record)
        print(f'Verified {len(app_paths)} app APKs', flush=True)
    return image_paths, app_paths


def connected(tool, state):
    output = run([tool, 'devices'])
    return re.findall(rf'^(\S+)[ \t]+{state}[ \t]*$', output, re.MULTILINE)


def one_device(tool, state):
    serials = connected(tool, state)
    require(len(serials) == 1, f'Connect exactly one authorized {state} device')
    return serials[0]


def getvar(fastboot, name):
    output = run([*fastboot, 'getvar', name])
    match = re.search(rf'^(?:\(bootloader\)\s*)?{re.escape(name)}:\s*(.+?)\s*$',
                      output, re.MULTILINE)
    require(match is not None, f'Cannot read fastboot variable {name}')
    return match.group(1)


def expect(fastboot, name, value):
    actual = getvar(fastboot, name)
    require(actual == value, f'Expected {name}={value}, found {actual}')


def size(fastboot, partition):
    return int(getvar(fastboot, f'partition-size:{partition}'), 0)


def wait_for_fastboot(tool, serial, mode):
    fastboot = [tool, '-s', serial]
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if connected(tool, 'fastboot') == [serial]:
            try:
                if getvar(fastboot, 'is-userspace') == mode:
                    return
            except ValueError:
                pass
        time.sleep(2)
    raise ValueError('The Pixel did not reconnect in the expected fastboot mode')


def flash(tool, images):
    serial = one_device(tool, 'fastboot')
    fastboot = [tool, '-s', serial]
    for key, value in {'product': 'bluejay', 'is-userspace': 'no', 'unlocked': 'yes',
                       'current-slot': SLOT, 'version-bootloader': BOOTLOADER,
                       'version-baseband': BASEBAND, 'snapshot-update-status': 'none',
                       'slot-unbootable:a': 'no', 'slot-successful:a': 'yes',
                       'slot-unbootable:b': 'no'}.items():
        expect(fastboot, key, value)
    require(size(fastboot, 'super') == SUPER_BYTES, 'Unexpected super partition size')
    for name in PHYSICAL:
        require(size(fastboot, f'{name}_{SLOT}') >= images[name].stat().st_size,
                f'{name} does not fit the Pixel partition')

    run([*fastboot, 'reboot', 'fastboot'], show=True)
    wait_for_fastboot(tool, serial, 'yes')
    for key, value in {'product': 'bluejay', 'current-slot': SLOT,
                       'snapshot-update-status': 'none'}.items():
        expect(fastboot, key, value)
    target_sizes = {**LOGICAL, **dict.fromkeys(EMPTY_LOGICAL, 0)}
    actual_sizes = {}
    for name in target_sizes:
        partition = f'{name}_{SLOT}'
        expect(fastboot, f'is-logical:{partition}', 'yes')
        actual_sizes[name] = size(fastboot, partition)

    # Free space before growing partitions. A release already using these sizes skips resizing.
    resize = [name for name in target_sizes if actual_sizes[name] != target_sizes[name]]
    resize.sort(key=lambda name: target_sizes[name] - actual_sizes[name])
    for name in resize:
        run([*fastboot, 'resize-logical-partition', f'{name}_{SLOT}', str(target_sizes[name])],
            show=True)
    for name, target in target_sizes.items():
        require(size(fastboot, f'{name}_{SLOT}') == target, f'Unexpected resized {name} partition')
    for name in LOGICAL:
        run([*fastboot, 'flash', f'{name}_{SLOT}', images[name]], timeout=1800, show=True)

    run([*fastboot, 'reboot', 'bootloader'], show=True)
    wait_for_fastboot(tool, serial, 'no')
    expect(fastboot, 'product', 'bluejay')
    expect(fastboot, 'current-slot', SLOT)
    for name in PHYSICAL:
        run([*fastboot, 'flash', f'{name}_{SLOT}', images[name]], timeout=180, show=True)
    run([*fastboot, '-w'], timeout=300, show=True)
    print('Flash complete. Select Start on the Pixel to begin Android setup.')


def install_apps(tool, apps):
    adb = [tool, '-s', one_device(tool, 'device')]
    require(run([*adb, 'shell', 'getprop', 'ro.product.vendor.device']) == 'bluejay',
            'This add-on bundle is for Pixel 6a')
    require(run([*adb, 'shell', 'getprop', 'ro.pixel.port.release']) == BUILD,
            'The installed ROM does not match this release')
    require(run([*adb, 'shell', 'settings', '--user', '0', 'get', 'secure',
                 'user_setup_complete']) == '1', 'Finish Android setup first')
    installed = set(run([*adb, 'shell', 'pm', 'list', 'packages', '--user', '0']).splitlines())
    for package, file in apps.items():
        if f'package:{package}' in installed:
            print(f'Already installed {package}')
            continue
        run([*adb, 'install', '--user', '0', '-r', file], timeout=600, show=True)
    installed = set(run([*adb, 'shell', 'pm', 'list', 'packages', '--user', '0']).splitlines())
    # Static shared libraries are listed with pm list libraries, rather than as user apps.
    missing = set(apps) - {name.removeprefix('package:') for name in installed}
    if 'com.google.android.trichromelibrary' in missing:
        libraries = run([*adb, 'shell', 'pm', 'list', 'libraries'])
        if re.search(r'^library:com\.google\.android\.trichromelibrary(?:\s|$)',
                     libraries, re.MULTILINE):
            missing.remove('com.google.android.trichromelibrary')
    require(not missing, f'Packages missing after installation: {", ".join(sorted(missing))}')
    print('Add-on app installation complete.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify', 'flash', 'apps'))
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--platform-tools', type=Path, help='directory containing adb and fastboot')
    parser.add_argument('--execute', action='store_true', help='send commands to the Pixel')
    parser.add_argument('--wipe-userdata', action='store_true', help='acknowledge a clean install erases data')
    args = parser.parse_args()
    if args.action == 'flash' and args.execute and not args.wipe_userdata:
        parser.error('a clean flash requires --execute and --wipe-userdata')
    images, apps = read_bundle(args.bundle.resolve(), images=args.action != 'apps',
                               apps=args.action != 'flash' or args.execute)
    if args.action == 'verify' or not args.execute:
        if args.action == 'flash':
            print('Plan only. Fastbootd will write system, vendor and vendor_dlkm to slot b. '
                  'Bootloader fastboot will write six boot/AVB images to slot b, then wipe userdata.')
        elif args.action == 'apps':
            print('Plan only. Verified APKs will be installed after Android setup with --execute.')
        return
    name = 'fastboot' if args.action == 'flash' else 'adb'
    if args.platform_tools:
        suffix = '.exe' if sys.platform == 'win32' else ''
        tool = str((args.platform_tools / (name + suffix)).resolve())
    else:
        tool = name
    if args.action == 'flash':
        flash(tool, images)
    else:
        install_apps(tool, apps)


if __name__ == '__main__':
    try:
        main()
    except (OSError, KeyError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(f'Stopped: {error}')
