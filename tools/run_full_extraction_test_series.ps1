$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ConfigPath = Join-Path $ProjectRoot "config\.env"
$LogsDir = Join-Path $ProjectRoot "logs"
$PythonExe = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$ManualScript = Join-Path $ProjectRoot "src\check_manual_csv_source.py"
$DatabaseScript = Join-Path $ProjectRoot "src\extract_database_sources.py"
$TestDates = @("2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-20")
$DatabaseSources = @("mssql", "oracle", "db2", "mysql", "postgresql")

New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
$SeriesTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$SeriesLogPath = Join-Path $LogsDir "full_extraction_test_series_$SeriesTimestamp.log"
$EnvBackupPath = Join-Path ([System.IO.Path]::GetTempPath()) "multi_rdbms_config_env_$SeriesTimestamp.bak"
$OriginalEnvContent = Get-Content -LiteralPath $ConfigPath -Raw
$OriginalEffDat = ""
$Results = New-Object System.Collections.Generic.List[object]
$Failures = New-Object System.Collections.Generic.List[string]
$EnvRestored = $false

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

function Get-EnvValueFromContent {
    param(
        [string]$Content,
        [string]$Name
    )

    foreach ($line in ($Content -split "`r?`n")) {
        if ($line -match "^$([regex]::Escape($Name))=(.*)$") {
            return $Matches[1]
        }
    }
    return ""
}

function Set-EnvValues {
    param([hashtable]$Values)

    $lines = Get-Content -LiteralPath $ConfigPath
    $updatedNames = New-Object System.Collections.Generic.HashSet[string]
    $updated = foreach ($line in $lines) {
        $matched = $false
        foreach ($key in $Values.Keys) {
            if ($line -match "^$([regex]::Escape($key))=") {
                "$key=$($Values[$key])"
                [void]$updatedNames.Add($key)
                $matched = $true
                break
            }
        }
        if (-not $matched) {
            $line
        }
    }

    foreach ($key in $Values.Keys) {
        if (-not $updatedNames.Contains($key)) {
            $updated += "$key=$($Values[$key])"
        }
    }

    Write-Utf8NoBom -Path $ConfigPath -Content (($updated -join [Environment]::NewLine) + [Environment]::NewLine)
}

function Invoke-PythonScript {
    param(
        [string]$ScriptPath,
        [string]$Label
    )

    Push-Location $ProjectRoot
    try {
        $previousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $consoleLines = & $PythonExe $ScriptPath 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
        Pop-Location
    }

    $consoleText = ($consoleLines | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
    $logPaths = @()
    foreach ($line in $consoleLines) {
        $text = $line.ToString()
        if ($text -match "^Log file:\s*(.+)$") {
            $logPaths += $Matches[1]
        }
    }

    Write-SeriesLog "script_run=$Label"
    Write-SeriesLog "script_path=$ScriptPath"
    Write-SeriesLog "exit_code=$exitCode"
    Write-SeriesLog "generated_log_paths=$($logPaths -join '; ')"
    Write-SeriesLog "console_output_begin"
    Write-SeriesLog $consoleText
    Write-SeriesLog "console_output_end"

    return [pscustomobject]@{
        label = $Label
        exit_code = $exitCode
        console_lines = $consoleLines
        console_text = $consoleText
        log_paths = $logPaths
    }
}

function Read-KeyValueLogSection {
    param(
        [string]$LogPath,
        [string]$SectionName
    )

    $values = @{}
    if (-not $LogPath -or -not (Test-Path -LiteralPath $LogPath -PathType Leaf)) {
        return $values
    }

    $inSection = $false
    foreach ($line in Get-Content -LiteralPath $LogPath) {
        if ($line -eq "[$SectionName]") {
            $inSection = $true
            continue
        }
        if ($inSection -and $line -match "^\[.+\]$") {
            break
        }
        if ($inSection -and $line -match "^([^=]+)=(.*)$") {
            $values[$Matches[1]] = $Matches[2]
        }
    }
    return $values
}

function Get-ManualResult {
    param([object]$Run)

    $status = ""
    $action = ""
    foreach ($line in $Run.console_lines) {
        $text = $line.ToString()
        if ($text -match "^Validation status:\s*(.+)$") {
            $status = $Matches[1]
        }
        if ($text -match "^Output action:\s*(.+)$") {
            $action = $Matches[1]
        }
    }
    if (-not $status) {
        $status = "NOT_RUN_OR_UNKNOWN"
    }
    return [pscustomobject]@{
        status = $status
        output_action = $action
        exit_code = $Run.exit_code
        log_paths = $Run.log_paths
    }
}

function Get-CsvDataRowCount {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return -1
    }

    $lineCount = (Get-Content -LiteralPath $Path | Measure-Object -Line).Lines
    if ($lineCount -lt 1) {
        return -1
    }
    return [Math]::Max(0, $lineCount - 1)
}

