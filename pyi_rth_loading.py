"""
PyInstaller runtime hook to display loading message immediately.
This runs before any imports, so users know the app is starting.
"""
import sys

# Print loading message immediately (before any slow imports)
# Use stderr so it appears even if stdout is buffered
print("\n" + "="*60, file=sys.stderr, flush=True)
print("Sport Passport CSV Converter", file=sys.stderr, flush=True)
print("Loading... Please wait...", file=sys.stderr, flush=True)
print("="*60 + "\n", file=sys.stderr, flush=True)
sys.stderr.flush()
