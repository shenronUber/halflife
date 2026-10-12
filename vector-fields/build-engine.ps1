param([int]$Jobs=8,[switch]$Configure,[string]$Destination="",[string]$BuildDirectory="")
$ErrorActionPreference='Stop'
$vfEngineIdentity=& python "$PSScriptRoot/build_release.py" --engine-identity
if ($LASTEXITCODE -ne 0) { throw 'Engine source identity failed.' }
$projectRoot=Split-Path -Parent $PSScriptRoot
# Use the physical project path so Waf shares one cache through the C: junction.
$projectRootItem=Get-Item -LiteralPath $projectRoot -Force
if($projectRootItem.LinkType -eq 'Junction') {
    $projectRoot=[IO.Path]::GetFullPath(@($projectRootItem.Target)[0])
}
$sourceRoot=(Join-Path $projectRoot 'runtime/engine-source').Replace('\','/')
$outputRoot=if ($Destination) {[IO.Path]::GetFullPath((Join-Path $projectRoot $Destination))} else {Join-Path $PSScriptRoot 'build/engine-candidate'}
if ($outputRoot.TrimEnd('\','/') -eq (Join-Path $projectRoot 'runtime/vector-engine').TrimEnd('\','/')) {throw 'Build the engine privately, then publish through build_release.py.'}
$wafArgs=@()
if ($BuildDirectory) {
    $vfBuildPath=[IO.Path]::GetFullPath((Join-Path $projectRoot $BuildDirectory))
    if (!$vfBuildPath.StartsWith(([IO.Path]::GetFullPath($projectRoot)+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)) {throw 'Build cache must remain inside the project.'}
    $wafArgs=@("--out=$vfBuildPath")
}
if (!$outputRoot.StartsWith(([IO.Path]::GetFullPath($projectRoot)+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)) {throw 'Engine destination must remain inside the project.'}
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
foreach ($vfEnginePatch in @($patchFile,(Join-Path $PSScriptRoot 'engine/first-person-body.patch'),(Join-Path $PSScriptRoot 'engine/performance.patch'),(Join-Path $PSScriptRoot 'engine/player-pose.patch'))) {
if (Test-Path $vfEnginePatch) {
    # A not-yet-applied optional patch is expected to fail the reverse probe.
    # Windows PowerShell 5 turns native stderr into terminating errors under
    # Stop; inspect the exit code without treating this probe as a build error.
    $vfProbePreference=$ErrorActionPreference
    try {
        $ErrorActionPreference='Continue'
        & git -C $sourceRoot apply --reverse --check $vfEnginePatch 2>$null
        $vfReverseExit=$LASTEXITCODE
    } finally {$ErrorActionPreference=$vfProbePreference}
    if ($vfReverseExit -ne 0) {
        & git -C $sourceRoot apply --check $vfEnginePatch
        if ($LASTEXITCODE -ne 0) {throw 'Engine patch conflicts with local edits; source was not overwritten.'}
        & git -C $sourceRoot apply $vfEnginePatch
        if ($LASTEXITCODE -ne 0) {throw 'Could not apply the engine patch.'}
    }
}
}
Copy-Item "$projectRoot/game_shared/vf_engine_api.h" "$sourceRoot/common/vf_engine_api.h"
Copy-Item "$projectRoot/game_shared/vf_assembly_policy.h" "$sourceRoot/common/vf_assembly_policy.h"
Copy-Item "$projectRoot/game_shared/vf_traversal.h" "$sourceRoot/common/vf_traversal.h"
Copy-Item "$projectRoot/game_shared/vf_wallrun.h" "$sourceRoot/common/vf_wallrun.h"
Copy-Item "$PSScriptRoot/engine/vf_wallrun_pose.inc" "$sourceRoot/common/vf_wallrun_pose.inc"
Copy-Item "$PSScriptRoot/engine/vf_wallrun_pose.inc" "$sourceRoot/ref/gl/vf_wallrun_pose.inc"
Copy-Item "$PSScriptRoot/engine/gl_vf_perf.inc" "$sourceRoot/ref/gl/gl_vf_perf.inc"
Copy-Item "$PSScriptRoot/engine/gl_vf.inc" "$sourceRoot/ref/gl/gl_vf.inc"
Copy-Item "$PSScriptRoot/engine/gl_vf_headgear.inc" "$sourceRoot/ref/gl/gl_vf_headgear.inc"
Copy-Item "$projectRoot/game_shared/vf_headgear.h" "$sourceRoot/common/vf_headgear.h"
Copy-Item "$projectRoot/game_shared/vf_player_pose.h" "$sourceRoot/common/vf_player_pose.h"
Copy-Item "$PSScriptRoot/engine/vf_player_pose.inc" "$sourceRoot/common/vf_player_pose.inc"
Copy-Item "$PSScriptRoot/engine/sv_vf_pose.inc" "$sourceRoot/common/sv_vf_pose.inc"
Copy-Item "$PSScriptRoot/engine/gl_vf_headgear.inc" "$sourceRoot/common/gl_vf_headgear.inc"
Copy-Item "$PSScriptRoot/engine/vf_player_pose.inc" "$sourceRoot/ref/gl/vf_player_pose.inc"
Push-Location $sourceRoot
try {
    if ($Configure -or $BuildDirectory -or !(Test-Path 'build/c4che/_cache.py')) {
        & python waf configure @wafArgs "--sdl2=$sdlRoot" -T release --enable-tests --enable-dedicated --enable-bundled-deps '--msvc_version=msvc 17.4' --msvc_targets=x86 --disable-werror
        if ($LASTEXITCODE -ne 0) {throw 'Engine configuration failed.'}
    }
    & python waf build @wafArgs -j $Jobs --notests
    if ($LASTEXITCODE -ne 0) {throw 'Engine build failed.'}
    # The client/server image tests write the same test_gen.* files in their
    # shared output directory. Run tests serially after parallel compilation.
    & python waf build @wafArgs -j 1 --alltests
    if ($LASTEXITCODE -ne 0) {throw 'Engine tests failed.'}
    & python waf install @wafArgs "--destdir=$outputRoot"
    if ($LASTEXITCODE -ne 0) {throw 'Engine installation failed. Close the native prototype before rebuilding.'}
    Copy-Item "$sdlRoot/lib/x86/SDL2.dll" "$outputRoot/SDL2.dll"
} finally {Pop-Location}
$vfEngineIdentityAfter=& python "$PSScriptRoot/build_release.py" --engine-identity
if ($LASTEXITCODE -ne 0 -or $vfEngineIdentityAfter -ne $vfEngineIdentity) { throw 'Engine sources changed during compilation; candidate was not published.' }
$binaryHashes=@{}
foreach($binaryName in @('xash3d.exe','xash.dll','xash.exe','ref_gl.dll','SDL2.dll')) {
    $binaryHashes[$binaryName]=(Get-FileHash (Join-Path $outputRoot $binaryName) -Algorithm SHA256).Hash
}
@{base_commit=$revision;built_utc=[DateTime]::UtcNow.ToString('o');architecture='win32-i386';
  engine_source_identity=$vfEngineIdentity;extension_version=4;player_pose_version=1;melee_pose_version=1;headgear_renderer_version=1;status_viewmodel_version=1;traversal_renderer_version=2;body_renderer_version=2;patch_sha256=(Get-FileHash $patchFile -Algorithm SHA256).Hash;
  player_pose_sha256=(Get-FileHash "$PSScriptRoot/engine/vf_player_pose.inc" -Algorithm SHA256).Hash;
  player_collision_sha256=(Get-FileHash "$PSScriptRoot/engine/sv_vf_pose.inc" -Algorithm SHA256).Hash;
  body_patch_sha256=(Get-FileHash (Join-Path $PSScriptRoot 'engine/first-person-body.patch') -Algorithm SHA256).Hash;
  renderer_sha256=(Get-FileHash "$PSScriptRoot/engine/gl_vf.inc" -Algorithm SHA256).Hash;
  headgear_renderer_sha256=(Get-FileHash "$PSScriptRoot/engine/gl_vf_headgear.inc" -Algorithm SHA256).Hash;
  performance_profiler_version=1;performance_sha256=(Get-FileHash "$PSScriptRoot/engine/gl_vf_perf.inc" -Algorithm SHA256).Hash;
  performance_patch_sha256=(Get-FileHash "$PSScriptRoot/engine/performance.patch" -Algorithm SHA256).Hash;
  headgear_policy_sha256=(Get-FileHash "$projectRoot/game_shared/vf_headgear.h" -Algorithm SHA256).Hash;
  binaries=$binaryHashes} | ConvertTo-Json -Depth 3 | Set-Content "$outputRoot/vector-engine-build.json" -Encoding utf8
Write-Output "Native engine built: $outputRoot"
