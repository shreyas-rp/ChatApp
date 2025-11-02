# Troubleshooting Connection Errors

## Common Connection Error Solutions

### 1. Check Your .env File

Make sure you have a `.env` file in the root directory with:

```env
AZURE_OPENAI_API_KEY=your_actual_api_key_here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
```

**Important:**
- Remove any quotes around the values
- No spaces before/after the `=` sign
- Endpoint should start with `https://`
- Endpoint should end with `/` (trailing slash is optional but recommended)

### 2. Verify API Key and Endpoint

1. **Check Azure Portal:**
   - Go to Azure Portal → Your OpenAI resource
   - Verify the endpoint URL
   - Verify the API key (create new one if needed)

2. **Test Your Endpoint:**
   ```bash
   # Test if endpoint is reachable
   curl https://your-resource-name.openai.azure.com/
   ```

### 3. Check Network Connection

- Ensure you have internet connectivity
- Check if firewall/proxy is blocking the connection
- Try accessing the endpoint from a browser

### 4. Verify Model Availability

Make sure `gpt-4o` model is deployed in your Azure OpenAI resource:
- Go to Azure Portal → Your OpenAI resource → Model deployments
- Verify `gpt-4o` is deployed
- If not, deploy it or change model name in `chat.py`

### 5. Check API Version

The default API version is `2024-02-15-preview`. If that doesn't work, try:
- `2023-12-01-preview`
- `2024-06-01-preview`

Update in your `.env` file:
```env
AZURE_OPENAI_API_VERSION=2024-06-01-preview
```

### 6. Test Connection

Run this test script:

```python
from src.chatapp.chat import get_chat_response

try:
    response = get_chat_response("Hello, test")
    print("✅ Connection successful!")
    print(response)
except Exception as e:
    print(f"❌ Error: {e}")
```

### 7. Common Error Messages

**"Connection error"**
- Check internet connection
- Verify endpoint URL is correct
- Check firewall settings

**"Authentication failed"**
- Verify API key is correct
- Regenerate API key in Azure Portal
- Check if API key has expired

**"Model not found"**
- Verify model is deployed in Azure OpenAI
- Check model name matches exactly (case-sensitive)
- Try different model name like `gpt-35-turbo`

### 8. Alternative: Use OpenAI API Instead

If Azure OpenAI is having issues, you can temporarily use OpenAI directly:

Update `chat.py`:
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7
)
```

Add to `.env`:
```env
OPENAI_API_KEY=your_openai_api_key
```

---

## Still Having Issues?

1. Check the logs in `logs/` directory for detailed error messages
2. Verify all environment variables are loaded correctly
3. Test with a simple Python script outside Streamlit
4. Check Azure OpenAI service status


