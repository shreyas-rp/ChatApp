# Environment Activation Commands

## Current Setup (Python Virtual Environment) ✅

### To Activate:
```powershell
.\venv\Scripts\Activate.ps1
```

**After activation, you'll see `(venv)` in your terminal prompt**

---

## If You Want to Use Conda Instead:

### Step 1: Install Conda (if not installed)
Download and install Miniconda or Anaconda:
- Miniconda: https://docs.conda.io/en/latest/miniconda.html
- Anaconda: https://www.anaconda.com/products/distribution

After installation, **restart your terminal**.

### Step 2: Create Conda Environment
```bash
conda create -n chatapp python=3.9
```

### Step 3: Activate Conda Environment
```bash
conda activate chatapp
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Quick Commands Reference

### Python venv (Current):
```powershell
# Activate
.\venv\Scripts\Activate.ps1

# Deactivate
deactivate

# Check if activated (you'll see "venv" in prompt)
```

### Conda (Alternative):
```bash
# Activate
conda activate chatapp

# Deactivate  
conda deactivate

# List all environments
conda env list
```

---

## Recommended: Use Current venv Setup

Since your virtual environment is already set up and working, just use:

```powershell
.\venv\Scripts\Activate.ps1
```

No need to switch to conda unless you specifically prefer it!

