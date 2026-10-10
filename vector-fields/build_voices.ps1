$ErrorActionPreference='Stop'
$vfRoot=$PSScriptRoot
$repoRoot=Split-Path -Parent $vfRoot
& python "$vfRoot/build_effects.py"
if ($LASTEXITCODE -ne 0) { throw 'Effect catalog generation failed.' }
& python "$vfRoot/death_voice_workshop.py" build --ensure
if ($LASTEXITCODE -ne 0) { throw 'Death voice asset generation failed.' }
& python "$vfRoot/voice_workshop.py" build
if ($LASTEXITCODE -ne 0) { throw 'Voice asset generation failed.' }
$vswherePath=Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) 'Microsoft Visual Studio/Installer/vswhere.exe'
$vsRoot=& $vswherePath -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (!$vsRoot) { throw 'C++ tools unavailable.' }
$msbuildExe=Join-Path $vsRoot 'MSBuild/Current/Bin/MSBuild.exe'
Push-Location $repoRoot
try {
  foreach ($part in @(@{Name='server';Project='hldll'},@{Name='client';Project='hl_cdll'})) {
    & $msbuildExe "projects/vs2019/$($part.Project).vcxproj" /t:Build /m /nologo /v:quiet /clp:ErrorsOnly /p:Configuration=Release /p:Platform=Win32 /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0.22000.0 /p:PostBuildEventUseInBuild=false "/p:OutDir=$vfRoot/build/voices/$($part.Name)/" "/p:IntDir=$vfRoot/build/voices/obj-$($part.Name)/" /fl "/flp:logfile=$vfRoot/build/voices-$($part.Name).log;verbosity=normal"
    if ($LASTEXITCODE -ne 0) { throw "Voice build failed: $($part.Name)" }
    Write-Output "PASS voice build $($part.Name)"
  }
  $vcvars=Join-Path $vsRoot 'VC/Auxiliary/Build/vcvarsall.bat'
  $compileCommand='call "'+$vcvars+'" x86 >nul && cl.exe /nologo /EHsc /MT /W4 vector-fields/tests/voice_policy_test.cpp /Fovector-fields/build/voices/ /Fevector-fields/build/voices/voice-policy-test.exe'
  & $env:ComSpec /d /c $compileCommand
  if ($LASTEXITCODE -ne 0) { throw 'Voice policy compilation failed.' }
  & "$vfRoot/build/voices/voice-policy-test.exe"
  if ($LASTEXITCODE -ne 0) { throw 'Voice policy failed.' }
} finally { Pop-Location }

