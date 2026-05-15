import threading
import sys

# Standart girdiyi (Terminali) canlı tutmak için ayar
sys.stdin = open(0)
workers = 1
threads = 2
timeout = 120