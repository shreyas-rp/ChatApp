# Environment Activation Guide

## Option 1: Python Virtual Environment (Already Set Up)

### Activate on Windows (PowerShell):
```powershell
.\venv\Scripts\Activate.ps1
```

### Activate on Windows (Command Prompt):
```cmd
venv\Scripts\activate.bat
```

### Activate on Linux/Mac:
```bash
source venv/bin/activate
```

### Verify Activation:
You should see `(venv)` prefix in your terminal prompt when activated.

---

## Option 2: Conda Environment (Alternative Setup)

### If you want to use Conda instead, follow these steps:

### Step 1: Create Conda Environment
```bash
conda create -n chatapp python=3.9
```

### Step 2: Activate Conda Environment
```bash
conda activate chatapp
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Deactivate (when done)
```bash
conda deactivate
```

---

## Quick Reference

### Current Setup (Python venv):
```powershell
# Activate
.\venv\Scripts\Activate.ps1

# Deactivate
deactivate

# Verify Python path
python --version
which python  # Linux/Mac
where python  # Windows
```

### Conda Setup (if you switch):
```bash
# Activate
conda activate chatapp

# Deactivate
conda deactivate

# List environments
conda env list
```

---

## Troubleshooting

### If PowerShell execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### If conda command not found:
- Install Miniconda or Anaconda
- Restart terminal after installation
- Verify: `conda --version`

