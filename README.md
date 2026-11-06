# ColorOS 17 for Pixel 6a

An unofficial Android 17 port for **Pixel 6a (`bluejay`)**. Includes English first-run setup, AGC Camera, Play Store, OPPO Clock and Weather, and Flux wallpapers. The port also includes the Pixel fixes for power, battery, fingerprint, Dynamic Island, live wallpapers, and touch vibration.

## Install on Windows

**Back up first. A clean flash erases your apps and files.** RC1 requires an unlocked Pixel 6a on active slot **b**, a bootable fallback on slot **a**, and the `CP1A.260405.005` port hardware layout. The flasher checks for bootloader `bluejay-17.0-15199431`, baseband `g5123b-145971-260414-B-15201439`, and a clear OTA snapshot state. Keep the bootloader unlocked.

1. Extract the RC1 images ZIP. Download [Google Platform-Tools](https://developer.android.com/tools/releases/platform-tools) and place the extracted `platform-tools` folder next to `Flash.cmd`.
2. Power off the Pixel. Hold **Volume Down + Power** to enter the bootloader, then connect the USB cable.
3. Double-click **`Flash.cmd`**. Once the checks pass, type `FLASH` to confirm. Select **Start** on the Pixel when flashing finishes.
4. Complete Android setup. For the remaining Google and OPPO apps, enable **USB debugging**, allow your PC on the phone, and double-click **`Install Apps.cmd`**.

`system.img` is the ROM. Android Recovery and fastbootd are in `vendor_boot.img`. Keep the included images together. For stock recovery instructions, see [Google Pixel factory images](https://developers.google.com/android/images/).

The ZIP passed file checks and the clean first boot still needs a hardware test. SELinux runs in Permissive mode. The RC1 image ZIP is a separate local bundle. [RC1 build notes and source inputs](https://github.com/timbostud/coloros17-bluejay/blob/1da37dce825cbe911824eb632f0ec8d1461423bb/BUILDING.md)
