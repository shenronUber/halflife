param(
    [string]$ValveDir = 'F:/SteamLibrary/steamapps/common/Half-Life/valve',
    [string]$MSBuild = 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/MSBuild/Current/Bin/MSBuild.exe',
    [string]$MapToolDir = (Join-Path $PSScriptRoot 'sdhlt/sdhlt-v1.3.0/tools/Win64')
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent

# SDHLT v1.3.0 is downloaded from its official release and extracted locally:
# https://github.com/seedee/SDHLT/releases/tag/v1.3.0
# No installation or writes to the Steam library are performed by this script.
foreach ($stage in @('CSG','BSP','VIS','RAD')) {
    if (-not (Test-Path -LiteralPath (Join-Path $MapToolDir "sdHL${stage}_x64.exe"))) {
        throw "Missing SDHLT compiler in $MapToolDir"
    }
}

& $MSBuild (Join-Path $repo 'projects/vs2010/studiomdl.vcxproj') /t:Build /m /nologo /v:quiet /clp:ErrorsOnly /p:Configuration=Release /p:Platform=Win32 /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0.22000.0 "/p:OutDir=$PSScriptRoot/tools/" "/p:IntDir=$PSScriptRoot/obj-studiomdl/" /fl "/flp:logfile=$PSScriptRoot/studiomdl-build.log;verbosity=normal"
if ($LASTEXITCODE -ne 0) { throw 'StudioMDL build failed' }
& python (Join-Path $PSScriptRoot 'generate_assets.py') --valve $ValveDir
if ($LASTEXITCODE -ne 0) { throw 'Asset generation failed' }
Push-Location -LiteralPath (Join-Path $PSScriptRoot 'generated')
try {
    & (Join-Path $PSScriptRoot 'tools/studiomdl.exe') vf_modular.qc > (Join-Path $PSScriptRoot 'model-build.log')
    if ($LASTEXITCODE -ne 0) { throw 'Model compile failed' }
    foreach ($stage in @('CSG','BSP','VIS','RAD')) {
        $arguments = @('-threads','2')
        if ($stage -eq 'CSG') { $arguments += @('-wadinclude','halflife.wad') }
        $arguments += 'vf_asset_lab'
        & (Join-Path $MapToolDir "sdHL${stage}_x64.exe") @arguments > (Join-Path $PSScriptRoot ($stage.ToLower() + '-build.log'))
        if ($LASTEXITCODE -ne 0) { throw "Map compile failed at $stage" }
    }
} finally {
    Pop-Location
}
& python (Join-Path $PSScriptRoot 'verify_outputs.py')
if ($LASTEXITCODE -ne 0) { throw 'Output validation failed' }
