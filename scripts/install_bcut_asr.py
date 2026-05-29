#!/usr/bin/env python3
"""
Automatically install bcut-asr module
"""
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def check_bcut_asr_installed():
    """Check if bcut-asr is installed"""
    try:
        import bcut_asr
        from bcut_asr import BcutASR
        from bcut_asr.orm import ResultStateEnum
        logger.info("bcut-asr is installed")
        return True
    except ImportError:
        logger.info("bcut-asr is not installed")
        return False

def check_ffmpeg_installed():
    """Check if ffmpeg is installed"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("ffmpeg is installed")
            return True
        else:
            logger.warning("ffmpeg is not properly installed")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.warning("ffmpeg is not installed")
        return False

def install_ffmpeg():
    """Install ffmpeg"""
    logger.info("Starting ffmpeg installation...")
    
    system = sys.platform.lower()
    
    try:
        if system == "darwin":  # macOS
            logger.info("Detected macOS system, using Homebrew to install ffmpeg")
            result = subprocess.run(['brew', 'install', 'ffmpeg'], 
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info("ffmpeg installed successfully")
                return True
            else:
                logger.error(f"ffmpeg installation failed: {result.stderr}")
                return False
                
        elif system == "linux":
            logger.info("Detected Linux system, using apt to install ffmpeg")
            result = subprocess.run(['sudo', 'apt', 'update'], 
                                  capture_output=True, text=True, timeout=60)
            result = subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], 
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info("ffmpeg installed successfully")
                return True
            else:
                logger.error(f"ffmpeg installation failed: {result.stderr}")
                return False
                
        elif system == "win32":
            logger.info("Detected Windows system, using winget to install ffmpeg")
            result = subprocess.run(['winget', 'install', 'ffmpeg'], 
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info("ffmpeg installed successfully")
                return True
            else:
                logger.error(f"ffmpeg installation failed: {result.stderr}")
                logger.info("Please install ffmpeg manually: https://ffmpeg.org/download.html")
                return False
        else:
            logger.error(f"Unsupported operating system: {system}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg installation timed out")
        return False
    except Exception as e:
        logger.error(f"ffmpeg installation failed: {e}")
        return False

def install_bcut_asr():
    """Install bcut-asr"""
    logger.info("Starting bcut-asr installation...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        bcut_asr_path = temp_path / "bcut-asr"
        
        try:
            # Try multiple methods to clone repository
            clone_success = False
            
            # Method 1: Use HTTPS
            logger.info("Cloning bcut-asr repository (HTTPS)...")
            result = subprocess.run([
                'git', 'clone', 
                'https://github.com/SocialSisterYi/bcut-asr.git',
                str(bcut_asr_path)
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info("Repository cloned successfully (HTTPS)")
                clone_success = True
            else:
                logger.warning(f"HTTPS clone failed: {result.stderr}")
                
                # Method 2: Use SSH
                logger.info("Trying SSH clone...")
                result = subprocess.run([
                    'git', 'clone', 
                    'git@github.com:SocialSisterYi/bcut-asr.git',
                    str(bcut_asr_path)
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    logger.info("Repository cloned successfully (SSH)")
                    clone_success = True
                else:
                    logger.warning(f"SSH clone failed: {result.stderr}")
            
            if not clone_success:
                logger.error("All clone methods failed")
                logger.info("Please check:")
                logger.info("  1. Network connection is working")
                logger.info("  2. Can access GitHub")
                logger.info("  3. Firewall settings")
                return False
            
            # Check if poetry is available
            try:
                subprocess.run(['poetry', '--version'], 
                             capture_output=True, text=True, timeout=10)
                has_poetry = True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                has_poetry = False
            
            if has_poetry:
                # Install using poetry
                logger.info("Installing bcut-asr using poetry...")
                result = subprocess.run([
                    'poetry', 'lock'
                ], cwd=bcut_asr_path, capture_output=True, text=True, timeout=120)
                
                if result.returncode != 0:
                    logger.warning(f"poetry lock failed: {result.stderr}")
                    logger.info("Trying pip installation...")
                    return install_bcut_asr_with_pip(bcut_asr_path)
                
                result = subprocess.run([
                    'poetry', 'build', '-f', 'wheel'
                ], cwd=bcut_asr_path, capture_output=True, text=True, timeout=120)
                
                if result.returncode != 0:
                    logger.warning(f"poetry build failed: {result.stderr}")
                    logger.info("Trying pip installation...")
                    return install_bcut_asr_with_pip(bcut_asr_path)
                
                # Find generated wheel file
                dist_path = bcut_asr_path / "dist"
                wheel_files = list(dist_path.glob("*.whl"))
                
                if not wheel_files:
                    logger.warning("Wheel file not found, trying pip installation...")
                    return install_bcut_asr_with_pip(bcut_asr_path)
                
                wheel_file = wheel_files[0]
                logger.info(f"Found wheel file: {wheel_file}")
                
                # Install wheel file
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', str(wheel_file)
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    logger.info("bcut-asr installed successfully")
                    return True
                else:
                    logger.error(f"bcut-asr installation failed: {result.stderr}")
                    return False
            else:
                # Install using pip
                logger.info("poetry not installed, using pip to install...")
                return install_bcut_asr_with_pip(bcut_asr_path)
                
        except subprocess.TimeoutExpired:
            logger.error("bcut-asr installation timed out")
            return False
        except Exception as e:
            logger.error(f"bcut-asr installation failed: {e}")
            return False

def install_bcut_asr_with_pip(bcut_asr_path):
    """Install bcut-asr using pip"""
    try:
        logger.info("Installing bcut-asr from source using pip...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', str(bcut_asr_path)
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("bcut-asr installed successfully")
            return True
        else:
            logger.error(f"bcut-asr installation failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"pip installation failed: {e}")
        return False

def install_dependencies():
    """Install all dependencies"""
    logger.info("Starting bcut-asr dependency installation...")
    
    # Check and install ffmpeg
    if not check_ffmpeg_installed():
        logger.info("ffmpeg not installed, starting installation...")
        if not install_ffmpeg():
            logger.warning("ffmpeg installation failed, please install manually")
            logger.info("Installation guide:")
            logger.info("  macOS: brew install ffmpeg")
            logger.info("  Ubuntu: sudo apt install ffmpeg")
            logger.info("  Windows: winget install ffmpeg")
    
    # Check and install bcut-asr
    if not check_bcut_asr_installed():
        logger.info("bcut-asr not installed, starting installation...")
        if not install_bcut_asr():
            logger.error("bcut-asr installation failed")
            return False
    
    logger.info("All dependencies installed successfully!")
    return True

def main():
    """Main function"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting automatic bcut-asr dependency installation...")
    
    success = install_dependencies()
    
    if success:
        logger.info("Installation complete! You can now use bcut-asr for speech recognition")
        return True
    else:
        logger.error("Installation failed, please check network connection and system permissions")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
