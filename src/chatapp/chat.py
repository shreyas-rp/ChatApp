import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

# Access the environment variables
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

# Initialize the LLM
llm = AzureChatOpenAI(
    model_name="gpt-4o",
    azure_endpoint=endpoint,
    api_key=api_key,
    api_version=api_version,
    temperature=0.7  # Add some creativity for chat
)

# Create a custom prompt template for chat
chat_template = """The following is a friendly conversation between a human and an AI assistant. 
The AI is helpful, knowledgeable, and provides detailed, thoughtful responses. The AI remembers previous parts of the conversation.

Current conversation:
{history}
Human: {input}
AI Assistant:"""

# Create prompt template
chat_prompt = PromptTemplate(
    input_variables=["history", "input"],
    template=chat_template
)

# Initialize memory (stores conversation history)
memory = ConversationBufferMemory(return_messages=True)

# Create conversation chain with memory
conversation_chain = ConversationChain(
    llm=llm,
    memory=memory,
    prompt=chat_prompt,
    verbose=False
)

def get_chat_response(user_input: str) -> str:
    """
    Get response from the chat chain with memory
    
    Args:
        user_input: User's message
        
    Returns:
        AI's response
    """
    try:
        # Try invoke method first (newer API), fallback to predict
        try:
            response = conversation_chain.invoke({"input": user_input})
            return response.get("response", str(response))
        except (AttributeError, TypeError):
            # Fallback to predict method for older LangChain versions
            response = conversation_chain.predict(input=user_input)
            return response
    except Exception as e:
        return f"Error: {str(e)}"

def clear_memory():
    """Clear the conversation memory"""
    global memory, conversation_chain
    memory.clear()
    # Recreate chain with fresh memory
    conversation_chain = ConversationChain(
        llm=llm,
        memory=memory,
        prompt=chat_prompt,
        verbose=False
    )

def get_memory_messages():
    """Get all messages from memory"""
    return memory.chat_memory.messages if memory.chat_memory else []

