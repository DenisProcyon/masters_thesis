#!/usr/bin/env python3
import subprocess
import sys
import os

# Меняем рабочую директорию
os.chdir("/Users/denis/Desktop/masters_thesis")

# Выполняем скрипт
try:
    result = subprocess.run([sys.executable, "src/generate_dashboard_fixed.py"], 
                          capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
except Exception as e:
    print(f"Error: {e}") 