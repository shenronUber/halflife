param([ValidateSet('first-person','third-person')][string]$View='first-person', [switch]$PosesCorrigees, [switch]$PriseReference, [switch]$RevueComplete, [switch]$Franchissements, [switch]$SautMural)
$ErrorActionPreference='Stop'
$vfAnimationRoot=Split-Path -Parent $PSScriptRoot
$vfProjectRoot=Split-Path -Parent $vfAnimationRoot
$vfBlenderRoot=Join-Path $vfProjectRoot 'devtools/blender'
$vfInstallation=Get-Content (Join-Path $vfBlenderRoot 'installation.json') -Raw | ConvertFrom-Json
$vfEditor=$vfInstallation.executable
$vfFileName=if ($View -eq 'first-person') {'Mains-R1.blend'} else {'Corps-R1.blend'}
if ($PosesCorrigees) {
 if ($View -ne 'first-person') {throw 'La revision de posture concerne actuellement les mains.'}
 $vfFileName='Mains-R1-poses-corrigees.blend'
 if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'traversal/blender/Mains-R1-pouces-corriges.blend')) {$vfFileName='Mains-R1-pouces-corriges.blend'}
}
if ($PriseReference) {
 if ($View -ne 'first-person') {throw 'La prise de reference concerne les mains.'}
 $vfFileName='Mains-R1-prise-reference.blend'
}
if ($RevueComplete) {$vfFileName=if($View -eq 'first-person'){'Mains-R1-revue-complete.blend'}else{'Corps-R1-revue-complete.blend'}}
if ($Franchissements) {$vfFileName=if($View -eq 'first-person'){'Mains-R1-franchissements-revus.blend'}else{'Corps-R1-franchissements-revus.blend'}}
if ($SautMural) {$vfFileName=if($View -eq 'first-person'){'Mains-R1-saut-mural.blend'}else{'Corps-R1-saut-mural.blend'}}
$vfWorkshop=Join-Path $PSScriptRoot ('traversal/blender/'+$vfFileName)
if (!(Test-Path -LiteralPath $vfEditor)) {throw 'Blender est absent du dossier devtools/blender.'}
if (!(Test-Path -LiteralPath $vfWorkshop)) {throw 'Le projet Blender doit etre prepare avant son ouverture.'}
$env:BLENDER_USER_CONFIG=Join-Path $vfBlenderRoot 'profile/config'
$env:BLENDER_USER_SCRIPTS=Join-Path $vfBlenderRoot 'profile/scripts'
$env:BLENDER_USER_DATAFILES=Join-Path $vfBlenderRoot 'profile/datafiles'
$vfArguments='"'+$vfWorkshop+'"'
if ($PriseReference) {
 $vfArguments+=' --python "'+(Join-Path $PSScriptRoot 'blender-reference-layout.py')+'"'
}
Start-Process -FilePath $vfEditor -ArgumentList $vfArguments -WorkingDirectory (Split-Path -Parent $vfWorkshop) -WindowStyle Normal
