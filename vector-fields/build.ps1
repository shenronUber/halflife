param([switch]$Force)
$ErrorActionPreference='Stop'
$vfReleaseArguments=@("$PSScriptRoot/build_release.py")
if ($Force) { $vfReleaseArguments+='--force' }
& python @vfReleaseArguments
if ($LASTEXITCODE -ne 0) { throw 'Validated release build/publication failed; see vector-fields/build/releases.' }
