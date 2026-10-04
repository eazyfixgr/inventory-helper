# Inventory Manager Pro

A clean, fast desktop app to manage products and stock, built with Python and SQLite.

> **Download:** grab the latest `InventoryManager.exe` from the [Releases](https://github.com/eazyfixgr/inventory-helper/releases) page. No installation required.

## Features

- Product catalogue with quantities and prices
- Local **SQLite** database (`inventory.db` created on first run)
- **Excel / CSV import & export** (openpyxl)
- Low-stock warnings
- Keyboard shortcuts for fast data entry
- Ships with `Import_Demo_Excel.xlsx` to try imports instantly

## Getting started (run from source)

```bash
python -m pip install -r requirements.txt
python inventory_manager.py
```

## Build a standalone EXE

Use the included `build.bat`, or run:

```bash
python -m pip install pyinstaller
python -m PyInstaller --onefile --windowed --name InventoryManager ^
  --hidden-import=openpyxl --hidden-import=sqlite3 inventory_manager.py
```

The executable is created in `dist/InventoryManager.exe`.

## License

Released under the [MIT License](LICENSE).

---

# Inventory Manager Pro (Ελληνικά)

Εφαρμογή διαχείρισης αποθέματος για Windows, με τοπική βάση SQLite.

> **Λήψη:** κατεβάστε το `InventoryManager.exe` από τη σελίδα [Releases](https://github.com/eazyfixgr/inventory-helper/releases).

## Δυνατότητες

- Κατάλογος προϊόντων με ποσότητες και τιμές
- Τοπική βάση δεδομένων SQLite
- Εισαγωγή/εξαγωγή Excel & CSV
- Προειδοποιήσεις χαμηλού αποθέματος
- Συντομεύσεις πληκτρολογίου
