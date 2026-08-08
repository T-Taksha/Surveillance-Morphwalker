#!/bin/bash
# ============================================================
# Raspberry Pi Robot - One-Click Setup Script
# ============================================================
# Run this script on your Raspberry Pi after transferring files
# Usage: bash raspberry_pi_setup.sh
# ============================================================

set -e  # Exit on error

echo ""
echo "============================================================"
echo "  Raspberry Pi Robot - Automated Setup"
echo "============================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}[1/7] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

echo ""
echo -e "${GREEN}[2/7] Installing system dependencies...${NC}"
sudo apt-get install -y python3-pip python3-venv python3-dev
sudo apt-get install -y libopencv-dev python3-opencv
sudo apt-get install -y libatlas-base-dev libhdf5-dev
sudo apt-get install -y i2c-tools python3-smbus

echo ""
echo -e "${GREEN}[3/7] Configuring GPIO permissions...${NC}"
sudo usermod -a -G gpio $USER
sudo usermod -a -G i2c $USER
echo "GPIO permissions configured (reboot required to take effect)"

echo ""
echo -e "${GREEN}[4/7] Creating Python virtual environment...${NC}"
if [ -d "venv" ]; then
    echo "Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "Virtual environment created"
fi

echo ""
echo -e "${GREEN}[5/7] Activating virtual environment...${NC}"
source venv/bin/activate

echo ""
echo -e "${GREEN}[6/7] Installing Python dependencies...${NC}"
pip install --upgrade pip

echo "Installing core packages..."
pip install opencv-python numpy flask imutils flask-cors

echo "Installing RPi.GPIO..."
pip install RPi.GPIO

echo "Installing YOLO (this may take a while)..."
read -p "Install YOLO for object detection? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install ultralytics
    echo "YOLO installed"
else
    echo "Skipping YOLO installation"
fi

echo ""
echo -e "${GREEN}[7/7] Verifying installation...${NC}"
python3 -c "import cv2, numpy, flask, RPi.GPIO; print('✓ All core packages imported successfully!')" || {
    echo -e "${RED}Error: Package verification failed${NC}"
    exit 1
}

echo ""
echo "============================================================"
echo -e "${GREEN}  Installation Complete!${NC}"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Reboot to apply GPIO permissions: sudo reboot"
echo "  2. After reboot, activate environment: source venv/bin/activate"
echo "  3. Test motor control: python3 motor_control.py"
echo "  4. Run main system: python3 main.py --mode autonomous"
echo ""
echo "Web interface will be available at:"
echo "  http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "============================================================"

read -p "Reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo reboot
fi
