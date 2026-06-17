# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for El Malick Gest (onedir, windowed).

Build:
    .venv/Scripts/python -m PyInstaller "El Malick Gest.spec" --noconfirm --clean \
        --distpath dist_release --workpath build_release

NOTE: build from a folder that is NOT synced by OneDrive/Dropbox. Cloud sync
holds file handles and makes PyInstaller's COLLECT step fail with
"PermissionError: [WinError 5]". Either pause sync or point --distpath/--workpath
to a local path (e.g. C:\Temp\emg_dist).

Bundles the Arabic fonts (required for PDF bulletins), the app icon, the
config template, and the Alembic migrations so the database can be set up on a
clean machine.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# --- Data files shipped alongside the executable -----------------------------
datas = [
    ("Fonts", "Fonts"),                     # Amiri / Cairo / Noto Naskh — Arabic PDF rendering
    ("icon.ico", "."),
    ("config.ini.example", "."),            # template for first-run config.ini
    ("alembic", "alembic"),                 # migration scripts
    ("alembic.ini", "."),
]
datas += collect_data_files("matplotlib")   # mpl-data (fonts, styles)

# --- Modules PyInstaller's static analysis can miss --------------------------
hiddenimports = [
    "psycopg2",
    "matplotlib.backends.backend_qtagg",
    "openpyxl",
    "fpdf",
]
hiddenimports += collect_submodules("psycopg2")

a = Analysis(
    ["main_dashbord.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="El Malick Gest",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="El Malick Gest",
)
