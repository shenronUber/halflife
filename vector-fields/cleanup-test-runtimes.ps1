param([switch]$Apply)
$ErrorActionPreference='Stop'
$projectPath=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$projectPrefix=$projectPath+[IO.Path]::DirectorySeparatorChar
$archivePath=Join-Path $PSScriptRoot 'build/retired-runtime-evidence'
$targets=@(
 'vector-fields/build/animation-native',
 'vector-fields/build/status-feedback-native',
 'vector-fields/build/weapon-fx-native',
 'runtime/vector-engine-death-validation',
 'runtime/vector-engine-respawn-validation','runtime/vector-engine-respawn-peer',
 'runtime/vector-engine-voice-validation','runtime/vector-engine-voice-peer',
 'runtime/vector-engine-status-validation','runtime/vector-engine-status-peer',
 'runtime/vector-engine-taunt-peer','runtime/vector-engine-bot-voice-validation',
 'runtime/vector-engine-peer','runtime/vector-engine-baseline'
)
# Recover only abandoned sessions from the maintained harness. A live Python
# owner is excluded even when it has not launched its game window yet.
$sessionsPath=Join-Path $PSScriptRoot 'build/native-sessions'
if (Test-Path -LiteralPath $sessionsPath) {
 foreach ($session in Get-ChildItem -LiteralPath $sessionsPath -Directory) {
  if ($session.Name -match '^(\d+)-[0-9a-f]{12}$') {
   $ownerId=[int]$Matches[1]
   if (!(Get-Process -Id $ownerId -ErrorAction SilentlyContinue)) {
    $targets+=('vector-fields/build/native-sessions/'+$session.Name)
   }
  }
 }
}
function Assert-WorkspacePath([string]$path) {
 $absolute=[IO.Path]::GetFullPath($path)
 if (!$absolute.StartsWith($projectPrefix,[StringComparison]::OrdinalIgnoreCase)) {throw "Path escaped project: $absolute"}
 if (Test-Path -LiteralPath $absolute) {
  $resolved=(Resolve-Path -LiteralPath $absolute).Path
  if (!$resolved.StartsWith($projectPrefix,[StringComparison]::OrdinalIgnoreCase)) {throw "Resolved path escaped project: $resolved"}
  $item=Get-Item -LiteralPath $absolute -Force
  if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw "Reparse point cannot be cleaned: $absolute"}
 }
 return $absolute
}
$liveGames=@(Get-Process xash3d,xash,hl -ErrorAction SilentlyContinue)
if ($Apply -and $liveGames.Count) {throw 'A game engine is still running. No runtime cleanup was performed.'}
$disk=New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($projectPath))
$freeBefore=$disk.AvailableFreeSpace
$records=@()
$proofExtensions=@('.png','.jpg','.jpeg','.bmp','.tga','.gif','.mp4','.mkv','.webm','.avi',
 '.log','.json','.txt','.cfg','.sav','.blend','.smd','.qc','.map','.py','.ps1','.js','.cjs','.cpp','.c','.h','.html','.md')
foreach ($relative in $targets) {
 $target=Assert-WorkspacePath (Join-Path $projectPath $relative)
 if (!(Test-Path -LiteralPath $target)) {continue}
 # These allowlisted trees contain test engines only. Tracked sources cannot
 # be deleted, even if somebody accidentally put one in an old test folder.
 $tracked=@(& git -c "safe.directory=$($projectPath.Replace('\','/'))" -C $projectPath ls-files -- $relative)
 if ($LASTEXITCODE -ne 0 -or $tracked.Count) {throw "Tracked content or Git check failed in $target"}
 Write-Output "Inspecting $relative"
 $logicalBytes=0L;$preservedBytes=0L;$preservedFiles=0
 Get-ChildItem -LiteralPath $target -Recurse -Force | ForEach-Object {
  $item=$_
  if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw "Link found inside runtime: $($item.FullName)"}
  if ($item.PSIsContainer) {return}
  $logicalBytes+=$item.Length
  $tail=$item.FullName.Substring($target.Length+1).Replace('\','/')
  $parts=$tail.Split('/')
  $fallback=if ($relative.StartsWith('vector-fields/build/')) {$parts.Length -gt 2 -and $parts[1] -in @('valve','tfc_assets','cs_assets','vf_visual')} else {$parts[0] -in @('tfc_assets','cs_assets')}
  if ($fallback -or $tail.Contains('/.fontcache/') -or $item.Extension.ToLowerInvariant() -notin $proofExtensions) {return}
  $preservedBytes+=$item.Length;$preservedFiles++
  if ($Apply) {
   $destination=Assert-WorkspacePath (Join-Path $archivePath ($relative+'/'+$tail))
   $source=Assert-WorkspacePath $item.FullName
   if (Test-Path -LiteralPath $destination) {throw "Evidence archive already exists: $destination"}
   New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
   Move-Item -LiteralPath $source -Destination $destination
  }
 }
 if ($Apply) {
  # Validate the final absolute target again immediately before recursive delete.
  $target=Assert-WorkspacePath $target
  Remove-Item -LiteralPath $target -Recurse -Force
 }
 $records+=@{path=$relative;logical_bytes=$logicalBytes;preserved_bytes=$preservedBytes;preserved_files=$preservedFiles;removed=[bool]$Apply}
 Write-Output "$relative : $preservedFiles proof/source files preserved; removed=$Apply"
}
$report=@{applied=[bool]$Apply;free_before=$freeBefore;free_after=$disk.AvailableFreeSpace;freed_bytes=($disk.AvailableFreeSpace-$freeBefore);targets=$records;archive=$archivePath;utc=[DateTime]::UtcNow.ToString('o')}
New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot 'build') -Force | Out-Null
$reportName=if ($Apply) {'runtime-cleanup.json'} else {'runtime-cleanup-preview.json'}
$report | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $PSScriptRoot ('build/'+$reportName)) -Encoding utf8
Write-Output ("Freed on disk: {0:N2} GB" -f ($report.freed_bytes/1e9))
