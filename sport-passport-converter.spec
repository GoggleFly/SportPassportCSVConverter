# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Sport Passport CSV Converter (Interactive Version)
Creates a standalone executable for the interactive version that doesn't require Python installation.
The interactive version prompts users for input and output file paths.
"""

block_cipher = None

a = Analysis(
    ['converter_interactive.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pandas',
        'openpyxl',
        'pydantic',
        'rich',
        'questionary',
        'python-dateutil',
        'converter',
        'converter.schema',
        'converter.validator',
        'converter.corrector',
        'converter.interactive',
        'converter.row_detector',
        'converter.column_variations',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='sport-passport-converter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path here if you have one
)
