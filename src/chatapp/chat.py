import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

# Try different import paths for ConversationBufferMemory based on LangChain version
try:
    from langchain.memory import ConversationBufferMemory
except ImportError:
    try:
        # Try direct import from buffer module
        from langchain.memory.buffer import ConversationBufferMemory
    except ImportError:
        try:
            import langchain.memory.buffer as buffer_module
            ConversationBufferMemory = buffer_module.ConversationBufferMemory
        except ImportError:
            try:
                from langchain_community.memory import ConversationBufferMemory
            except ImportError:
                try:
                    from langchain_core.memory import ConversationBufferMemory
                except ImportError:
                    raise ImportError(
                        "Could not import ConversationBufferMemory from any location. "
                        "Please ensure LangChain is installed in your Python environment. "
                        "Run: pip install langchain langchain-community langchain-openai"
                    )

from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

# Access the environment variables
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

# Validate environment variables
if not api_key:
    raise ValueError("AZURE_OPENAI_API_KEY not found in environment variables. Please check your .env file.")
if not endpoint:
    raise ValueError("AZURE_OPENAI_ENDPOINT not found in environment variables. Please check your .env file.")

# Initialize the LLM with error handling
try:
    llm = AzureChatOpenAI(
        model_name="gpt-4o",
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        temperature=0.7,  # Add some creativity for chat
        timeout=30  # Add timeout for connection
    )
except Exception as e:
    # Don't expose endpoint or API key in error messages
    error_msg = str(e).lower()
    if "endpoint" in error_msg:
        raise ConnectionError("Failed to initialize AI client. Please check your endpoint configuration in the .env file.")
    elif "api key" in error_msg or "key" in error_msg:
        raise ConnectionError("Failed to initialize AI client. Please check your API key in the .env file.")
    else:
        raise ConnectionError("Failed to initialize AI client. Please verify your configuration.")

# Create a normal chat prompt template
normal_chat_template = """The following is a friendly conversation between a human and an AI assistant. 
The AI is helpful, knowledgeable, and provides detailed, thoughtful responses. The AI remembers previous parts of the conversation.

Current conversation:
{history}
Human: {input}
AI Assistant:"""

# Create a custom prompt template for QA Assistant
qa_chat_template = """You are a professional QA Assistant specialized in creating comprehensive defect reports for QA teams. 
Your role is to analyze user input about bugs, issues, or problems they've encountered and generate well-structured defect reports.

**IMPORTANT: Only ask clarifying questions if ABSOLUTELY ESSENTIAL information is missing to create a basic defect report. Do NOT ask too many questions - be smart and infer reasonable details from context. Only ask for critical missing information like:**
- If no steps are provided and it's not obvious from the description
- If neither expected nor actual result is mentioned
- If the component/feature affected is completely unknown

**Try to create the defect report with the information provided, and only ask 1-2 essential questions maximum if really necessary.**

When you have sufficient information, create a professional defect report with the following structure:

**TITLE/SUMMARY:**
- Clear, concise description of the issue
- Include what component/feature is affected

**DESCRIPTION:**
- Detailed explanation of the problem
- Context about when/where it occurs
- Impact on the system or users

**STEPS TO REPRODUCE:**
Format as detailed, numbered steps with point-wise details:
- Use numbered format (1., 2., 3., etc.)
- Each step should be specific and detailed
- Break down complex actions into sub-points if needed
- Include any prerequisites or setup steps
- Mention any specific modules, pages, or components
- Include relevant test data or configurations
- Each step should be actionable and clear

**EXPECTED RESULT:**
Format as point-wise list:
- List what should happen when following the steps
- Use bullet points for each expected behavior
- Be specific about expected outcomes
- Include expected system responses or behaviors
- Mention expected user experience

**ACTUAL RESULT:**
Format as point-wise list:
- List what actually happens (different from expected)
- Use bullet points for each actual behavior observed
- Include specific error messages if any
- Describe incorrect behavior or unexpected output
- Mention any observations during execution
- Note any workarounds or alternative behaviors observed

Guidelines:
- **IMPORTANT: Only ask questions if ABSOLUTELY CRITICAL information is missing**
- Do NOT ask too many questions - infer reasonable details from context
- Use your intelligence to fill in reasonable assumptions for minor missing details
- Only ask 1-2 essential questions maximum if really necessary
- Ask for missing information only if it's truly critical for the defect report
- If steps, expected result, or actual result are partially mentioned, infer and create the report
- Be smart and practical - create the best defect report possible with available information
- Format all sections with detailed point-wise information (use bullet points)
- Make steps detailed and comprehensive - break down complex actions
- Ensure all sections are clear, professional, and well-structured
- Use technical language appropriate for QA teams
- Maintain professional QA documentation standards
- Remember context from previous messages in the conversation
- Only include the sections listed above - do not add ENVIRONMENT/SETUP, PRIORITY, or ADDITIONAL NOTES sections
- Each section should be detailed with multiple bullet points, not just one sentence

Current conversation:
{history}
Human: {input}
QA Assistant:"""

