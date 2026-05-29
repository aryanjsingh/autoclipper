#!/bin/bash
# bcut-asr manual installation script

echo "Starting bcut-asr installation..."

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $python_version"

if [[ $(echo "$python_version < 3.10" | bc -l) -eq 1 ]]; then
    echo "Error: Python 3.10 or higher is required"
    exit 1
fi

# Install ffmpeg
echo "Installing ffmpeg..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "Please install Homebrew first: https://brew.sh/"
        exit 1
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    sudo apt update
    sudo apt install -y ffmpeg
else
    echo "Please install ffmpeg manually"
fi

# Clone and install bcut-asr
echo "Cloning bcut-asr repository..."
git clone https://github.com/SocialSisterYi/bcut-asr.git
cd bcut-asr

echo "Installing bcut-asr..."
pip install .

echo "Verifying installation..."
python3 -c "import bcut_asr; print('bcut-asr installed successfully')"

echo "Installation completed!"
