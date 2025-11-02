# 🚀 Quick Start Guide

## ✅ Run the Application

**ALWAYS use the conda environment's Python!**

### For Git Bash Users:
```bash
./env/python.exe -m streamlit run app.py
```

### For Windows Command Prompt/PowerShell:
```bash
.\env\python.exe -m streamlit run app.py
```

## ❌ Common Error Fix

If you see this error:
```
ModuleNotFoundError: No module named 'langchain.memory'
```

**Solution:** You're using the wrong Python! Always use:
```bash
.\env\python.exe -m streamlit run app.py
```

**NEVER use:** `streamlit run app.py` directly (it uses global Python which doesn't have LangChain)

## 🔧 Verify Setup

Check if everything is installed correctly:
```bash
.\env\python.exe -c "from src.chatapp.chat import get_chat_response; print('✅ Everything works!')"
```

## 📝 Environment Setup

If you haven't set up the environment yet:

1. Install dependencies:
```bash
.\env\python.exe -m pip install -r requirements.txt
```

2. Create `.env` file from `env.example`:
```bash
Copy-Item env.example .env
```

3. Edit `.env` and add your Azure OpenAI credentials.

## 🎯 Troubleshooting

- **Import errors?** → Make sure you're using `.\env\python.exe`
- **Module not found?** → Run: `.\env\python.exe -m pip install -r requirements.txt`
- **Streamlit not found?** → Run: `.\env\python.exe -m pip install streamlit`

