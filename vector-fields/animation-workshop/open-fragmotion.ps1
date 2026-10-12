param([ValidateSet('first-person','third-person')][string]$View='first-person')
$ErrorActionPreference='Stop'
$vfAnimationRoot=Split-Path -Parent $PSScriptRoot
$vfProjectRoot=Split-Path -Parent $vfAnimationRoot
$vfEditor=Join-Path $vfProjectRoot 'devtools/fragmotion/app/fragMOTION.exe'
$vfWorkshop=Join-Path $PSScriptRoot "traversal/$View/atelier.smd"
if (!(Test-Path -LiteralPath $vfEditor)) {throw 'fragMOTION est absent du dossier devtools/fragmotion/app.'}
if (!(Test-Path -LiteralPath $vfWorkshop)) {
 & python (Join-Path $vfAnimationRoot 'traversal_editor.py') export
 if ($LASTEXITCODE -ne 0) {throw 'Preparation de l atelier impossible.'}
}
Start-Process -FilePath $vfEditor -ArgumentList ('"'+$vfWorkshop+'"') -WorkingDirectory (Split-Path -Parent $vfWorkshop) -WindowStyle Normal
