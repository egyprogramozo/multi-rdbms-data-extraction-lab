$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ConfigPath = Join-Path $ProjectRoot "config\.env"
$BaselineDir = Join-Path $ProjectRoot "manual_csv_filedrop_baseline"
$WorkingDir = Join-Path $ProjectRoot "manual_csv_filedrop"
$LogsDir = Join-Path $ProjectRoot "logs"
$PythonExe = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$Extractor = Join-Path $ProjectRoot "src\check_manual_csv_source.py"

New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
$SeriesTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$SeriesLogPath = Join-Path $LogsDir "manual_csv_test_series_$SeriesTimestamp.log"
$OriginalEnvContent = Get-Content -LiteralPath $ConfigPath -Raw
$Results = New-Object System.Collections.Generic.List[object]

function Write-SeriesLog {
    param([string]$Message)
    Add-Content -LiteralPath $SeriesLogPath -Value $Message -Encoding UTF8
}

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Content
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Reset-WorkingSource {
    if (-not (Test-Path -LiteralPath $BaselineDir -PathType Container)) {
        throw "Baseline directory does not exist: $BaselineDir"
    }

    if (-not (Test-Path -LiteralPath $WorkingDir -PathType Container)) {
        New-Item -ItemType Directory -Path $WorkingDir -Force | Out-Null
    }

    Get-ChildItem -LiteralPath $WorkingDir -Filter "*.csv" -File |
        Remove-Item -Force
    Get-ChildItem -LiteralPath $BaselineDir -Filter "*.csv" -File |
        Copy-Item -Destination $WorkingDir -Force
}

function Set-EnvForTest {
    param([string]$EffDat)

    $lines = Get-Content -LiteralPath $ConfigPath
    $updated = foreach ($line in $lines) {
        if ($line -match "^EFF_DAT=") {
            "EFF_DAT=$EffDat"
        } elseif ($line -match "^MANUAL_CSV_SOURCE_DIR=") {
            "MANUAL_CSV_SOURCE_DIR=manual_csv_filedrop"
        } else {
            $line
        }
    }
    Write-Utf8NoBom -Path $ConfigPath -Content (($updated -join [Environment]::NewLine) + [Environment]::NewLine)
}

function Get-FirstMatch {
    param(
        [string[]]$Lines,
        [string]$Pattern
    )

    foreach ($line in $Lines) {
        if ($line -match $Pattern) {
            return $Matches[1]
        }
    }
    return ""
}

