# Compatibility entry point: map and server are part of the same main release.
$ErrorActionPreference='Stop'
& python "$PSScriptRoot/build_release.py"
if ($LASTEXITCODE -ne 0) { throw 'Main release build failed.' }
