#!/usr/bin/env python3
"""
Install Multi-Model Provider Dependencies Script
"""
import subprocess
import sys
import os

def install_package(package):
    """Install Python package"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}: {e}")
        return False

def main():
    """Main function"""
    print("Starting multi-model provider dependency installation...")
    
    # Packages to install
    packages = [
        "openai>=1.0.0",           # OpenAI
        "google-generativeai>=0.3.0",  # Google Gemini
        "requests>=2.25.0",        # SiliconFlow (HTTP requests)
        "dashscope>=1.10.0",       # Alibaba Tongyi Qianwen (if not already installed)
    ]
    
    success_count = 0
    total_count = len(packages)
    
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\nInstallation results: {success_count}/{total_count} packages installed successfully")
    
    if success_count == total_count:
        print("All dependencies installed! You can now use multi-model provider features.")
        print("\nUsage instructions:")
        print("1. Start system: python backend/main.py")
        print("2. Visit settings page to configure API keys")
        print("3. Select your preferred AI model provider")
        print("4. Start using AI auto-clipping features")
    else:
        print("Some dependencies failed to install. Please check your network connection or manually install the failed packages.")
        print("Manual install commands:")
        for package in packages:
            print(f"  pip install {package}")

if __name__ == "__main__":
    main()
