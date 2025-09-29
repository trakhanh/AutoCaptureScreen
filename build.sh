#!/bin/bash

echo "========================================"
echo "    AutoScreen Build Script"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 is not installed or not in PATH"
    echo "Please install Python 3.7+ and try again"
    exit 1
fi

echo "[1/5] Checking Python installation..."
python3 --version

echo
echo "[2/5] Installing/updating dependencies..."
pip3 install -r requirements.txt
pip3 install pyinstaller

echo
echo "[3/5] Cleaning previous builds..."
rm -rf dist build __pycache__

echo
echo "[4/5] Building executable with PyInstaller..."
python3 -m PyInstaller autoscreen.spec

if [ $? -ne 0 ]; then
    echo
    echo "ERROR: Build failed!"
    echo "Check the error messages above"
    exit 1
fi

echo
echo "[5/5] Build completed successfully!"
echo
echo "Executable location: dist/AutoScreen"
echo
echo "You can now distribute the entire 'dist' folder to users."
echo
