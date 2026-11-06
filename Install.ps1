param([switch]$Apps, [switch]$PlanOnly)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$build = 'coloros17-bluejay-rc1'
$boot = @('boot', 'vendor_boot', 'dtbo', 'vbmeta_system', 'vbmeta_vendor', 'vbmeta')
$logical = [ordered]@{ system = 7516192768; vendor = 805306368; vendor_dlkm = 53657600; product = 0; system_ext = 0 }
$manifest = Get-Content -LiteralPath (Join-Path $root 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.device -cne 'bluejay' -or $manifest.build -cne $build) { throw 'Wrong bundle.' }

function Check-File($Path, $Record) {
    $file = Get-Item -LiteralPath $Path
    if ($file.Length -ne $Record.bytes -or (Get-FileHash -LiteralPath $Path).Hash -ne $Record.sha256) {
        throw "File check failed for $($file.Name). Extract the ZIP again."
    }
}

function Find-Tool($Name) {
    $local = Join-Path $root "platform-tools\$Name.exe"
    if (Test-Path -LiteralPath $local -PathType Leaf) { return $local }
    return (Get-Command "$Name.exe" -CommandType Application).Source
}

function Get-Devices($Tool, $State) {
    & $Tool devices | ForEach-Object {
        if ($_ -match "^(\S+)\s+$State\s*$") { $Matches[1] }
    }
    if ($LASTEXITCODE -ne 0) { throw "$Tool devices failed." }
}

if ($Apps) {
    if (@($manifest.apps).Count -ne 43) { throw 'Wrong add-on list.' }
    foreach ($app in $manifest.apps) {
        if ($app.package -cnotmatch '^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)+$') { throw 'Invalid APK name.' }
        Check-File (Join-Path $root "apps\$($app.package).apk") $app
    }
    if ($PlanOnly) { Write-Host 'Verified 43 APKs.'; return }
    $adb = Find-Tool 'adb'
    $devices = @(Get-Devices $adb 'device')
    if ($devices.Count -ne 1) { throw 'Connect one Pixel and allow USB debugging on it.' }
    $serial = $devices[0]
    if ((& $adb -s $serial shell getprop ro.product.vendor.device) -cne 'bluejay' -or
        (& $adb -s $serial shell getprop ro.pixel.port.release) -cne $build -or
        (& $adb -s $serial shell settings --user 0 get secure user_setup_complete) -ne '1') {
        throw 'Finish setup on the matching ColorOS 17 RC1 build first.'
    }
    $installed = @(& $adb -s $serial shell pm list packages --user 0)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to read installed packages.' }
    foreach ($app in $manifest.apps) {
        $package = $app.package
        if ($installed -contains "package:$package") { continue }
        Write-Host "Installing $package"
        $apk = Join-Path $root "apps\$package.apk"
        & $adb -s $serial install --user 0 -r $apk
        if ($LASTEXITCODE -ne 0) { throw "Installation stopped at $package." }
    }
    Write-Host 'Apps installed.'
    return
}

$expected = $boot + @('system', 'vendor', 'vendor_dlkm')
if (@($manifest.images).Count -ne $expected.Count -or
    (Compare-Object $expected @($manifest.images.partition))) { throw 'Wrong image list.' }
$images = @{}
foreach ($image in $manifest.images) {
    $name = $image.partition
    if ($logical.Contains($name) -and $image.bytes -ne $logical[$name]) { throw "Wrong size for $name." }
    $images[$name] = Join-Path $root "$name.img"
    Write-Host "Checking $name.img"
    Check-File $images[$name] $image
}
if ($PlanOnly) { Write-Host 'Verified all nine images.'; return }

$fastboot = Find-Tool 'fastboot'
$devices = @(Get-Devices $fastboot 'fastboot')
if ($devices.Count -ne 1) { throw 'Connect one Pixel in bootloader mode.' }
$serial = $devices[0]

