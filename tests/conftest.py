import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
