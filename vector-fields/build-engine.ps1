param([int]$Jobs=8,[switch]$Configure)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$sourceRoot=(Join-Path $projectRoot 'runtime/engine-source').Replace('\','/')
$outputRoot=Join-Path $projectRoot 'runtime/vector-engine'
$sdlRoot=Join-Path $projectRoot 'devtools/SDL2-sdk/SDL2-2.32.10'
$revision='9137964147d8f749dbeddf1cb5482c3d16f86e4a'
if (!(Test-Path "$sourceRoot/waf")) {throw 'Missing Xash3D checkout: see vector-fields/engine/README.md.'}
if (!(Test-Path "$sdlRoot/lib/x86/SDL2.dll")) {throw 'Missing SDL2 2.32.10 Visual C++ SDK: see vector-fields/engine/README.md.'}
$actual=& git -c "safe.directory=$sourceRoot" -C $sourceRoot rev-parse HEAD
if ($actual -ne $revision) {throw "Engine revision differs from the reviewed base: $actual"}
$env:PYTHONUTF8='1'
# Waf invokes Git itself for its build identification.
$env:GIT_CONFIG_COUNT='1';$env:GIT_CONFIG_KEY_0='safe.directory';$env:GIT_CONFIG_VALUE_0=$sourceRoot
$patchFile=Join-Path $PSScriptRoot 'engine/xash3d.patch'
if (Test-Path $patchFile) {
    & git -C $sourceRoot apply --reverse --check $patchFile 2>$null
    if ($LASTEXITCODE -ne 0) {
        & git -C $sourceRoot apply --check $patchFile
        if ($LASTEXITCODE -ne 0) {throw 'Engine patch conflicts with local edits; source was not overwritten.'}
        & git -C $sourceRoot apply $patchFile
        if ($LASTEXITCODE -ne 0) {throw 'Could not apply the engine patch.'}
    }
}
Copy-Item "$projectRoot/game_shared/vf_engine_api.h" "$sourceRoot/common/vf_engine_api.h"
Copy-Item "$PSScriptRoot/engine/gl_vf.inc" "$sourceRoot/ref/gl/gl_vf.inc"
Push-Location $sourceRoot
try {
    if ($Configure -or !(Test-Path 'build/c4che/_cache.py')) {
        & python waf configure "--sdl2=$sdlRoot" -T release --enable-tests --enable-dedicated --enable-bundled-deps '--msvc_version=msvc 17.4' --msvc_targets=x86 --disable-werror
        if ($LASTEXITCODE -ne 0) {throw 'Engine configuration failed.'}
    }
    & python waf build -j $Jobs
    if ($LASTEXITCODE -ne 0) {throw 'Engine build/tests failed.'}
    & python waf install "--destdir=$outputRoot"
    if ($LASTEXITCODE -ne 0) {throw 'Engine installation failed. Close the native prototype before rebuilding.'}
    Copy-Item "$sdlRoot/lib/x86/SDL2.dll" "$outputRoot/SDL2.dll"
} finally {Pop-Location}
$binaryHashes=@{}
foreach($binaryName in @('xash3d.exe','xash.dll','xash.exe','ref_gl.dll','SDL2.dll')) {
    $binaryHashes[$binaryName]=(Get-FileHash (Join-Path $outputRoot $binaryName) -Algorithm SHA256).Hash
}
@{base_commit=$revision;built_utc=[DateTime]::UtcNow.ToString('o');architecture='win32-i386';
  extension_version=2;patch_sha256=(Get-FileHash $patchFile -Algorithm SHA256).Hash;
  renderer_sha256=(Get-FileHash "$PSScriptRoot/engine/gl_vf.inc" -Algorithm SHA256).Hash;
  binaries=$binaryHashes} | ConvertTo-Json -Depth 3 | Set-Content "$outputRoot/vector-engine-build.json" -Encoding utf8
Write-Output "Native engine built: $outputRoot"
