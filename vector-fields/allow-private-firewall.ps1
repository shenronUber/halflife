#Requires -RunAsAdministrator
# This script changes only inbound rules for the two installed game executables.
param()
$ErrorActionPreference = 'Stop'
$vfProjectRoot = Split-Path -Parent $PSScriptRoot
$vfAuditDirectory = Join-Path $PSScriptRoot 'build/firewall-permissions'
New-Item -ItemType Directory -Path $vfAuditDirectory -Force | Out-Null
$vfResultPath = Join-Path $vfAuditDirectory 'result.json'
$vfBackupPath = Join-Path $vfAuditDirectory ('before-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
$vfTargets = @(
    @{ Name = 'VectorFields-Xash3D-Private-In'; File = 'xash3d.exe'; Label = 'Vector Fields - Xash3D (private)' },
    @{ Name = 'VectorFields-XashDedicated-Private-In'; File = 'xash.exe'; Label = 'Vector Fields - Dedicated server (private)' }
)

try {
    $vfPrograms = @(foreach ($vfTarget in $vfTargets) {
        $vfProgram = Join-Path $vfProjectRoot ('runtime/vector-engine/' + $vfTarget.File)
        if (!(Test-Path -LiteralPath $vfProgram -PathType Leaf)) {
            throw ('Missing installed executable: ' + $vfProgram)
        }
        $vfTarget.Program = [IO.Path]::GetFullPath($vfProgram)
        $vfTarget.Program
    })

    foreach ($vfTarget in $vfTargets) {
        $vfNamedRule = Get-NetFirewallRule -PolicyStore PersistentStore -Name $vfTarget.Name -ErrorAction SilentlyContinue
        if ($vfNamedRule -and ($vfNamedRule | Get-NetFirewallApplicationFilter).Program -ne $vfTarget.Program) {
            throw ('Rule name belongs to a different program: ' + $vfTarget.Name)
        }
    }

    # Record existing local rules before changing their profiles or enabled state.
    $vfExisting = @(Get-NetFirewallApplicationFilter -PolicyStore PersistentStore |
        Where-Object { $_.Program -in $vfPrograms } |
        ForEach-Object {
            $vfFilter = $_
            Get-NetFirewallRule -AssociatedNetFirewallApplicationFilter $vfFilter |
                Where-Object { $_.Direction -eq 'Inbound' } |
                Select-Object Name, DisplayName, Enabled, Direction, Action, Profile,
                    @{ Name = 'Program'; Expression = { $vfFilter.Program } }
        })
    [pscustomobject]@{ CreatedUtc = [DateTime]::UtcNow.ToString('o'); Rules = $vfExisting } |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $vfBackupPath -Encoding UTF8

    foreach ($vfRule in $vfExisting) {
        if ($vfRule.Action -eq 'Allow') {
            # Existing automatic exceptions must not keep granting public access.
            Set-NetFirewallRule -PolicyStore PersistentStore -Name $vfRule.Name -Profile Private | Out-Null
        } elseif ($vfRule.Action -eq 'Block') {
            # A previous Cancel can leave a block that overrides our new allow.
            # Retain that block on Domain/Public, removing only its Private scope.
            $vfProfileMask = [int]$vfRule.Profile
            if ($vfProfileMask -eq 0) { $vfProfileMask = 7 }
            if (($vfProfileMask -band 2) -ne 0) {
                $vfRetained = @()
                if (($vfProfileMask -band 1) -ne 0) { $vfRetained += 'Domain' }
                if (($vfProfileMask -band 4) -ne 0) { $vfRetained += 'Public' }
                if ($vfRetained.Count) {
                    Set-NetFirewallRule -PolicyStore PersistentStore -Name $vfRule.Name -Profile $vfRetained | Out-Null
                } else {
                    Set-NetFirewallRule -PolicyStore PersistentStore -Name $vfRule.Name -Enabled False | Out-Null
                }
            }
        }
    }

    foreach ($vfTarget in $vfTargets) {
        $vfRule = Get-NetFirewallRule -PolicyStore PersistentStore -Name $vfTarget.Name -ErrorAction SilentlyContinue
        if ($vfRule) {
            # Replace only our own named rule so an earlier run cannot leave extra restrictions.
            $vfOldProgram = ($vfRule | Get-NetFirewallApplicationFilter).Program
            if ($vfOldProgram -ne $vfTarget.Program) {
                throw ('Rule name belongs to a different program: ' + $vfTarget.Name)
            }
            Remove-NetFirewallRule -PolicyStore PersistentStore -Name $vfTarget.Name
        }
        New-NetFirewallRule -PolicyStore PersistentStore -Name $vfTarget.Name `
            -DisplayName $vfTarget.Label -Group 'Vector Fields - Private network' `
            -Description 'Permanent inbound exception for the installed game; private networks only.' `
            -Program $vfTarget.Program -Direction Inbound -Action Allow `
            -Enabled True -Profile Private -Protocol Any | Out-Null
    }

    $vfVerified = @(foreach ($vfTarget in $vfTargets) {
        $vfRule = Get-NetFirewallRule -PolicyStore PersistentStore -Name $vfTarget.Name
        $vfProgram = ($vfRule | Get-NetFirewallApplicationFilter).Program
        if ($vfRule.Enabled -ne 'True' -or $vfRule.Direction -ne 'Inbound' -or
            $vfRule.Action -ne 'Allow' -or [int]$vfRule.Profile -ne 2 -or
            $vfProgram -ne $vfTarget.Program) {
            throw ('Firewall rule verification failed: ' + $vfTarget.Name)
        }
        [pscustomobject]@{
            Name = $vfRule.Name; Program = $vfProgram; Enabled = [string]$vfRule.Enabled
            Direction = [string]$vfRule.Direction; Action = [string]$vfRule.Action
            Profile = [string]$vfRule.Profile; PolicyStore = 'PersistentStore'
        }
    })
    [pscustomobject]@{ Success = $true; Rules = $vfVerified; Backup = $vfBackupPath } |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $vfResultPath -Encoding UTF8
    exit 0
} catch {
    [pscustomobject]@{ Success = $false; Error = $_.Exception.Message; Backup = $vfBackupPath } |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $vfResultPath -Encoding UTF8
    exit 1
}
