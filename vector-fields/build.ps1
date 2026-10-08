param([string]$PlatformToolset='v143',[string]$WindowsSdkVersion='10.0.22000.0')
$ErrorActionPreference='Stop'
$vfRoot=$PSScriptRoot
$repoRoot=Split-Path -Parent $vfRoot
$vswherePath=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vsRoot=& $vswherePath -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsRoot) { throw 'Visual Studio C++ build tools were not found.' }
$msbuildExe=Join-Path $vsRoot 'MSBuild/Current/Bin/MSBuild.exe'
New-Item -ItemType Directory -Path "$vfRoot/build" -Force | Out-Null
if (!(Test-Path "$vfRoot/generated/ui/ui_font.spr") -or !(Test-Path "$repoRoot/cl_dll/vf_ui_font.h")) {
    & python "$vfRoot/build_ui.py"
    if ($LASTEXITCODE -ne 0) { throw 'UI atlas generation failed.' }
}
if (!(Test-Path "$vfRoot/generated/equipment_visuals/eq_optic.mdl")) {
    & python "$vfRoot/build_equipment_visuals.py"
    if ($LASTEXITCODE -ne 0) { throw 'Equipment asset generation failed.' }
}
& python "$vfRoot/build_reference_weapon.py" --ensure
if ($LASTEXITCODE -ne 0) { throw 'Reference weapon generation failed.' }
& python "$vfRoot/build_personas.py" --ensure
if ($LASTEXITCODE -ne 0) { throw 'GIGN character generation failed.' }
& python "$vfRoot/build_effects.py"
if ($LASTEXITCODE -ne 0) { throw 'Effect catalog generation failed.' }
Push-Location $repoRoot
try {
    foreach ($part in @(@{Name='server';Project='hldll'},@{Name='client';Project='hl_cdll'})) {
        & $msbuildExe "projects/vs2019/$($part.Project).vcxproj" /t:Build /m /nologo /v:quiet /clp:ErrorsOnly `
            /p:Configuration=Release /p:Platform=Win32 "/p:PlatformToolset=$PlatformToolset" `
            "/p:WindowsTargetPlatformVersion=$WindowsSdkVersion" /p:PostBuildEventUseInBuild=false `
            "/p:OutDir=$vfRoot/build/$($part.Name)/" "/p:IntDir=$vfRoot/build/obj-$($part.Name)/" `
            /fl "/flp:logfile=$vfRoot/build/$($part.Name).log;verbosity=normal"
        if ($LASTEXITCODE -ne 0) { throw "Build failed: $($part.Name)" }
    }
    $vcvars=Join-Path $vsRoot 'VC/Auxiliary/Build/vcvarsall.bat'
    $compileCommand='call "'+$vcvars+'" x86 >nul && cl.exe /nologo /EHsc /MT /W4 vector-fields/tests/loadout_test.cpp game_shared/vf_loadout.cpp game_shared/vf_appearance.cpp /Fovector-fields/build/ /Fevector-fields/build/loadout-test.exe'
    & $env:ComSpec /d /c $compileCommand *> "$vfRoot/build/tests-build.log"
    if ($LASTEXITCODE -ne 0) { throw 'Test compilation failed.' }
    & "$vfRoot/build/loadout-test.exe" "$vfRoot/data/equipment.txt" "$vfRoot/generated/visual_skins/skins.txt" "$vfRoot/generated/skins/arsenal.txt" | Tee-Object -FilePath "$vfRoot/build/tests-result.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Loadout checks failed.' }
    $effectsCompile='call "'+$vcvars+'" x86 >nul && cl.exe /nologo /EHsc /MT /W4 vector-fields/tests/effects_test.cpp /Fovector-fields/build/ /Fevector-fields/build/effects-test.exe'
    & $env:ComSpec /d /c $effectsCompile *> "$vfRoot/build/effects-tests-build.log"
    if ($LASTEXITCODE -ne 0) { throw 'Effect test compilation failed.' }
    & "$vfRoot/build/effects-test.exe" | Tee-Object -FilePath "$vfRoot/build/effects-tests-result.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Effect tests failed.' }

} finally { Pop-Location }
