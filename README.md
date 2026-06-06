# Βιβλίο Εκρηκτικών Υλών — Electron + Flask

## Δομή Project

```
vivlio-ekrktikon/
├── main.js          ← Electron main process
├── preload.js       ← Electron preload (window controls)
├── package.json     ← npm config + electron-builder
├── assets/
│   ├── icon.png     ← 512x512 PNG (Linux + fallback)
│   ├── icon.ico     ← Windows icon
│   └── icon.icns    ← macOS icon
└── backend/         ← Ο φάκελος με τον Flask κώδικα
    ├── app.py
    ├── database.py
    ├── pdf_parser.py
    ├── exports.py
    ├── templates/
    │   └── index.html
    └── venv/        ← Python virtual environment (δεν ανεβαίνει στο git)
```

## Εγκατάσταση (Development)

### 1. Python backend
```bash
cd backend
python3 -m venv venv

# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install flask pypdf openpyxl reportlab
```

### 2. Node / Electron
```bash
# Στον root φάκελο:
npm install
```

### 3. Εκτέλεση
```bash
npm start
```

Το Electron ξεκινά → spawns το Flask → φορτώνει http://localhost:5000

---

## Build (Παραγωγή)

### Windows (.exe installer)
```bash
npm run dist:win
```

### Linux (.AppImage)
```bash
npm run dist:linux
```

### macOS (.dmg)
```bash
npm run dist:mac
```

Τα αρχεία βγαίνουν στον φάκελο `dist/`.

> **Σημείωση για packaging:** Το electron-builder θα πρέπει να συμπεριλάβει
> και το venv ή να χρησιμοποιήσεις PyInstaller για να φτιάξεις ένα
> standalone Python executable. Δες παρακάτω.

---

## Packaging Python (για standalone .exe / AppImage)

Αντί να απαιτείς Python εγκατεστημένη στον υπολογιστή του χρήστη,
μπόρεσε να χρησιμοποιήσεις PyInstaller:

```bash
cd backend
pip install pyinstaller
pyinstaller --onefile --name flask_backend app.py
```

Μετά αντικατέστησε στο `main.js` το `getPythonPath()` ώστε να δείχνει
στο `backend/dist/flask_backend` (ή `.exe` σε Windows).

---

## .gitignore

```
node_modules/
dist/
backend/venv/
backend/*.db
backend/__pycache__/
*.pyc
*.log
```