function Read-Var($Name) {
    $ErrorActionPreference = 'Continue'
    $result = (& $fastboot -s $serial getvar $Name 2>&1 | ForEach-Object { $_.ToString() }) -join "`n"
    $pattern = '(?m)^(?:\(bootloader\)\s*)?' + [regex]::Escape($Name) + ':\s*([^\r\n]+)'
    if ($LASTEXITCODE -ne 0 -or $result -notmatch $pattern) { throw "Fastboot cannot read $Name." }
    return $Matches[1].Trim()
}

function Require-Var($Name, $Expected) {
    $actual = Read-Var $Name
    if ($actual -cne $Expected) { throw "Expected $Name=$Expected, found $actual." }
}

function Partition-Size($Name) {
    $value = Read-Var "partition-size:$Name"
    if ($value -match '^0x([0-9a-fA-F]+)$') { return [Convert]::ToInt64($Matches[1], 16) }
    return [long]$value
}

function Send-Fastboot {
    & $fastboot -s $serial @args
    if ($LASTEXITCODE -ne 0) { throw 'Fastboot stopped. See the recovery link in README.md.' }
}

function Wait-Mode($Userspace) {
    $deadline = [DateTime]::UtcNow.AddSeconds(90)
    do {
        $online = @(Get-Devices $fastboot 'fastboot')
        if ($online.Count -eq 1 -and $online[0] -eq $serial) {
            try { if ((Read-Var 'is-userspace') -eq $Userspace) { return } } catch { }
        }
        Start-Sleep -Seconds 2
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'The Pixel did not reconnect in the expected fastboot mode.'
}

Require-Var 'is-userspace' 'no'
Require-Var 'product' 'bluejay'
Require-Var 'unlocked' 'yes'
Require-Var 'current-slot' 'b'
Require-Var 'slot-unbootable:a' 'no'
Require-Var 'slot-successful:a' 'yes'
Require-Var 'slot-unbootable:b' 'no'
Require-Var 'version-bootloader' 'bluejay-17.0-15199431'
Require-Var 'version-baseband' 'g5123b-145971-260414-B-15201439'
Require-Var 'snapshot-update-status' 'none'
if ((Partition-Size 'super') -ne 8531214336) { throw 'Wrong super partition size.' }
foreach ($name in $boot) {
    if ((Partition-Size "${name}_b") -lt (Get-Item -LiteralPath $images[$name]).Length) {
        throw "$name.img does not fit."
    }
}
Write-Host 'A clean flash erases the apps and files on this Pixel.'
if ((Read-Host 'Type FLASH to start') -cne 'FLASH') { Write-Host 'Cancelled.'; return }

Send-Fastboot 'reboot' 'fastboot'
Wait-Mode 'yes'
Require-Var 'product' 'bluejay'
Require-Var 'current-slot' 'b'
Require-Var 'snapshot-update-status' 'none'
$changes = foreach ($name in $logical.Keys) {
    $partition = "${name}_b"
    Require-Var "is-logical:$partition" 'yes'
    $size = Partition-Size $partition
    if ($size -ne $logical[$name]) {
        [pscustomobject]@{ Partition = $partition; Target = $logical[$name]; Delta = $logical[$name] - $size }
    }
}
foreach ($change in ($changes | Sort-Object Delta)) {
    Send-Fastboot 'resize-logical-partition' $change.Partition "$($change.Target)"
}
foreach ($name in $logical.Keys) {
    if ((Partition-Size "${name}_b") -ne $logical[$name]) { throw "Wrong size for ${name}_b." }
}
foreach ($name in @('system', 'vendor', 'vendor_dlkm')) {
    Send-Fastboot 'flash' "${name}_b" $images[$name]
}

Send-Fastboot 'reboot' 'bootloader'
Wait-Mode 'no'
Require-Var 'product' 'bluejay'
Require-Var 'current-slot' 'b'
foreach ($name in $boot) { Send-Fastboot 'flash' "${name}_b" $images[$name] }
Send-Fastboot '-w'
Write-Host 'Flash complete. Select Start on the Pixel.'
