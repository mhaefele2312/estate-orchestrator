# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Estate OS — Estate Interview
# Run from the build/ directory: pyinstaller estate_interview.spec --noconfirm

block_cipher = None

a = Analysis(
    ['../behaviors/estate-interview/estate_interview.py'],
    pathex=['../behaviors/estate-interview'],
    binaries=[],
    datas=[
        ('../behaviors/estate-interview/questions.py',    '.'),
        ('../behaviors/estate-interview/pdf_generator.py', '.'),
        ('../icons/estate-capture-windows.ico',           '.'),
    ],
    hiddenimports=[
        'customtkinter',
        'reportlab',
        'reportlab.lib',
        'reportlab.platypus',
        'reportlab.lib.pagesizes',
        'reportlab.lib.styles',
        'reportlab.lib.units',
        'reportlab.lib.colors',
        'reportlab.lib.enums',
        'edge_tts',
        'speech_recognition',
        'pyaudio',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['pygame', 'matplotlib', 'numpy', 'pandas'],
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
    name='EstateOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                               # no black window
    icon='../icons/estate-capture-windows.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EstateOS',
)
