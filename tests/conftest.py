"""
Shared pytest fixtures.

The tests need the project root on sys.path so `import app.foo` and
`import config` resolve the same way they do when running `python app.py`.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
