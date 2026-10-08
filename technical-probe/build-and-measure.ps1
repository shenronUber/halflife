param(
    [string]$PlatformToolset = 'v143',
    [string]$WindowsSdkVersion = '10.0.22000.0'
)
$ErrorActionPreference = 'Stop'
$probeRoot = $PSScriptRoot
$repoRoot = Split-Path -Parent $probeRoot
$vswherePath = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vsRoot = & $vswherePath -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsRoot) { throw 'Visual Studio C++ build tools were not found.' }
$msbuildExe = Join-Path $vsRoot 'MSBuild/Current/Bin/MSBuild.exe'
Push-Location $repoRoot
try {
    foreach ($part in @(
        @{ Name = 'server'; Project = 'hldll' },
        @{ Name = 'client'; Project = 'hl_cdll' }
    )) {
        & $msbuildExe "projects/vs2019/$($part.Project).vcxproj" /t:Build /m /nologo /v:quiet /clp:ErrorsOnly `
            /p:Configuration=Release /p:Platform=Win32 "/p:PlatformToolset=$PlatformToolset" `
            "/p:WindowsTargetPlatformVersion=$WindowsSdkVersion" /p:PostBuildEventUseInBuild=false `
            "/p:OutDir=$probeRoot/$($part.Name)/" "/p:IntDir=$probeRoot/obj-$($part.Name)/" `
            /fl "/flp:logfile=$probeRoot/$($part.Name)-build.log;verbosity=normal"
        if ($LASTEXITCODE -ne 0) { throw "Build failed: $($part.Name). Read its build log." }
    }
    # Use the actual SDK movement objects. They are not copied into another engine.
    $vcvars = Join-Path $vsRoot 'VC/Auxiliary/Build/vcvarsall.bat'
    # Paths supplied by Visual Studio are quoted; the rest is fixed relative to repoRoot.
    $compileCommand = 'call "' + $vcvars + '" x86 >nul && cl.exe /nologo /MT /O2 /Gy /DWIN32 /Icommon /Ipm_shared /Ipublic technical-probe/movement_probe.c technical-probe/obj-server/pm_shared.obj technical-probe/obj-server/pm_math.obj technical-probe/obj-server/pm_debug.obj /Fotechnical-probe/movement_probe.obj /Fetechnical-probe/movement-probe.exe /link /OPT:REF /LTCG'
    & $env:ComSpec /d /c $compileCommand *> (Join-Path $probeRoot 'movement-build.log')
    if ($LASTEXITCODE -ne 0) { throw 'Movement harness build failed. Read movement-build.log.' }
    $measurements = & (Join-Path $probeRoot 'movement-probe.exe') 2> (Join-Path $probeRoot 'movement-run.log')
    $probeExit = $LASTEXITCODE
    $measurements | Set-Content -LiteralPath (Join-Path $probeRoot 'movement-results.csv') -Encoding utf8
    if ($probeExit -ne 0) { throw 'One or more movement measurements failed.' }
    Get-Content -LiteralPath (Join-Path $probeRoot 'movement-run.log')
    Write-Output "DLLs and measurements are in $probeRoot"
} finally {
    Pop-Location
}