function Test-DatabaseLandingFiles {
    param([string]$EffDat)

    $checked = 0
    $missing = New-Object System.Collections.Generic.List[string]
    $rowCounts = @{}
    foreach ($source in $DatabaseSources) {
        $path = Join-Path $ProjectRoot "data\landing\$EffDat\database_sources\$($source)_orders_$EffDat.csv"
        $rowCount = Get-CsvDataRowCount -Path $path
        $rowCounts[$source] = $rowCount
        if ($rowCount -ge 0) {
            $checked += 1
        } else {
            $missing.Add($path) | Out-Null
        }
    }

    return [pscustomobject]@{
        checked = $checked
        missing = $missing
        row_counts = $rowCounts
    }
}

function Test-DateOutputs {
    param([string]$EffDat)

    $landingDir = Join-Path $ProjectRoot "data\landing\$EffDat"
    $stagingDir = Join-Path $ProjectRoot "data\staging\$EffDat"
    $dbLanding = Test-DatabaseLandingFiles -EffDat $EffDat
    return [pscustomobject]@{
        landing_dir_exists = Test-Path -LiteralPath $landingDir -PathType Container
        staging_dir_exists = Test-Path -LiteralPath $stagingDir -PathType Container
        db_landing = $dbLanding
    }
}

function Invoke-DateCase {
    param(
        [string]$TestName,
        [string]$EffDat
    )

    Write-SeriesLog "==== $TestName ===="
    Write-SeriesLog "EFF_DAT=$EffDat"
    Set-EnvValues @{ EFF_DAT = $EffDat }

    $manualResultText = "SKIPPED"
    if (Test-Path -LiteralPath $ManualScript -PathType Leaf) {
        $manualRun = Invoke-PythonScript -ScriptPath $ManualScript -Label "$TestName manual"
        $manual = Get-ManualResult -Run $manualRun
        $manualResultText = "$($manual.status) exit=$($manual.exit_code)"
    } else {
        $manual = [pscustomobject]@{
            status = "SKIPPED_MISSING_SCRIPT"
            output_action = ""
            exit_code = 0
            log_paths = @()
        }
        Write-SeriesLog "manual_script_missing=$ManualScript"
    }

    $databaseRun = Invoke-PythonScript -ScriptPath $DatabaseScript -Label "$TestName database"
    $databaseLog = if ($databaseRun.log_paths.Count -gt 0) { $databaseRun.log_paths[-1] } else { "" }
    $databaseStatuses = @{}
    foreach ($sourceName in @("MSSQL", "Oracle", "DB2", "MySQL", "PostgreSQL")) {
        $section = Read-KeyValueLogSection -LogPath $databaseLog -SectionName $sourceName
        $databaseStatuses[$sourceName] = $section
    }

    $outputChecks = Test-DateOutputs -EffDat $EffDat
    $notes = New-Object System.Collections.Generic.List[string]
    if (-not $outputChecks.landing_dir_exists) {
        $notes.Add("missing landing dir") | Out-Null
    }
    if (-not $outputChecks.staging_dir_exists) {
        $notes.Add("missing staging dir") | Out-Null
    }
    foreach ($missingPath in $outputChecks.db_landing.missing) {
        $notes.Add("missing or empty-header database CSV: $missingPath") | Out-Null
    }

    $databaseSuccess = $databaseRun.exit_code -eq 0
    foreach ($sourceName in $databaseStatuses.Keys) {
        $status = $databaseStatuses[$sourceName]["status"]
        if ($status -notin @("SUCCESS_WITH_ROWS", "SUCCESS_EMPTY")) {
            $databaseSuccess = $false
            $notes.Add("$sourceName status=$status") | Out-Null
        }
    }

    $status = if ($databaseSuccess -and $outputChecks.landing_dir_exists -and $outputChecks.staging_dir_exists -and $outputChecks.db_landing.checked -eq 5) {
        "PASS"
    } else {
        "FAIL"
    }

    if ($status -eq "FAIL") {
        $Failures.Add("${TestName} failed for EFF_DAT=${EffDat}: $($notes -join '; ')") | Out-Null
    }

    Write-SeriesLog "manual_result=$manualResultText"
    Write-SeriesLog "manual_log_paths=$($manual.log_paths -join '; ')"
    Write-SeriesLog "database_exit_code=$($databaseRun.exit_code)"
    Write-SeriesLog "database_log_path=$databaseLog"
    Write-SeriesLog "landing_dir_exists=$($outputChecks.landing_dir_exists)"
    Write-SeriesLog "staging_dir_exists=$($outputChecks.staging_dir_exists)"
    foreach ($source in $DatabaseSources) {
        Write-SeriesLog "csv_row_count_$source=$($outputChecks.db_landing.row_counts[$source])"
    }
    Write-SeriesLog "status=$status"
    Write-SeriesLog "notes=$($notes -join '; ')"
    Write-SeriesLog ""

    $Results.Add([pscustomobject]@{
        test_name = $TestName
        EFF_DAT = $EffDat
        manual_csv_result = $manualResultText
        database_extraction_result = "exit=$($databaseRun.exit_code)"
        landing_files_checked = "$($outputChecks.db_landing.checked)/5"
        status = $status
        notes = $notes -join "; "
    }) | Out-Null
}

