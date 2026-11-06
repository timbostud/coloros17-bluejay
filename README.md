# ColorOS 17 for Pixel 6a

An unofficial Android 17 port for **Pixel 6a (`bluejay`)**. Includes English first-run setup, AGC Camera, Play Store, OPPO Clock and Weather, and Flux wallpapers. The port also includes the Pixel fixes for power, battery, fingerprint, Dynamic Island, live wallpapers, and touch vibration. [Full feature list and build notes](BUILDING.md)

## Install on Windows

**Back up first. A clean flash erases your apps and files.** This RC1 package requires an unlocked Pixel 6a on active slot **b** with the [matching firmware and layout](BUILDING.md#clean-flash). Keep the bootloader unlocked.

1. Extract the RC1 images ZIP. Download [Google Platform-Tools](https://developer.android.com/tools/releases/platform-tools) and place the extracted `platform-tools` folder next to `Flash.cmd`.
2. Power off the Pixel. Hold **Volume Down + Power** to enter the bootloader, then connect the USB cable.
3. Double-click **`Flash.cmd`**. Once the checks pass, type `FLASH` to confirm. Select **Start** on the Pixel when flashing finishes.
4. Complete Android setup. For the remaining Google and OPPO apps, enable **USB debugging**, allow your PC on the phone, and double-click **`Install Apps.cmd`**.

`system.img` is the ROM. Android Recovery and fastbootd are in `vendor_boot.img`. Keep the included images together. For stock recovery instructions, see [Google Pixel factory images](https://developers.google.com/android/images/).

The ZIP passed file checks and the clean first boot still needs a hardware test. This repository hosts the scripts and guide. [Assemble the images locally from the required inputs](BUILDING.md#assemble-a-local-bundle).
