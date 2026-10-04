# 📦 Οδηγός Μετατροπής σε EXE - Inventory Manager Pro

## 🎯 Γιατί να το κάνω EXE;

✅ **Πλεονεκτήματα:**
- Τρέχει σε ΚΑΘΕ Windows (χωρίς Python)
- Ένα αρχείο = εύκολη διανομή
- Επαγγελματική εμφάνιση
- Drag & drop σε Desktop
- Double-click και τρέχει!

---

## 🚀 Μέθοδος 1: PyInstaller (ΣΥΝΙΣΤΏΜΕΝΗ)

### Βήμα 1: Εγκατάσταση

```bash
pip install pyinstaller
```

### Βήμα 2: Δημιουργία EXE

**Απλή εντολή (ένα αρχείο):**
```bash
pyinstaller --onefile --windowed --name "InventoryManager" --icon=app_icon.ico inventory_manager.py
```

**Με περισσότερες επιλογές:**
```bash
pyinstaller --onefile ^
    --windowed ^
    --name "Inventory Manager Pro" ^
    --icon=app_icon.ico ^
    --add-data "README.md;." ^
    --hidden-import=openpyxl ^
    --hidden-import=sqlite3 ^
    inventory_manager.py
```

### Παράμετροι:

| Παράμετρος | Τι κάνει |
|-----------|----------|
| `--onefile` | Δημιουργεί ΕΝΑ .exe (πιο εύκολο) |
| `--windowed` | Χωρίς console window (GUI μόνο) |
| `--name` | Όνομα του .exe αρχείου |
| `--icon` | Custom εικονίδιο (.ico) |
| `--add-data` | Προσθήκη άλλων αρχείων |
| `--hidden-import` | Force import βιβλιοθηκών |

### Βήμα 3: Αποτέλεσμα

```
📁 dist/
  └── Inventory Manager Pro.exe  ← Αυτό μοιράζεις!
```

**Μέγεθος:** ~15-25 MB

---

## 🔥 Μέθοδος 2: Auto-py-to-exe (GUI - Πιο εύκολο!)

### Βήμα 1: Εγκατάσταση

```bash
pip install auto-py-to-exe
```

### Βήμα 2: Εκτέλεση

```bash
auto-py-to-exe
```

### Βήμα 3: Ρυθμίσεις στο GUI

Ανοίγει παράθυρο με επιλογές:

1. **Script Location:** Διάλεξε `inventory_manager.py`
2. **Onefile:** One File (✓)
3. **Console Window:** Window Based (No Console) (✓)
4. **Icon:** Διάλεξε το `app_icon.ico` (αν έχεις)
5. **Additional Files:** Πρόσθεσε `README.md` (optional)
6. **Advanced:**
   - Hidden Imports: `openpyxl, sqlite3`

### Βήμα 4: Convert!

Πάτα **"CONVERT .PY TO .EXE"**

✅ **Πλεονεκτήματα:**
- Πολύ εύκολο (GUI)
- Βλέπεις όλες τις επιλογές
- Live preview

---

## ⚡ Μέθοδος 3: cx_Freeze (Cross-platform)

### Βήμα 1: Εγκατάσταση

```bash
pip install cx_Freeze
```

### Βήμα 2: Δημιουργία setup.py

```python
from cx_Freeze import setup, Executable

setup(
    name="Inventory Manager Pro",
    version="1.0",
    description="Σύστημα Διαχείρισης Αποθέματος",
    executables=[
        Executable(
            "inventory_manager.py",
            base="Win32GUI",
            icon="app_icon.ico",
            target_name="InventoryManager.exe"
        )
    ],
    options={
        "build_exe": {
            "packages": ["tkinter", "openpyxl", "sqlite3", "json"],
            "include_files": ["README.md"],
        }
    }
)
```

### Βήμα 3: Build

```bash
python setup.py build
```

---

## 🎨 Δημιουργία Icon (.ico)

### Online Tools (Πιο εύκολο):
1. Πήγαινε: https://convertio.co/png-ico/
2. Ανέβασε μια εικόνα (512x512 px recommended)
3. Convert σε .ico
4. Download

### Python Script:
```python
from PIL import Image

# Άνοιγμα PNG
img = Image.open('icon.png')

# Resize σε 256x256
img = img.resize((256, 256), Image.LANCZOS)

# Αποθήκευση ως .ico
img.save('app_icon.ico', format='ICO')
```

### Ετοιμα Icons:
- 📦 https://icons8.com (δωρεάν)
- 📦 https://www.flaticon.com

---

## 📋 Automated Build Script

Δημιούργησε `build.bat` για Windows:

