param([string]$PlatformToolset='v143',[string]$WindowsSdkVersion='10.0.22000.0')
$ErrorActionPreference='Stop'
$vfRoot=$PSScriptRoot
$repoRoot=Split-Path -Parent $vfRoot
& python "$vfRoot/model_contract.py"
if ($LASTEXITCODE -ne 0) { throw "Model contract generation failed." }
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
& python "$vfRoot/build_first_person.py" --ensure
if ($LASTEXITCODE -ne 0) { throw 'First-person glove and sleeve generation failed.' }
& python "$vfRoot/build_personas.py" --ensure
if ($LASTEXITCODE -ne 0) { throw 'GIGN character generation failed.' }
& python "$vfRoot/build_death_sounds.py" --ensure
if ($LASTEXITCODE -ne 0) { throw 'Death sound assets are incomplete.' }
& python "$vfRoot/build_deaths.py" --ensure
if ($LASTEXITCODE -ne 0) { throw 'Death asset generation failed.' }
& python "$vfRoot/third_person.py" --ensure
if ($LASTEXITCODE -ne 0) { throw 'Third-person arm and weapon generation failed.' }
& python "$vfRoot/build_materials.py"
if ($LASTEXITCODE -ne 0) { throw 'Combat material generation failed.' }
& python "$vfRoot/build_lootpool.py"
if ($LASTEXITCODE -ne 0) { throw 'Gameplay lootpool generation failed.' }
& python "$vfRoot/build_effects.py"
if ($LASTEXITCODE -ne 0) { throw 'Effect catalog generation failed.' }
& python "$vfRoot/build_status_decals.py" --ensure
if ($LASTEXITCODE -ne 0) { throw 'Custom HUD decal generation failed.' }
& python "$vfRoot/build_test_room.py" --ensure
if ($LASTEXITCODE -ne 0) { throw 'GIGN test room generation failed.' }
& python "$vfRoot/build_weapon_fx_range.py"
if ($LASTEXITCODE -ne 0) { throw 'Weapon FX range generation failed.' }
& python "$vfRoot/build_weapon_fx.py"
if ($LASTEXITCODE -ne 0) { throw 'Weapon VFX generation failed.' }
& python "$vfRoot/death_voice_workshop.py" build --ensure
if ($LASTEXITCODE -ne 0) { throw 'Death voice asset generation failed.' }
& python "$vfRoot/voice_workshop.py" build
if ($LASTEXITCODE -ne 0) { throw 'Operator voice assets are incomplete.' }
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
    $architectureCompile='call "'+$vcvars+'" x86 >nul && cl.exe /nologo /EHsc /MT /W4 vector-fields/tests/architecture_test.cpp game_shared/vf_loadout.cpp game_shared/vf_appearance.cpp /Fovector-fields/build/ /Fevector-fields/build/architecture-test.exe'
    & $env:ComSpec /d /c $architectureCompile *> "$vfRoot/build/architecture-tests-build.log"
    if ($LASTEXITCODE -ne 0) { throw 'Architecture test compilation failed.' }
    & "$vfRoot/build/architecture-test.exe" "$vfRoot/data/equipment.txt" "$vfRoot/data/r01_styles.txt" "$vfRoot/generated/visual_skins/skins.txt" | Tee-Object -FilePath "$vfRoot/build/architecture-tests-result.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Architecture checks failed.' }
    $effectsCompile='call "'+$vcvars+'" x86 >nul && cl.exe /nologo /EHsc /MT /W4 vector-fields/tests/effects_test.cpp /Fovector-fields/build/ /Fevector-fields/build/effects-test.exe'
    & $env:ComSpec /d /c $effectsCompile *> "$vfRoot/build/effects-tests-build.log"
    if ($LASTEXITCODE -ne 0) { throw 'Effect test compilation failed.' }
    & "$vfRoot/build/effects-test.exe" | Tee-Object -FilePath "$vfRoot/build/effects-tests-result.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Effect tests failed.' }
    $voiceCompile='call "'+$vcvars+'" x86 >nul && cl.exe /nologo /EHsc /MT /W4 vector-fields/tests/voice_policy_test.cpp /Fovector-fields/build/ /Fevector-fields/build/voice-policy-test.exe'
    & $env:ComSpec /d /c $voiceCompile *> "$vfRoot/build/voice-tests-build.log"
    if ($LASTEXITCODE -ne 0) { throw 'Voice and status test compilation failed.' }
    & "$vfRoot/build/voice-policy-test.exe" | Tee-Object -FilePath "$vfRoot/build/voice-tests-result.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Voice and status policy tests failed.' }
    $combatCompile='call "'+$vcvars+'" x86 >nul && cl.exe /nologo /EHsc /MT /W4 vector-fields/tests/combat_policy_test.cpp /Fovector-fields/build/ /Fevector-fields/build/combat-policy-test.exe'
    & $env:ComSpec /d /c $combatCompile *> "$vfRoot/build/combat-tests-build.log"
    if ($LASTEXITCODE -ne 0) { throw 'Combat policy test compilation failed.' }
    & "$vfRoot/build/combat-policy-test.exe" | Tee-Object -FilePath "$vfRoot/build/combat-tests-result.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Combat policy tests failed.' }
    $procCompile='call "'+$vcvars+'" x86 >nul && cl.exe /nologo /EHsc /MT /W4 vector-fields/tests/proc_policy_test.cpp /Fovector-fields/build/ /Fevector-fields/build/proc-policy-test.exe'
    & $env:ComSpec /d /c $procCompile *> "$vfRoot/build/proc-tests-build.log"
    if ($LASTEXITCODE -ne 0) { throw 'Proc policy test compilation failed.' }
    & "$vfRoot/build/proc-policy-test.exe"
    if ($LASTEXITCODE -ne 0) { throw 'Proc policy checks failed.' }
    $fragmentCompile='call "'+$vcvars+'" x86 >nul && cl.exe /nologo /EHsc /MT /W4 vector-fields/tests/fragment_finish_policy_test.cpp /Fovector-fields/build/ /Fevector-fields/build/fragment-finish-policy-test.exe'
    & $env:ComSpec /d /c $fragmentCompile *> "$vfRoot/build/fragment-finish-tests-build.log"
    if ($LASTEXITCODE -ne 0) { throw 'Fragment finish policy compilation failed.' }
    & "$vfRoot/build/fragment-finish-policy-test.exe"
    if ($LASTEXITCODE -ne 0) { throw 'Fragment finish policy checks failed.' }
    & python "$vfRoot/validate.py" --suite unit --suite assets
    if ($LASTEXITCODE -ne 0) { throw 'Unit or generated asset checks failed.' }

} finally { Pop-Location }
