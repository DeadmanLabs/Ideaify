@echo off
REM Get the current directory
set CURRENT_DIR=%cd%

REM Create the ObsidianVault directory if it doesn't exist
if not exist "%CURRENT_DIR%\ObsidianVault" (
    mkdir "%CURRENT_DIR%\ObsidianVault"
    mkdir "%CURRENT_DIR%\ObsidianVault\Ideas"
    echo Created ObsidianVault directory
)

REM Run the Docker container with the Obsidian vault mounted
docker run -it -p 8000:8000 -v "%CURRENT_DIR%\ObsidianVault:/obsidian/vault" ideaify
