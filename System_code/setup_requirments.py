#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_requirements.py - Setup script to install required dependencies
"""

import subprocess
import sys
import importlib

def install_package(package):
    """Install a package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def check_and_install_packages():
    """Check and install required packages."""
    required_packages = {
        'pandas': 'pandas',
        'openpyxl': 'openpyxl',
        'xlsxwriter': 'xlsxwriter'  # Alternative Excel writer
    }
    
    print("🔍 Checking required packages...")
    
    missing_packages = []
    
    for module_name, package_name in required_packages.items():
        try:
            importlib.import_module(module_name)
            print(f"✅ {module_name} is installed")
        except ImportError:
            print(f"❌ {module_name} is missing")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n📦 Installing missing packages: {', '.join(missing_packages)}")
        
        for package in missing_packages:
            print(f"Installing {package}...")
            if install_package(package):
                print(f"✅ {package} installed successfully")
            else:
                print(f"❌ Failed to install {package}")
                return False
        
        print("\n🎉 All packages installed successfully!")
    else:
        print("\n✅ All required packages are already installed!")
    
    return True

def main():
    """Main setup function."""
    print("🚀 RFID LoRaWAN Processing - Setup Requirements")
    print("=" * 60)
    
    if check_and_install_packages():
        print("\n✅ Setup completed successfully!")
        print("You can now run the main test script.")
        return 0
    else:
        print("\n❌ Setup failed!")
        print("Please install the missing packages manually:")
        print("pip install pandas openpyxl xlsxwriter")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)