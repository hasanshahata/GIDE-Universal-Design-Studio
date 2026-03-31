#!/bin/bash

# GIDE V3 - Linux Standalone Executable Build
# Optimized for Debian 8 with Conda/X11 compatibility fixes
# DEBUG MODE: Console enabled to catch runtime errors

echo "========================================================"
echo "GIDE V3 - Linux Standalone Executable Build (Debug Mode)"
echo "========================================================"

# 1. Detect Python Version
PYTHON_CMD="python3.8"

echo "Using $PYTHON_CMD for build..."

# 2. Install Dependencies
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install pyinstaller pillow customtkinter numpy pandas scipy matplotlib psf_utils

# 3. Generate .spec file
echo "Generating GIDE_Sizing_Dashboard_Linux.spec..."
$PYTHON_CMD -m PyInstaller.utils.cliutils.makespec --onefile \
    --name "GIDE_Sizing_Dashboard_Linux" \
    --add-data "gui/assets:gui/assets" \
    --add-data "luts_generation:luts_generation" \
    --hidden-import "PIL._tkinter_finder" \
    --hidden-import "PIL" \
    --hidden-import "psf_utils" \
    --hidden-import "luts_generation.techsweep_spectre" \
    --collect-all customtkinter \
    --collect-all matplotlib \
    --collect-submodules scipy \
    main.py

# 4. Patch .spec file to fix Conda libX11 conflict and filter data
echo "Patching GIDE_Sizing_Dashboard_Linux.spec for X11 compatibility and data filtering..."
$PYTHON_CMD - <<EOF
import os

spec_file = "GIDE_Sizing_Dashboard_Linux.spec"

if not os.path.exists(spec_file):
    print(f"Error: {spec_file} not found!")
    exit(1)

with open(spec_file, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Insert fix before PYZ block
    if line.startswith('pyz = PYZ'):
        new_lines.append("# --- Fixes ---\n")
        # 1. Filter out Conda libX11 conflict but keep system ones
        new_lines.append("a.binaries = [x for x in a.binaries if not x[0].startswith('_CONDA_')]\n")
        new_lines.append("a.binaries = [x for x in a.binaries if not (x[0].startswith('libX11') and 'conda' in x[1].lower())]\n")
        new_lines.append("a.binaries = [x for x in a.binaries if not (x[0].startswith('libxcb') and 'conda' in x[1].lower())]\n")
print("Patch applied successfully.")
EOF

# 5. Build Executable using patched .spec
echo "Building from patched .spec..."
$PYTHON_CMD -m PyInstaller --clean GIDE_Sizing_Dashboard_Linux.spec

# 6. Set Execution Permissions
if [ -f "dist/GIDE_Sizing_Dashboard_Linux" ]; then
    echo "Setting execution permissions..."
    chmod +x dist/GIDE_Sizing_Dashboard_Linux
fi

echo "========================================================"
echo "Build Process Finished!"
echo ""
echo "CRITICAL: Run the file from the Terminal to see any errors:"
echo "cd dist"
echo "./GIDE_Sizing_Dashboard_Linux"
echo "========================================================"
