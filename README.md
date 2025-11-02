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

### Step 1: Create Virtual Environment

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
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

```python
from src.chatapp.chat import get_chat_response, clear_memory

# Get chat response
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
├── venv/                 # Virtual environment (not in git)
├── .env                  # Environment variables (not in git)
├── requirements.txt      # Python dependencies
└── setup.py             # Package setup
```

## Notes

- The `.env` file is in `.gitignore` - never commit your API keys
- Logs are stored in the `logs/` directory
- Always activate your virtual environment before running the application

