# Release Checklist - El Malick Gest

Use this checklist before publishing any new version.

## 1) Versioning

- [ ] Update `AppVersion` in `ElMalickGestInstaller.iss`.
- [ ] Keep output name/version aligned with the release label.
- [ ] Add a short release note (what changed, bug fixes, known limits).

## 2) Pre-release validation

- [ ] Launch app and test login.
- [ ] Test student add/edit/delete.
- [ ] Confirm class assignment is required before student save.
- [ ] Test invoices screen and dues report export.
- [ ] Test PDF reports (students, staff, attendance, timetable).
- [ ] Verify Arabic text rendering where applicable.
- [ ] Verify app icon in login and main window.

## 3) Clean build

- [ ] Remove previous `build_release` and `dist_release` folders.
- [ ] Build with:

```powershell
& "c:/Users/EL MALICK/OneDrive/Documents/El Malick Gest - Copie/.venv/Scripts/python.exe" -m PyInstaller "El Malick Gest.spec" --noconfirm --clean --distpath dist_release --workpath build_release
```

- [ ] Confirm executable exists:
  - `dist_release/El Malick Gest/El Malick Gest.exe`

## 4) Installer build

- [ ] Compile installer script:

```powershell
& "C:\Users\EL MALICK\AppData\Local\Programs\Inno Setup 6\ISCC.exe" "ElMalickGestInstaller.iss"
```

- [ ] Confirm setup exists:
  - `installer_output/El_Malick_Gest_Setup.exe`

## 5) Final smoke test

- [ ] Install using setup on a clean machine/user profile if possible.
- [ ] Launch app from Start menu shortcut.
- [ ] Open core modules and export one PDF.
- [ ] Uninstall test (optional but recommended).

## 6) Distribution package

- [ ] Share `installer_output/El_Malick_Gest_Setup.exe`.
- [ ] Include `CHANGELOG.md` or release notes text.
- [ ] Tag source snapshot in git for traceability.

## Current verified build (2026-03-08)

- EXE: `dist_release/El Malick Gest/El Malick Gest.exe`
- Setup: `installer_output/El_Malick_Gest_Setup.exe`
