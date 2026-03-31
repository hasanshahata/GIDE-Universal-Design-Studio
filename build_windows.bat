@echo off
echo ========================================================
echo GIDE V3 - Windows Standalone Executable Build
echo ========================================================

:: Ensure dependecies are installed
pip install pyinstaller pillow customtkinter numpy pandas scipy matplotlib psf_utils -q

:: Build the executable
:: --noconsole: Hide the terminal window
:: --onefile: Bundle everything into a single .exe
:: --clean: Clean PyInstaller cache before building
:: --name: Name of the output file
:: --add-data: Include UI assets (Format: "source;dest" on Windows)

echo Building...
pyinstaller --noconsole --onefile --clean ^
    --name "GIDE_Sizing_Dashboard" ^
    --add-data "gui/assets;gui/assets" ^
    --add-data "luts_generation;luts_generation" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "PIL" ^
    --hidden-import "psf_utils" ^
    --hidden-import "luts_generation.techsweep_spectre" ^
    --collect-all customtkinter ^
    --collect-all matplotlib ^
    --collect-all scipy ^
    main.py

echo ========================================================
echo Build Complete! Check the 'dist' folder for the .exe
echo ========================================================
pause
