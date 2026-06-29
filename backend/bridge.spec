# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec για το ExpVault bridge

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Συλλογή δεδομένων από reportlab (fonts, κλπ)
datas = collect_data_files('reportlab')
datas += collect_data_files('docx')

a = Analysis(
    ['bridge.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'database',
        'exports',
        'backup',
        'pdf_parser',
        'pdf_templates',
        'reportlab',
        'reportlab.pdfbase',
        'reportlab.pdfbase.ttfonts',
        'reportlab.pdfbase.pdfmetrics',
        'reportlab.lib',
        'reportlab.lib.colors',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.styles',
        'reportlab.lib.enums',
        'reportlab.platypus',
        'reportlab.platypus.tables',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'docx',
        'docx.shared',
        'docx.enum.text',
        'docx.oxml.ns',
        'docx.oxml',
        'sqlite3',
    ],
    excludes=['tkinter', 'matplotlib', 'numpy', 'PIL', 'PyQt5', 'wx'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='bridge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='bridge',
)