```batch
@echo off
echo ========================================
echo  Inventory Manager Pro - Build Script
echo ========================================
echo.

echo [1/3] Cleaning old builds...
rmdir /s /q build dist 2>nul
del /q *.spec 2>nul

echo [2/3] Building EXE with PyInstaller...
pyinstaller --onefile ^
    --windowed ^
    --name "InventoryManager" ^
    --icon=app_icon.ico ^
    --hidden-import=openpyxl ^
    --hidden-import=sqlite3 ^
    inventory_manager.py

echo [3/3] Copying files to dist...
copy README.md dist\
copy Import_Demo_Excel.xlsx dist\ 2>nul

echo.
echo ========================================
echo  Build Complete!
echo  EXE Location: dist\InventoryManager.exe
echo ========================================
pause
```

Εκτέλεση:
```bash
build.bat
```

---

## 🐛 Αντιμετώπιση Προβλημάτων

### Πρόβλημα 1: "No module named openpyxl"

**Λύση:**
```bash
pyinstaller --hidden-import=openpyxl --hidden-import=openpyxl.cell._writer inventory_manager.py
```

### Πρόβλημα 2: "Database locked"

**Λύση:** Πρόσθεσε στον κώδικα:
```python
import sys
import os

# Αν τρέχει ως EXE
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# Database στον ίδιο φάκελο με το EXE
db_path = os.path.join(os.path.dirname(sys.executable), 'inventory.db')
```

### Πρόβλημα 3: Μεγάλο μέγεθος EXE

**Λύσεις:**
1. Χρησιμοποίησε `--onefile` αντί για `--onedir`
2. Χρησιμοποίησε UPX compression:
   ```bash
   pip install upx-windows
   pyinstaller --upx-dir=upx_dir inventory_manager.py
   ```
3. Exclude άχρηστες βιβλιοθήκες:
   ```bash
   pyinstaller --exclude-module matplotlib --exclude-module numpy
   ```

### Πρόβλημα 4: Αργή εκκίνηση

**Λύση:** Χρησιμοποίησε `--onedir` αντί για `--onefile`
```bash
pyinstaller --onedir --windowed inventory_manager.py
```

---

## 📦 Distribution Package

Δημιούργησε ένα ZIP με:

```
📁 InventoryManager_v1.0/
  ├── InventoryManager.exe       ← Το κύριο EXE
  ├── README.md                  ← Οδηγίες
  ├── Import_Demo_Excel.xlsx     ← Demo data
  └── ΟΔΗΓΙΕΣ_ΧΡΗΣΗΣ.txt        ← Γρήγορες οδηγίες
```

---

## ✅ Checklist πριν το EXE

- [ ] Δοκιμάστε την Python έκδοση
- [ ] Κλείστε όλες τις βάσεις δεδομένων
- [ ] Δημιουργήστε app_icon.ico
- [ ] Ελέγξτε τα imports
- [ ] Δοκιμάστε το EXE σε "καθαρό" PC
- [ ] Ελέγξτε τα ελληνικά (encoding)

---

## 🚀 Pro Tips

### 1. Versioning
Πρόσθεσε version info:
```bash
pyinstaller --onefile ^
    --version-file=version.txt ^
    inventory_manager.py
```

### 2. Digital Signature
Για επαγγελματική χρήση, υπογράψτε το EXE:
```bash
signtool sign /f certificate.pfx /p password InventoryManager.exe
```

### 3. Installer
Δημιουργήστε installer με **Inno Setup**:
- Download: https://jrsoftware.org/isdl.php
- Δημιουργεί setup.exe με wizard

### 4. Auto-Update
Προσθέστε στον κώδικα:
```python
import requests

CURRENT_VERSION = "1.0.0"
UPDATE_URL = "https://yoursite.com/version.json"

def check_updates():
    response = requests.get(UPDATE_URL)
    latest = response.json()['version']
    if latest > CURRENT_VERSION:
        messagebox.showinfo("Νέα Έκδοση", f"Διαθέσιμη v{latest}!")
```

---

## 📊 Σύγκριση Μεθόδων

| Μέθοδος | Ευκολία | Μέγεθος | Ταχύτητα | Cross-platform |
|---------|---------|---------|----------|----------------|
| PyInstaller | ⭐⭐⭐⭐ | ~20MB | Γρήγορο | ✅ |
| auto-py-to-exe | ⭐⭐⭐⭐⭐ | ~20MB | Γρήγορο | ✅ |
| cx_Freeze | ⭐⭐⭐ | ~25MB | Μέτριο | ✅ |

**Σύσταση:** Ξεκίνα με **auto-py-to-exe** (πιο εύκολο)

---

## 🎯 Τελική Εντολή (Copy-Paste Ready)

```bash
# Install
pip install pyinstaller

# Build
pyinstaller --onefile --windowed --name "InventoryManager" inventory_manager.py

# Το EXE είναι στο: dist\InventoryManager.exe
```

---

**Έτοιμο για παραγωγή!** 🚀
