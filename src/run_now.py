#!/usr/bin/env python3
import json
import os

# Меняем рабочую директорию
os.chdir("/Users/denis/Desktop/masters_thesis")

# Выполняем код напрямую
try:
    exec(open("src/generate_dashboard_fixed.py").read())
except Exception as e:
    print(f"ОШИБКА: {e}")
    import traceback
    traceback.print_exc() 