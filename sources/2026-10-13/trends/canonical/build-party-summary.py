"""Current October 8 evening entry point; earlier analyses remain in dated archives."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('build-summaries-2026-10-08-evening.py')), run_name='__main__')
