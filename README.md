# Chat Application

A conversational AI chat application built with LangChain and Azure OpenAI.

## Features

- Conversational AI with memory
- Session-based conversation history
- Configurable chat settings

## Local Environment Setup

### Prerequisites
- Python 3.9 or higher
- Azure OpenAI account with API credentials
- Conda (for environment management)

### Step 1: Create Conda Environment

```bash
conda create -p env python=3.9 -y
conda activate ./env
```

### Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

1. Copy the example environment file:
```bash
# Windows PowerShell
Copy-Item env.example .env

# Linux/Mac
cp env.example .env
```

2. Edit `.env` file and add your Azure OpenAI credentials:
```env
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
```

### Step 4: Verify Setup

Run the test script to verify everything is working:
```bash
python test.py
```

## Usage

### Run Streamlit UI (Recommended)

**IMPORTANT:** Always use the conda environment's Python to run Streamlit!

**Command to Run:**
```bash
# Windows Command Prompt / PowerShell:
.\env\python.exe -m streamlit run app.py

# Git Bash:
./env/python.exe -m streamlit run app.py
```

**⚠️ DO NOT USE:** `streamlit run app.py` directly - this uses the wrong Python and will cause import errors!

The app will open in your browser with a ChatGPT-like interface where you can:
- Chat with the AI assistant
- Copy messages easily
- See conversation memory status
- Clear chat history

### Use Python API

You can also use the chat module directly in Python:

```python
from src.chatapp.chat import get_chat_response, clear_memory

# Get chat response (with memory)
response = get_chat_response("Hello, how are you?")
print(response)

# Clear conversation memory
clear_memory()
```

## Project Structure

```
ChatApp/
├── src/
│   ├── chatapp/
│   │   ├── chat.py       # Chat functionality with memory
│   │   └── logger.py     # Logging utility
│   └── experiment/       # For experiments/testing
├── logs/                 # Application logs
├── env/                  # Conda environment (not in git)
├── .env                  # Environment variables (not in git)
├── app.py                # Streamlit UI application
├── requirements.txt      # Python dependencies
└── setup.py             # Package setup
```

## Notes

- The `.env` file is in `.gitignore` - never commit your API keys
- Logs are stored in the `logs/` directory
- Always activate your conda environment before running the application: `conda activate ./env`