function Invoke-ExtractionCase {
    param(
        [string]$TestId,
        [string]$EffDat,
        [string]$ExpectedStatus,
        [string]$ExpectedOutputAction,
        [scriptblock]$Manipulation,
        [string]$ManipulationDescription
    )

    $startTime = Get-Date -Format "o"
    Reset-WorkingSource
    Set-EnvForTest -EffDat $EffDat
    if ($Manipulation) {
        & $Manipulation
    }

    Push-Location $ProjectRoot
    try {
        $previousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $consoleLines = & $PythonExe .\src\check_manual_csv_source.py 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
        Pop-Location
    }

    $consoleText = ($consoleLines | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
    $actualStatus = Get-FirstMatch -Lines $consoleLines -Pattern "^Validation status:\s*(.+)$"
    $outputAction = Get-FirstMatch -Lines $consoleLines -Pattern "^Output action:\s*(.+)$"
    $extractionLogPath = Get-FirstMatch -Lines $consoleLines -Pattern "^Log file:\s*(.+)$"

    $statusMatches = $actualStatus -eq $ExpectedStatus
    $outputActionMatches = [string]::IsNullOrWhiteSpace($ExpectedOutputAction) -or $outputAction -eq $ExpectedOutputAction
    $result = if ($statusMatches -and $outputActionMatches) { "PASS" } else { "CHECK" }

    $Results.Add([pscustomobject]@{
        test_id = $TestId
        EFF_DAT = $EffDat
        expected_status = $ExpectedStatus
        actual_status = $actualStatus
        output_action = $outputAction
        exit_code = $exitCode
        result = $result
    }) | Out-Null

    Write-SeriesLog "==== $TestId ===="
    Write-SeriesLog "start_time=$startTime"
    Write-SeriesLog "source_manipulation=$ManipulationDescription"
    Write-SeriesLog "EFF_DAT=$EffDat"
    Write-SeriesLog "expected_status=$ExpectedStatus"
    Write-SeriesLog "expected_output_action=$ExpectedOutputAction"
    Write-SeriesLog "exit_code=$exitCode"
    Write-SeriesLog "actual_status=$actualStatus"
    Write-SeriesLog "output_action=$outputAction"
    Write-SeriesLog "extraction_log_path=$extractionLogPath"
    Write-SeriesLog "console_output_begin"
    Write-SeriesLog $consoleText
    Write-SeriesLog "console_output_end"
    Write-SeriesLog "result=$result"
    Write-SeriesLog ""
}

Write-SeriesLog "manual_csv_test_series_start=$(Get-Date -Format "o")"
Write-SeriesLog "project_root=$ProjectRoot"
Write-SeriesLog "baseline_dir=$BaselineDir"
Write-SeriesLog "working_dir=$WorkingDir"
Write-SeriesLog ""

try {
    Invoke-ExtractionCase `
        -TestId "T01_SUCCESS_WITH_ROWS_CREATED_OR_REPLACED" `
        -EffDat "2026-06-16" `
        -ExpectedStatus "SUCCESS_WITH_ROWS" `
        -ExpectedOutputAction "" `
        -Manipulation $null `
        -ManipulationDescription "Reset working source from baseline."

    Invoke-ExtractionCase `
        -TestId "T02_SUCCESS_WITH_ROWS_REPLACED_EXISTING" `
        -EffDat "2026-06-16" `
        -ExpectedStatus "SUCCESS_WITH_ROWS" `
        -ExpectedOutputAction "REPLACED_EXISTING_FILE" `
        -Manipulation {
            Add-Content -LiteralPath (Join-Path $WorkingDir "site06_orders_manual_export_2026-06-16.csv") -Value "9,1,2026-06-16,1990.00,PAID,2026-06-16,2026-06-16 17:30:00" -Encoding UTF8
        } `
        -ManipulationDescription "Appended one valid extra data row to 2026-06-16 orders file."

    Invoke-ExtractionCase `
        -TestId "T03_FAILED_MISSING_DAILY_ORDERS_FILE" `
        -EffDat "2026-06-17" `
        -ExpectedStatus "FAILED_MISSING_FILE" `
        -ExpectedOutputAction "" `
        -Manipulation {
            Remove-Item -LiteralPath (Join-Path $WorkingDir "site06_orders_manual_export_2026-06-17.csv") -Force
        } `
        -ManipulationDescription "Deleted 2026-06-17 daily orders file from working source."

    Invoke-ExtractionCase `
        -TestId "T04_FAILED_MISSING_CUSTOMER_SNAPSHOT" `
        -EffDat "2026-06-16" `
        -ExpectedStatus "FAILED_MISSING_FILE" `
        -ExpectedOutputAction "" `
        -Manipulation {
            Remove-Item -LiteralPath (Join-Path $WorkingDir "site06_customers_manual_snapshot_2026-06-20.csv") -Force
        } `
        -ManipulationDescription "Deleted customer snapshot file from working source."

    Invoke-ExtractionCase `
        -TestId "T05_FAILED_TOO_OLD_CUSTOMER_SNAPSHOT" `
        -EffDat "2026-06-16" `
        -ExpectedStatus "FAILED_VALIDATION" `
        -ExpectedOutputAction "" `
        -Manipulation {
            Rename-Item -LiteralPath (Join-Path $WorkingDir "site06_customers_manual_snapshot_2026-06-20.csv") -NewName "site06_customers_manual_snapshot_2026-06-10.csv"
        } `
        -ManipulationDescription "Renamed customer snapshot from 2026-06-20 to 2026-06-10."

    Invoke-ExtractionCase `
        -TestId "T06_SUCCESS_EMPTY" `
        -EffDat "2026-06-18" `
        -ExpectedStatus "SUCCESS_EMPTY" `
        -ExpectedOutputAction "" `
        -Manipulation {
            Write-Utf8NoBom -Path (Join-Path $WorkingDir "site06_orders_manual_export_2026-06-18.csv") -Content ("order_id,customer_id,order_date,amount,status,eff_dat,last_update_at" + [Environment]::NewLine)
        } `
        -ManipulationDescription "Replaced 2026-06-18 orders file with header-only file."

    Invoke-ExtractionCase `
        -TestId "T07_FAILED_INVALID_ORDER_DATE" `
        -EffDat "2026-06-16" `
        -ExpectedStatus "FAILED_VALIDATION" `
        -ExpectedOutputAction "" `
        -Manipulation {
            $path = Join-Path $WorkingDir "site06_orders_manual_export_2026-06-16.csv"
            $lines = Get-Content -LiteralPath $path
            $fields = $lines[1].Split(",")
            $fields[2] = "2027-06-16"
            $lines[1] = $fields -join ","
            Write-Utf8NoBom -Path $path -Content (($lines -join [Environment]::NewLine) + [Environment]::NewLine)
        } `
        -ManipulationDescription "Changed one 2026-06-16 order_date to 2027-06-16."

    Invoke-ExtractionCase `
        -TestId "T08_OTHER_DATE_FILE_MISSING_DOES_NOT_BLOCK_CURRENT_EFF_DAT" `
        -EffDat "2026-06-18" `
        -ExpectedStatus "SUCCESS_WITH_ROWS" `
        -ExpectedOutputAction "" `
        -Manipulation {
            Remove-Item -LiteralPath (Join-Path $WorkingDir "site06_orders_manual_export_2026-06-17.csv") -Force
        } `
        -ManipulationDescription "Deleted unrelated 2026-06-17 daily orders file while running 2026-06-18."
} finally {
    Reset-WorkingSource
    Write-Utf8NoBom -Path $ConfigPath -Content $OriginalEnvContent
    Write-SeriesLog "manual_csv_test_series_end=$(Get-Date -Format "o")"
    Write-SeriesLog "restored_config_env=true"
    Write-SeriesLog "restored_working_source_from_baseline=true"
}

Write-Output "Test-series log file: $SeriesLogPath"
$Results | Format-Table -AutoSize
