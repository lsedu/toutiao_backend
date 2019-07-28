import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR))
sys.path.insert(0, os.path.join(BASE_DIR, 'common'))

from server import run


if len(sys.argv) < 2:
    print('use python main.py [port].')
    exit(1)

port = int(sys.argv[1])
run(port)

