param([switch]$Publish)
$ErrorActionPreference='Stop'
$vfTaskRoot=$PSScriptRoot
$vfRepoRoot=Split-Path -Parent $vfTaskRoot
$vfVswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vfVsRoot=& $vfVswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$vfMsbuild=Join-Path $vfVsRoot 'MSBuild/Current/Bin/MSBuild.exe'
Push-Location $vfRepoRoot
try {
 foreach($vfPart in @(@{Name='client';Project='hl_cdll'},@{Name='server';Project='hldll'})) {
  $vfTaskOutput="$vfTaskRoot/build/headgear-action/$($vfPart.Name)/"
  & $vfMsbuild "projects/vs2019/$($vfPart.Project).vcxproj" /t:Build /m /nologo /v:quiet /clp:ErrorsOnly /p:Configuration=Release /p:Platform=Win32 /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0.22000.0 /p:PostBuildEventUseInBuild=false "/p:OutDir=$vfTaskOutput" "/p:IntDir=$vfTaskRoot/build/headgear-action/obj-$($vfPart.Name)/" /fl "/flp:logfile=$vfTaskRoot/build/headgear-action/$($vfPart.Name).log;verbosity=normal"
  if($LASTEXITCODE -ne 0){throw "Compilation failed: $($vfPart.Name)"}
 }
 if($Publish) {
  Copy-Item "$vfTaskRoot/build/headgear-action/client/client.dll" "$vfTaskRoot/build/client/client.dll"
  Copy-Item "$vfTaskRoot/build/headgear-action/server/hl.dll" "$vfTaskRoot/build/server/hl.dll"
 }
} finally {Pop-Location}
