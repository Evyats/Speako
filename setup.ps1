[CmdletBinding()]
param(
    [string]$Python = 'python',
    [switch]$Dev
)

$ErrorActionPreference = 'Stop'
$venv = Join-Path $PSScriptRoot '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'
$venvPythonw = Join-Path $venv 'Scripts\pythonw.exe'

if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python -I -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
    if ($LASTEXITCODE -ne 0) { throw 'Speako requires Python 3.11 or newer.' }
    & $Python -I -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the project virtual environment.' }
}

# Refuse an existing environment that exposes globally installed packages.
& $venvPython -I -c "import sys, site; assert sys.prefix != sys.base_prefix; assert not site.ENABLE_USER_SITE; from pathlib import Path; cfg = (Path(sys.prefix) / 'pyvenv.cfg').read_text().lower(); assert 'include-system-site-packages = false' in cfg"
if ($LASTEXITCODE -ne 0) { throw 'The existing .venv is not isolated. Recreate it before continuing.' }

$installTarget = $PSScriptRoot
if ($Dev) { $installTarget += '[dev]' }
& $venvPython -I -m pip --isolated install --editable $installTarget
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed; the shortcut was not updated.' }
& $venvPython -I -m pip --isolated check
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
& $venvPython -I -c "import speako.app"
if ($LASTEXITCODE -ne 0) { throw 'Speako could not load; the shortcut was not updated.' }

$envFile = Join-Path $PSScriptRoot '.env'
if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot '.env.example') -Destination $envFile
    Write-Host 'Add your OpenAI API key to .env before using Speako.'
}

$desktop = [Environment]::GetFolderPath('DesktopDirectory')
$shortcutPath = Join-Path $desktop 'Speako.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $venvPythonw
$shortcut.Arguments = '-I -m speako'
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = 'Speako (project virtual environment)'
$shortcut.Save()
Write-Host "Ready. Open $shortcutPath to start Speako."
