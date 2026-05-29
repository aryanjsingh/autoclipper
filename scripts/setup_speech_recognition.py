#!/usr/bin/env python3
"""
Speech Recognition Environment Setup Script
Automatically installs bcut-asr and related dependencies
"""
import sys
import os
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.install_bcut_asr import install_dependencies, check_bcut_asr_installed, check_ffmpeg_installed
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function"""
    logger.info("AutoClip Speech Recognition Environment Setup")
    logger.info("=" * 50)
    
    # Check current status
    logger.info("Checking current environment status...")
    bcut_available = check_bcut_asr_installed()
    ffmpeg_available = check_ffmpeg_installed()
    
    logger.info(f"bcut-asr status: {'Installed' if bcut_available else 'Not installed'}")
    logger.info(f"ffmpeg status: {'Installed' if ffmpeg_available else 'Not installed'}")
    
    if bcut_available and ffmpeg_available:
        logger.info("All dependencies are already installed, no need to reinstall")
        return True
    
    # Install dependencies
    logger.info("Installing missing dependencies...")
    success = install_dependencies()
    
    if success:
        logger.info("Speech recognition environment setup complete!")
        logger.info("You can now use the following features:")
        logger.info("  - bcut-asr cloud speech recognition (fast)")
        logger.info("  - whisper local speech recognition (reliable)")
        logger.info("  - Smart fallback mechanism")
        return True
    else:
        logger.error("Environment setup failed")
        logger.info("Please check:")
        logger.info("  1. Network connection is working")
        logger.info("  2. System permissions are sufficient")
        logger.info("  3. Dependency tools are available (git, pip, etc.)")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