# Create prompt templates
qa_prompt = PromptTemplate(
    input_variables=["history", "input"],
    template=qa_chat_template
)

normal_prompt = PromptTemplate(
    input_variables=["history", "input"],
    template=normal_chat_template
)

# Initialize memory for both modes (stores conversation history)
qa_memory = ConversationBufferMemory(return_messages=True)
normal_memory = ConversationBufferMemory(return_messages=True)

# Create conversation chains with memory
qa_conversation_chain = ConversationChain(
    llm=llm,
    memory=qa_memory,
    prompt=qa_prompt,
    verbose=False
)

normal_conversation_chain = ConversationChain(
    llm=llm,
    memory=normal_memory,
    prompt=normal_prompt,
    verbose=False
)

def get_chat_response(user_input: str, mode: str = "qa") -> str:
    """
    Get response from the chat chain with memory
    
    Args:
        user_input: User's message
        mode: "qa" for QA Assistant mode or "normal" for normal chat
        
    Returns:
        AI's response
    """
    try:
        # Select the appropriate conversation chain based on mode
        chain = qa_conversation_chain if mode == "qa" else normal_conversation_chain
        
        # Try invoke method first (newer API), fallback to predict
        try:
            response = chain.invoke({"input": user_input})
            return response.get("response", str(response))
        except (AttributeError, TypeError):
            # Fallback to predict method for older LangChain versions
            response = chain.predict(input=user_input)
            return response
    except Exception as e:
        error_msg = str(e)
        error_lower = error_msg.lower()
        
        # Provide user-friendly error messages without exposing sensitive details
        if "connection" in error_lower or "timeout" in error_lower or "connect" in error_lower:
            return "❌ **Connection Error**\n\nUnable to connect to the AI service. Please check:\n• Your internet connection\n• Service availability\n• Network settings"
        
        elif "authentication" in error_lower or "unauthorized" in error_lower or "api key" in error_lower:
            return "❌ **Authentication Error**\n\nInvalid API credentials. Please verify your configuration in the `.env` file."
        
        elif "endpoint" in error_lower or "url" in error_lower:
            return "❌ **Configuration Error**\n\nInvalid service endpoint configuration. Please check your `.env` file settings."
        
        elif "rate limit" in error_lower or "quota" in error_lower:
            return "❌ **Rate Limit Exceeded**\n\nToo many requests. Please wait a moment and try again."
        
        elif "model" in error_lower and ("not found" in error_lower or "deployment" in error_lower):
            return "❌ **Model Error**\n\nThe requested AI model is not available. Please check your model configuration."
        
        else:
            # Generic error without exposing details
            return "❌ **Error**\n\nSomething went wrong while processing your request. Please try again or check your configuration."

def clear_memory(mode: str = "qa"):
    """Clear the conversation memory"""
    global qa_memory, normal_memory, qa_conversation_chain, normal_conversation_chain
    
    if mode == "qa":
        qa_memory.clear()
        # Recreate chain with fresh memory
        qa_conversation_chain = ConversationChain(
            llm=llm,
            memory=qa_memory,
            prompt=qa_prompt,
            verbose=False
        )
    else:
        normal_memory.clear()
        # Recreate chain with fresh memory
        normal_conversation_chain = ConversationChain(
            llm=llm,
            memory=normal_memory,
            prompt=normal_prompt,
            verbose=False
        )

def get_memory_messages(mode: str = "qa"):
    """Get all messages from memory"""
    memory = qa_memory if mode == "qa" else normal_memory
    return memory.chat_memory.messages if memory.chat_memory else []

# Keep conversation_chain for backward compatibility
conversation_chain = qa_conversation_chain

