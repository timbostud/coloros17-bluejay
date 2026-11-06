#!/bin/sh
# Apply clean-install defaults to a mounted copy of the known bluejay ext4 image.
set -eu

[ "$#" = 2 ] || { echo 'Usage: prepare-system.sh MOUNTPOINT STAGED_APK_DIRECTORY' >&2; exit 2; }
root=$(realpath "$1")
input=$(realpath "$2")
[ "$root" != / ]
mountpoint -q "$root"
[ -d "$root/system/app" ] && [ ! -L "$root/system/app" ]
sha256sum -c <<EOF
94e5f0c0b7c2e05760363147d0cb233ab3f0d49a67613be390512380a211d317  $root/system/framework/oplus-services.jar
7970fb42a2b1a1e9080fb82f937a2d6b088bf3e0fd67d5b0148380925b11a3a6  $root/my_product/decouping_wallpaper/common/wallpaper_group/coe2_coz_weather/weather.coz2
EOF
[ -s "$root/system/priv-app/SetupWizard/SetupWizard.apk" ]
[ -s "$root/system/priv-app/Phonesky/Phonesky.apk" ]
[ -s "$root/my_stock/priv-app/Wallpapers/Wallpapers.apk" ]

product_prop="$root/product/etc/build.prop"
if [ -L "$root/product" ]; then
    [ "$(readlink "$root/product")" = /system/product ]
    product_prop="$root/system/product/etc/build.prop"
fi
[ -f "$product_prop" ] && [ ! -L "$product_prop" ]
[ "$(grep -c '^ro.setupwizard.mode=DISABLED$' "$product_prop")" = 1 ]
system_prop="$root/system/build.prop"
[ "$(grep -c '^ro.product.locale=en-US$' "$system_prop")" = 1 ]
! grep -q '^ro.pixel.port.release=' "$system_prop"

label_system() {
    setfattr -n security.selinux -v u:object_r:system_file:s0 "$1"
    [ "$(getfattr --only-values -n security.selinux "$1" 2>/dev/null | tr -d '\000')" = u:object_r:system_file:s0 ]
}

for name in AGCCamera OppoClock OppoWeatherService OppoWeather; do
    [ -s "$input/$name.apk" ]
    [ ! -e "$root/system/app/$name" ]
done
sha256sum -c <<EOF
52fa474dd0b8bb75af452daa5d7a7f0d248f9760ae9156dbdaa80abe581d8970  $input/AGCCamera.apk
c8d7bb09f10bb727cb49a14c0efe5ee99c339162e131c2e49f85ef5ca65632bf  $input/OppoClock.apk
5c9ecd41b39f85f8c7f8096a93ec18c2705ad822c611e724ced38e0ddfe32e92  $input/OppoWeatherService.apk
d8c51d4a2cbd6d596323e8e6b7a15e4fe130e485367865cb3fa989a28bf016c5  $input/OppoWeather.apk
EOF

for name in AGCCamera OppoClock OppoWeatherService OppoWeather; do
    app="$root/system/app/$name"
    install -d -m 0755 -o 0 -g 0 "$app"
    label_system "$app"
    install -m 0644 -o 0 -g 0 "$input/$name.apk" "$app/$name.apk"
    label_system "$app/$name.apk"
    cmp "$input/$name.apk" "$app/$name.apk"
done

preferred="$root/system/etc/preferred-apps"
if [ ! -d "$preferred" ]; then
    install -d -m 0755 -o 0 -g 0 "$preferred"
    label_system "$preferred"
fi
[ ! -L "$preferred" ]
camera="$preferred/pixel-agc-camera.xml"
[ ! -e "$camera" ]
cat > "$camera" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<preferred-activities>
    <item name="com.agc.gcam/.app.CameraActivity" match="108000" always="true" set="0">
        <filter>
            <action name="android.media.action.STILL_IMAGE_CAMERA" />
            <cat name="android.intent.category.DEFAULT" />
        </filter>
    </item>
    <item name="com.agc.gcam/.app.CameraActivity" match="108000" always="true" set="0">
        <filter>
            <action name="android.media.action.IMAGE_CAPTURE" />
            <cat name="android.intent.category.DEFAULT" />
        </filter>
    </item>
</preferred-activities>
EOF
chmod 0644 "$camera"
chown 0:0 "$camera"
label_system "$camera"

# Overwrite the contents in place to preserve the original inode metadata and label.
sed 's/^ro.setupwizard.mode=DISABLED$/ro.setupwizard.mode=OPTIONAL/' "$product_prop" > "$input/product-build.prop"
cat "$input/product-build.prop" > "$product_prop"
printf '\nro.pixel.port.release=coloros17-bluejay-rc1\n' >> "$system_prop"
grep -qx 'ro.setupwizard.mode=OPTIONAL' "$product_prop"
grep -qx 'ro.pixel.port.release=coloros17-bluejay-rc1' "$system_prop"
sync
echo 'Clean-install system files prepared'
