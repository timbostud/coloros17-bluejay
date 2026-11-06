# ColorOS 17 for Pixel 6a

An unofficial Android 17 port for the Google Pixel 6a (`bluejay`), based on the AxisGSI ColorOS 17 PLK110 build and the Pixel Tensor hardware stack. This repository contains the release tools and input checksums. The locally assembled **RC1** bundle requires separately obtained firmware and APKs. A clean first boot of RC1 still needs a hardware test.

## What's included

| Area | RC1 |
| --- | --- |
| First boot | English (United States) by default and the Google Setup Wizard enabled for a clean install |
| Camera | BigKaka AGC Camera 1.8.6 preinstalled and preferred for standard Android photo and camera intents |
| Google | Play Store, Play services, Services Framework, Gboard, and the first-run wizard in the system; Chrome, Maps, Photos, Gmail, YouTube, YouTube Music, Calendar, Drive, Google Search, speech services, and the other entries in `sources.json` via the add-on installer |
| OPPO | Clock, Weather, and the weather service in the system; the remaining selected OPPO and HeyTap apps, including Calculator, Notes, Files, Recorder, Calendar, Theme Store, and Phone Manager, via the add-on installer |
| Themes | Bundled Flux wallpapers and the OPPO online Flux catalog, including the Mountain variants and weather animation fixes. Online catalog items download inside the wallpaper picker. |

The app set contains the 34 OPPO and 13 Google packages selected for this port, plus AGC Camera. App and service availability can vary by region. The AGC default covers the standard photo intents listed above. Camera launch paths specific to the lock screen or individual apps can use a different handler.

## Port fixes

- Pixel Wi-Fi and the secure-storage services used by KeyMint.
- Immediate response to the physical power button.
- Control Center sizing, window corner transitions, and charging and battery reporting.
- Pixel-sized and positioned Dynamic Island with media and OPPO Clock timer capsules.
- Fingerprint enrollment, unlock, and the ColorOS indicator and ripple.
- Always-on clock with a dimmed wallpaper and changes to reduce display flashing.
- Live wallpaper persistence and Mountain playback on the home screen.
- Short Android click and tick effects through the Pixel vibration driver.

These changes come from the working port. The installer and image are release-candidate material. SELinux runs in **Permissive** mode and the bootloader must remain unlocked. Face unlock, IMS/VoLTE, all camera modes, Play Integrity, and long-term battery use have no release-level verification. Slight AOD flicker or tint was observed on the working port.

## Clean flash

You need a compatible **Pixel 6a** with an unlocked bootloader, active slot **b**, a previously booted fallback on slot **a**, and no pending OTA snapshot. The bootloader must report `bluejay-17.0-15199431` and the baseband must report `g5123b-145971-260414-B-15201439`. The known starting layout is the port's Pixel `CP1A.260405.005` hardware base. The installer also checks the model, slot state, super size, partition sizes, and image checksums. Start with a full backup, a charged phone, and a reliable USB cable. This is a **clean flash that erases user data**.

1. Install Python 3.11+ and Google's Android SDK Platform-Tools. Keep `adb` and `fastboot` on `PATH` or pass `--platform-tools PATH_TO_PLATFORM_TOOLS`. [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools)
2. Put the assembled bundle on a drive with room for the images and APKs. Verify the complete bundle before starting.

   ```sh
   python installer.py verify PATH_TO_BUNDLE
   python installer.py flash PATH_TO_BUNDLE
   ```

3. Turn the phone off, then hold Volume Down and Power to enter the bootloader. Connect just that Pixel over USB. Run the clean flash when you have verified the backup.

   ```sh
   python installer.py flash PATH_TO_BUNDLE --execute --wipe-userdata
   ```

4. Select **Start** in the bootloader when the script finishes. The first boot may take several minutes. Complete the on-device Google Setup Wizard.
5. In **Settings → About device**, enable Developer options, then enable USB debugging and authorize your computer. Install the remaining original-signature APKs from the bundle.

   ```sh
   python installer.py apps PATH_TO_BUNDLE --execute
   ```

   If interrupted, run the app step again. It checks the installed release and skips packages Android already reports as installed. You can switch USB debugging off afterward.

The clean-flash command writes the checked system and hardware images to slot **b** and leaves the phone in the bootloader. The bootloader, radio firmware, calibration partitions, and slot **a** are outside the write list. If a command stops mid-flash, keep the phone in the bootloader and use the official Pixel 6a recovery instructions for your current or newer firmware. Follow Google's Pixel 6a anti-rollback guidance before changing firmware or using the fallback slot. [Google Pixel factory images and recovery guidance](https://developers.google.com/android/images/)

## Assemble a local bundle

Use the already-patched raw ext4 system image from this port and the eight corresponding Pixel hardware images. This repository expects that base as input. `sources.json` lists the required SHA-256 checksums, APK paths, and placement. The Google APKs come from the Pixel 6a `CP2A.260705.006` factory image, the OPPO APKs from `PLK110_17.0.0.105(CN01)`, and AGC from BigKaka's 1.8.6 release. [AxisGSI donor](https://sourceforge.net/projects/axisgsiupdates/files/coloros/ColorOS-17-PLK110-1789230075256-18092026-AxisGSI.zip/download) · [Google factory images](https://developers.google.com/android/images/) · [AGC Camera](https://www.celsoazevedo.com/files/android/agc-camera/f/dl08/1/)

```sh
python stage-inputs.py bundle --system PORT_SYSTEM.img --hardware HARDWARE_IMAGES \
  --oppo EXTRACTED_OPPO_PARTITIONS --google EXTRACTED_GOOGLE_APPS --agc AGC_Camera-1.8.6.apk
```

On Linux, mount the newly copied image read-write with loopback, run `prepare-system.sh`, and unmount it before validating. The Linux environment needs `e2fsprogs` and the `attr` utilities, and must be able to write ext4 SELinux labels. The preparation script checks for the final haptics and Mountain files before applying changes.

```sh
mkdir -p ./system-mount
sudo mount -t ext4 -o loop bundle/images/system.img ./system-mount
sudo sh prepare-system.sh ./system-mount ./bundle/staging
sudo umount ./system-mount
e2fsck -fn bundle/images/system.img
python make-manifest.py bundle
python installer.py verify bundle
```

Keep the firmware and APKs in your local bundle. Google factory images and the other third-party inputs are subject to their own distribution terms. [Google factory image terms](https://developers.google.com/android/images/#terms-and-conditions)