function Invoke-DatabaseFailureSimulation {
    $testName = "MYSQL_PORT_FAILURE_SIMULATION"
    $effDat = "2026-06-16"
    Write-SeriesLog "==== $testName ===="

    Set-EnvValues @{ EFF_DAT = $effDat }
    $successRun = Invoke-PythonScript -ScriptPath $DatabaseScript -Label "$testName baseline"
    if ($successRun.exit_code -ne 0) {
        $Failures.Add("$testName baseline database extraction failed with exit code $($successRun.exit_code)") | Out-Null
    }

    $mysqlLanding = Join-Path $ProjectRoot "data\landing\$effDat\database_sources\mysql_orders_$effDat.csv"
    if (-not (Test-Path -LiteralPath $mysqlLanding -PathType Leaf)) {
        $Failures.Add("$testName cannot verify protection because MySQL landing file is missing: $mysqlLanding") | Out-Null
    }

    $beforeHash = if (Test-Path -LiteralPath $mysqlLanding -PathType Leaf) {
        (Get-FileHash -LiteralPath $mysqlLanding -Algorithm SHA256).Hash
    } else {
        ""
    }
    $beforeWriteTime = if (Test-Path -LiteralPath $mysqlLanding -PathType Leaf) {
        (Get-Item -LiteralPath $mysqlLanding).LastWriteTimeUtc.ToString("o")
    } else {
        ""
    }

    $currentEnv = Get-Content -LiteralPath $ConfigPath -Raw
    $originalMysqlPort = Get-EnvValueFromContent -Content $currentEnv -Name "MYSQL_PORT"
    try {
        Set-EnvValues @{ EFF_DAT = $effDat; MYSQL_PORT = "3399" }
        $failureRun = Invoke-PythonScript -ScriptPath $DatabaseScript -Label "$testName invalid_mysql_port"
    } finally {
        Set-EnvValues @{ EFF_DAT = $effDat; MYSQL_PORT = $originalMysqlPort }
    }

    $failureLog = if ($failureRun.log_paths.Count -gt 0) { $failureRun.log_paths[-1] } else { "" }
    $mysqlSection = Read-KeyValueLogSection -LogPath $failureLog -SectionName "MySQL"
    $sourceSections = @{}
    foreach ($sourceName in @("MSSQL", "Oracle", "DB2", "MySQL", "PostgreSQL")) {
        $sourceSections[$sourceName] = Read-KeyValueLogSection -LogPath $failureLog -SectionName $sourceName
    }

    $afterHash = if (Test-Path -LiteralPath $mysqlLanding -PathType Leaf) {
        (Get-FileHash -LiteralPath $mysqlLanding -Algorithm SHA256).Hash
    } else {
        ""
    }
    $afterWriteTime = if (Test-Path -LiteralPath $mysqlLanding -PathType Leaf) {
        (Get-Item -LiteralPath $mysqlLanding).LastWriteTimeUtc.ToString("o")
    } else {
        ""
    }

    $notes = New-Object System.Collections.Generic.List[string]
    $mysqlFailedAsExpected = $mysqlSection["status"] -in @("FAILED_PORT_UNREACHABLE", "FAILED_CONNECTION")
    $mysqlLeftUnchanged = $mysqlSection["output_action"] -eq "LEFT_EXISTING_FILE_UNCHANGED"
    $mysqlFileUnchanged = $beforeHash -and $beforeHash -eq $afterHash -and $beforeWriteTime -eq $afterWriteTime
    $exitFailedAsExpected = $failureRun.exit_code -eq 1
    if (-not $mysqlFailedAsExpected) {
        $notes.Add("MySQL status was $($mysqlSection["status"])") | Out-Null
    }
    if (-not $mysqlLeftUnchanged) {
        $notes.Add("MySQL output_action was $($mysqlSection["output_action"])") | Out-Null
    }
    if (-not $mysqlFileUnchanged) {
        $notes.Add("MySQL landing file changed") | Out-Null
    }
    if (-not $exitFailedAsExpected) {
        $notes.Add("failure run exit code was $($failureRun.exit_code)") | Out-Null
    }

    foreach ($sourceName in @("MSSQL", "Oracle", "DB2", "PostgreSQL")) {
        $status = $sourceSections[$sourceName]["status"]
        if ($status -notin @("SUCCESS_WITH_ROWS", "SUCCESS_EMPTY")) {
            $notes.Add("$sourceName did not succeed during failure simulation: $status") | Out-Null
        }
    }

    $status = if ($mysqlFailedAsExpected -and $mysqlLeftUnchanged -and $mysqlFileUnchanged -and $exitFailedAsExpected -and $notes.Count -eq 0) {
        "PASS"
    } else {
        "FAIL"
    }

    if ($status -eq "FAIL") {
        $Failures.Add("$testName failed: $($notes -join '; ')") | Out-Null
    }

    Write-SeriesLog "baseline_exit_code=$($successRun.exit_code)"
    Write-SeriesLog "mysql_landing_file=$mysqlLanding"
    Write-SeriesLog "before_sha256=$beforeHash"
    Write-SeriesLog "before_last_write_utc=$beforeWriteTime"
    Write-SeriesLog "failure_exit_code=$($failureRun.exit_code)"
    Write-SeriesLog "failure_log_path=$failureLog"
    Write-SeriesLog "mysql_status=$($mysqlSection["status"])"
    Write-SeriesLog "mysql_output_action=$($mysqlSection["output_action"])"
    Write-SeriesLog "after_sha256=$afterHash"
    Write-SeriesLog "after_last_write_utc=$afterWriteTime"
    Write-SeriesLog "landing_file_protected=$mysqlFileUnchanged"
    Write-SeriesLog "status=$status"
    Write-SeriesLog "notes=$($notes -join '; ')"
    Write-SeriesLog ""

    $Results.Add([pscustomobject]@{
        test_name = $testName
        EFF_DAT = $effDat
        manual_csv_result = "N/A"
        database_extraction_result = "exit=$($failureRun.exit_code); mysql=$($mysqlSection["status"])"
        landing_files_checked = "mysql protected=$mysqlFileUnchanged"
        status = $status
        notes = $notes -join "; "
    }) | Out-Null
}

