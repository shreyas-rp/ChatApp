# Quick Start Guide - Environment Activation

## ✅ USE THIS: Python Virtual Environment (Already Set Up!)

Your virtual environment is already created and ready to use. No need for conda!

### In Command Prompt (CMD):
```cmd
venv\Scripts\activate.bat
```

### In PowerShell:
```powershell
.\venv\Scripts\Activate.ps1
```

### After activation, you'll see `(venv)` at the start of your prompt.

---

## ❌ Conda Not Available

Conda is **not installed** on your system. You have two options:

### Option 1: Use Existing venv (Recommended) ✅
Just activate it with the commands above - **everything is already set up!**

### Option 2: Install Conda (Only if you really need it)
1. Download Miniconda: https://docs.conda.io/en/latest/miniconda.html
2. Install it (add to PATH during installation)
3. **Restart your terminal completely**
4. Then use: `conda create -n chatapp python=3.9`

**But honestly, you don't need conda - your venv is ready to go!**

---

## Quick Test

After activating venv, test it:
```cmd
python -c "import sys; print(sys.executable)"
```
This should show a path ending with `venv\Scripts\python.exe`

---

## Summary

**Just run this in your Command Prompt:**
```cmd
venv\Scripts\activate.bat
```

That's it! Your environment is ready. 🚀

