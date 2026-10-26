$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot
python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name StudyFlow `
    --specpath build `
    --workpath build\pyinstaller `
    --distpath dist `
    --collect-submodules keyring.backends `
    main.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}