Copy-Item -LiteralPath $ConfigPath -Destination $EnvBackupPath -Force
$OriginalEffDat = Get-EnvValueFromContent -Content $OriginalEnvContent -Name "EFF_DAT"

Write-SeriesLog "full_extraction_test_series_start=$(Get-Date -Format "o")"
Write-SeriesLog "project_root=$ProjectRoot"
Write-SeriesLog "config_path=$ConfigPath"
Write-SeriesLog "env_backup_path=$EnvBackupPath"
Write-SeriesLog "original_EFF_DAT=$OriginalEffDat"
Write-SeriesLog "tested_EFF_DAT_values=$($TestDates -join ', ')"
Write-SeriesLog ""

try {
    foreach ($effDat in $TestDates) {
        Invoke-DateCase -TestName "DATE_SERIES" -EffDat $effDat
    }

    Invoke-DateCase -TestName "RERUN_REPLACEMENT" -EffDat "2026-06-16"
    Invoke-DatabaseFailureSimulation
} finally {
    Copy-Item -LiteralPath $EnvBackupPath -Destination $ConfigPath -Force
    $restoredContent = Get-Content -LiteralPath $ConfigPath -Raw
    $EnvRestored = $restoredContent -eq $OriginalEnvContent
    Write-SeriesLog "restored_config_env=$EnvRestored"
    Write-SeriesLog "full_extraction_test_series_end=$(Get-Date -Format "o")"
}

if (-not $EnvRestored) {
    $Failures.Add("config/.env restore verification failed") | Out-Null
}

$finalStatus = if ($Failures.Count -eq 0) { "PASS" } else { "FAIL" }
Write-SeriesLog "final_status=$finalStatus"
if ($Failures.Count -gt 0) {
    Write-SeriesLog "failure_reasons_begin"
    foreach ($failure in $Failures) {
        Write-SeriesLog $failure
    }
    Write-SeriesLog "failure_reasons_end"
}

Write-Output "Full extraction test-series log file: $SeriesLogPath"
$Results | Format-Table -AutoSize
if ($Failures.Count -gt 0) {
    Write-Output "Failures:"
    foreach ($failure in $Failures) {
        Write-Output "- $failure"
    }
    exit 1
}

exit 0
