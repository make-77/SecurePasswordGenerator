$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BuildDeps = Join-Path $ProjectRoot ".build_deps"

if (-not (Test-Path $BuildDeps)) {
    throw "Missing .build_deps. Run: python -m pip install --target .build_deps pyinstaller cryptography"
}

$env:PYTHONPATH = "$BuildDeps;$ProjectRoot\src;$env:PYTHONPATH"

$PyInstallerExe = Join-Path $BuildDeps "bin\pyinstaller.exe"
$IconPath = Join-Path $ProjectRoot "assets\secure-random-password-generator.ico"
$FolderDist = Join-Path $ProjectRoot "dist\SecureRandomPasswordGenerator"
$ObsoleteStandalone = Join-Path $ProjectRoot "dist\SecureRandomPasswordGenerator-standalone.exe"

function Invoke-ProjectPyInstaller {
    param([string[]]$Arguments)

    if (Test-Path $PyInstallerExe) {
        & $PyInstallerExe @Arguments
    } else {
        python -c "import sys; from PyInstaller.__main__ import run; run(sys.argv[1:])" @Arguments
    }

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}

foreach ($PathToRemove in @($FolderDist, $ObsoleteStandalone)) {
    if (Test-Path -LiteralPath $PathToRemove -PathType Container) {
        Remove-Item -LiteralPath $PathToRemove -Recurse -Force
    } elseif (Test-Path -LiteralPath $PathToRemove) {
        Remove-Item -LiteralPath $PathToRemove -Force
    }
}

$OneFileArgs = @(
    "--paths", "$ProjectRoot\src",
    "--name", "SecureRandomPasswordGenerator-independent",
    "--onefile",
    "--windowed",
    "--icon", $IconPath,
    "--noconfirm",
    "--clean",
    "--add-data", "$ProjectRoot\assets;assets",
    "$ProjectRoot\main.py"
)

Invoke-ProjectPyInstaller -Arguments $OneFileArgs

$StandaloneExePath = Join-Path $ProjectRoot "dist\SecureRandomPasswordGenerator-independent.exe"
if (-not (Test-Path $StandaloneExePath)) {
    throw "Expected standalone exe was not created: $StandaloneExePath"
}

Write-Host "Built independent app: $StandaloneExePath"
