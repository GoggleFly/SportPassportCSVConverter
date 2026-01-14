# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Sport Passport CSV Converter (Interactive Version)
Creates a standalone executable for the interactive version that doesn't require Python installation.
The interactive version prompts users for input and output file paths.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None

# Collect all data files and submodules for packages that need them
# This ensures everything is included
pandas_datas, pandas_binaries, pandas_hiddenimports = collect_all('pandas')
openpyxl_datas, openpyxl_binaries, openpyxl_hiddenimports = collect_all('openpyxl')

a = Analysis(
    ['converter_interactive.py'],
    pathex=[],
    binaries=pandas_binaries + openpyxl_binaries,
    datas=pandas_datas + openpyxl_datas,
    hiddenimports=[
        # Use collect_all results for pandas and openpyxl
        *pandas_hiddenimports,
        *openpyxl_hiddenimports,
        # Additional explicit imports for packages that might be missed
        'pydantic',
        'pydantic._internal',
        'pydantic.fields',
        'pydantic.types',
        'pydantic.validators',
        'pydantic._pydantic_core',
        # Rich
        'rich',
        'rich.console',
        'rich.panel',
        'rich.table',
        'rich.text',
        'rich.progress',
        'rich.progress.spinner',
        'rich.box',
        'rich.markup',
        'rich.style',
        # Questionary
        'questionary',
        'questionary.prompts',
        'questionary.prompts.common',
        'questionary.prompts.select',
        'questionary.prompts.text',
        'questionary.prompts.confirm',
        'questionary.form',
        'questionary.style',
        'prompt_toolkit',
        'prompt_toolkit.formatted_text',
        'prompt_toolkit.shortcuts',
        # Date utilities
        'dateutil',
        'dateutil.parser',
        'dateutil.relativedelta',
        'dateutil.tz',
        # Converter modules
        'converter',
        'converter.schema',
        'converter.validator',
        'converter.corrector',
        'converter.interactive',
        'converter.row_detector',
        'converter.column_variations',
        'converter.banners',
        'converter.main',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyi_rth_loading.py'],
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
    upx=False,  # Disable UPX compression for faster startup
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
