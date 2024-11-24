import sys
import os
import psutil
import time

from persistent_data.ui_session_data_mgmt import *
from typing import Optional, Tuple
from server_data.ui_server_side_data import *

import langchain

from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder

from langchain.memory import ConversationBufferMemory

from langchain.globals import set_debug


#################################
# For OpenAI, use the following:
#################################
# from langchain_openai import ChatOpenAI

#################################
# For Gemini, use the following:
#################################
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain.schema import HumanMessage, AIMessage

import pdfplumber
import logging

# Set up logging configuration - uncomment when needed
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('debug.log', mode='w'),
#         logging.StreamHandler()  # This will print to console
#     ]
# )
# # Loggers for specific components - uncomment when needed
# # Specifically restrict pdfminer logging to WARNING level
# # it shpuld be used sparingly, as it is a resource HOG
# logging.getLogger('pdfminer').setLevel(logging.WARNING)
# logging.getLogger('langchain').setLevel(logging.WARNING)  # Suppress most LangChain logs
# logging.getLogger('urllib3').setLevel(logging.WARNING)   # Suppress HTTP request logs
# logging.getLogger('google').setLevel(logging.WARNING)    # If using Google/Gemini

# # Create our conversation-specific debug logger
# conversation_logger = logging.getLogger(__name__)
# conversation_logger.setLevel(logging.DEBUG)


# # Create a separate handler for LangChain-specific logging
# langchain_logger = logging.getLogger('langchain')
# langchain_handler = logging.FileHandler('langchain_debug.log')
# langchain_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
# langchain_logger.addHandler(langchain_handler)

# Configure LangChain debug logging
set_debug(False)  


def truncate_str(s: str, length: int = 100) -> str:
    """Truncate a string to length chars and add ellipsis if truncated."""
    return s[:length] + '...' if len(s) > length else s

import textwrap


class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors.""" 
    pass # These can actually be blank classes. We will pass a custom message through them if/when they are raised.

class FileWriteError(Exception):
    """Custom exception for file writing errors."""
    pass

class FileReadError(Exception):
    """Custom exception for file reading errors."""
    pass


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# This is some weird python majic that allows this file (which is in a subdirectory) to
#  access a function in the main project directory


############################
# Set up all the Langchain components for 
#       - system message
#       - additional prompt instructions used with an insurance policy upload
#       - additional prompt contents - the text of an insurance policy
#       - prompt structure
#       - model parameters
#       - conversation memory
#       - the Conversation Chain



# Start by defining the system messaage:
system_message = """Acting as an expert in U.S. personal insurance, please answer questions from the user in a helpful and supportive way about Life Insurance, Disability Insurance, Long Term Care Insurance, Auto Insurance, Umbrella Insurance, Pet Insurance, and Homeowners Insurance (including Condo insurance and Renters insurance), or about their previous questions in the current conversation. If the user asks a question about a different type of insurance, reply that you are not trained to discuss those types of insurance but would be happy to talk to them about Life Insurance, Disability Insurance, Long Term Care Insurance, Auto Insurance, Umbrella Insurance, Pet Insurance, and Homeowner's, Condo, and Renter's Insurance. If the user asks a question about a particular insurance policy, but no policy has been provided, politely invite them to select a policy from the radio buttons on the left of the screen, or upload a policy to the Insutrance Portal. If the user asks a question outside the realm of personal insurance in the United States (unless it is a question about this conversation) politely answer that you would love to help them, but are only trained to discuss issues and questions regarding personal insurance in the U.S. Users may be quite new to the domain of insurance so it is very important that you are welcoming and helpful, and that answers are complete and correct. Please err on the side of completeness rather than on the side of brevity, and always be truthful and accurate. And this is very important: please let the user know that they should always contact an insurance professional before making any important decisions."""

saved_policy_instructions = """Please use the following policy document as the primary source of information for answering the user's next query.  If you cannot find that information in the policy, please clearly but state that. If you can answer the question using your general knowledge about insurance, but please clearly state that as well. Always prioritize the specific policy details over general knowledge."""

policy_instructions = ""
policy_extracted_content = ""

# Set up the memory
memory = ConversationBufferMemory(return_messages=True) #ConversationBuffer
'''ConversationBufferMemory is a Langchain class that automajically stores the conversation history as a buffer. It labels which strings belong to "HumanMessage" (user) input and which belong to "AIMessage" (bot) output. return_messages=True configures the memory to return the history as a list of messages, which is compatible with chat models.'''




# Set up the language model

#################################
# For OpenAI, use the following:
#################################
# model = ChatOpenAI(
#     model="gpt-4o",     # Specify the preferred model
#     temperature=0.7,    # control the amount of randomness in replies
#     streaming=True      # Enable Streaming
# )

#################################
# For Gemini, use the following:
#################################
model = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.7,
    convert_messages_to_prompt=False, # We are managing the convo history ourselves, as we do not want it to include the insurancy polcy text, and the policy instructions if/when they are present.
    streaming=True
)

#################################
# For OpenAI, use the following:
#################################
# Create the prompt template
# prompt = ChatPromptTemplate.from_messages([ # Langchain will automatically fill in the history and input
#                                             # placeholders with the current conversation history and user
#                                             # query, creating a complete prompt for the language model.
#     SystemMessagePromptTemplate.from_template(system_message), # used for strings
#     SystemMessagePromptTemplate.from_template("{policy_instructions}"),# used for strings
#     SystemMessagePromptTemplate.from_template("{policy_content}"), # used for strings
#     MessagesPlaceholder(variable_name="history"), # used for LISTS of strings
#     HumanMessagePromptTemplate.from_template("{input}")# used for strings
# ])

#################################
# For Gemini, use the following:
#################################
# Create the prompt template
# But we need to modify how we structure the prompt and chain to keep system/policy content separate
prompt = ChatPromptTemplate.from_messages([
    # First message combines system content and instructions
    ("human", "System Instructions:\n{system_template}\n\nPolicy Instructions:\n{policy_instructions}\n\nPolicy Content:\n{policy_content}"),
    # Then include conversation history
    MessagesPlaceholder(variable_name="history"),
    # Finally, the current user query
    ("human", "{input}")
])



# Create the runnable chain (using the "pipe" operator as we would in Unix shells)
# This setup does a few important things:
# It creates a chain that formats our prompt and sends it to the model.
# It wraps this chain with conversation history management.
# It ensures that each time we use this chain, it will automatically:
    # Retrieve the conversation history
    # Add the new input to the history
    # Format the prompt with the full history
    # Send it to the model
    # Save the response back to the history
# This approach simplifies the management of conversation history and makes it easier to maintain context across multiple interactions in a chat session.

# Create the runnable chain
# Modified chain to separate system prompt, policy instructions & content
def create_chain():
    """Create a new chain with current global settings."""
    return (
        {
            "system_template": lambda x: system_message,  # Constant system message
            "policy_instructions": lambda x: x["policy_instructions"],
            "policy_content": lambda x: x["policy_content"],
            "input": lambda x: x["input"],
            "history": lambda x: format_history_for_gemini(memory.load_memory_variables({})["history"])
        }
        | prompt
        | model
    )

# Initial chain creation
chain = create_chain()


####################################
# Focus Handler
####################################

def handle_focus(session_state: SessionData, 
                 user_id: str, # would be passed to Chatbot from server
                 session_id: str, # would be passed to Chatbot from server
                 server_users: ServerUserDataCollection) -> None: # would be passed to Chatbot from server
    """
    Handle Focus.
        session_state: is used to manage the data that the chatbot needs to "remember" for the entire session across going in and out of focus.
        The last three function arguments represent data that would be available though the server

    This function processes the focus event for the chatbot. 
    --> WE ARE ASSUMING THAT WHEN FOCUS LANDS ON THE CHATBOT, IT IS AT THE VERY LEAST PASSED THE 
    --> USER ID OF THE CURRENT USER. 
    When focus is switched to the chatbot:
        If the session is not yet initialized, (i.e., no session state object exists for this user_id), this handler creates one.
        This will create a new SessionData object with:
        - The initialization flag set to False
        - The user_id set to ""
        - The number of policies uploaded by this user set to 0
        - The collection of policy objects for this user set to None
        - The currently selected policy set to None
    --> The intialization flag is then set to True
    --> and the actual user_id is filled in

    --> The rest of the handler is executed everytime it is called, whether or nor the initialization has been run.
    --> Using the user_id, the retrieval or at last the copying of the stored data from the server is emulated. This action includes copying and storing:
        - The number of policies uploaded by the user (which may have changed since the last time the chatbot was in focus
            
        - And for each policy uploaded:
            - file_id: str  # Unique identifier for the policy file
            - path:   str # URL or file path
            - policy_type: str  # Type of policy (e.g., "auto", "home")
            - print_name: str  # Display name for the policy
            - carrier: str  # Insurance carrier name
            - format: str  # File format (e.g., "pdf", "docx")
            - additional_metadata: Optional[Dict] = None  # Optional dictionary for extra information 
            - the currently chosen policy is kept at its current value ("which may be none") as the UI is not yet rendered.
    --> Now that the session_state is up to date, the UI can be rendered.
    --> Note that the conversation history will be kept by Langchain as it is a compoenent of the prompt template, and the UI render will need to get that data from Langchain
    
    Args:
        session_state: SessionData. # The current session state, or "None"
        The user ID

    Returns:
        None

    Raises:
    TBD
"""
    session_state.user_id = user_id
    session_state.session_id = session_id
    # the following is only executed the fist time the Chatbot receives focus or when the session is restarted by the tester
    if session_state.get_is_initialized() == False:
        session_state.selected_policy = "None"
        session_state.selected_policy_index = None # ints can be initialized to None
        session_state.is_initialized = True
        
    ###############################################################################################
    # --> IN THE ACTUAL SYSTEM, THE DATA ON THE SERVER WOULD BE ACCESSIBLE VIA API OR OTHER METHOD 
    # --> AND WOULD NOT BE PASSED AS A PARAMETER TO THIS FUNCTION                                  
    ##############################################################################################
 

    # The following would be executed EVERY TIME the chatbot receives focus, including the first, as this data may have changed. E.g., the user may have deleted and/or uploaded some policies since the chatbot last had focus. 
    
    transfer_server_data_for_current_user(session_state, server_users) 




def transfer_server_data_for_current_user(session_state: SessionData, server_users: ServerUserDataCollection) -> None:

    # First get the userID for this session's user
    user_id = session_state.user_id

    # Use user_id as a key to find data for that specific user
    try:
        server_user_data = server_users[user_id]
    except KeyError:
        print(f"User with id {user_id} not found")
    
    session_state.first_name = server_user_data.first_name
    session_state.last_name = server_user_data.last_name

    # Next get the info about that user's uploaded insurance policies
    session_state.policy_list = get_policy_file_info(session_state, user_id, server_user_data)

    



def get_policy_file_info(session_state: SessionData, 
                         user_id: str, 
                         server_user: ServerUserData) -> None:
    
     # the set of uploaded policies may have changed since the last focus even, so reinitialize
    policy_count = 0    # the set of uploaded policies may have changed since the last focus event
    session_state.policy_list=[] # initialize as empty list
    
    for policy in server_user.policies:  # Number of policeis uploaded can be 0 
        sesh_policy = Policy() # create a fresh Policy instance
        sesh_policy.file_id = policy.file_id # Unique identifier for the policy file
        sesh_policy.path = policy.path # URL or file path
        sesh_policy.policy_type = policy.policy_type # Type of policy (e.g., "auto", "home")
        sesh_policy.print_name = policy.print_name # Display name for the policy
        sesh_policy.carrier = policy.carrier # Insurance carrier name
        sesh_policy.format = policy.format # File format (e.g., "pdf", "docx", "md")
        sesh_policy.is_extracted = policy.is_extracted
        sesh_policy.extracted_file_path = policy.extracted_file_path
        sesh_policy.additional_metadata = policy.addl_metadata # Optional dictionary for extra information which can either be a dict or None
        
        session_state.policy_list.append(sesh_policy)
        policy_count += 1

    session_state.number_policies = policy_count
    if (policy_count > 0):
        session_state.current_policy = "None" # for users with at least 1 policy uploaded, the "None" button is the default policy selector button
    return(session_state.policy_list)


####################################
# Query Handler
####################################
def handle_query(user_input: str, session_state: SessionData, user_id: str) -> None:

    policy = ""
    policy_instructions = ""
    policy_content = ""

    # First check if there are any policies uploaded or selected
    if (session_state.number_policies is not None and 
        session_state.number_policies > 0 and 
        session_state.selected_policy_index is not None and 
        session_state.selected_policy != "None"):
        # A policy has been selected
        index = session_state.selected_policy_index
        policy = session_state.policy_list[index] # will need this to (Optionally) extract the txt from the .pdf and then (Always) add the text and the additional instructions to the prompt through the template

            
        if (not (policy.is_extracted)):
            process_pdf_file(policy, session_state)
            
        policy_content = read_from_extracted_file(policy.extracted_file_path) # python chokes on very large strings passed back to the caller, so we force a read from the converted file even for the initial conversion to txt
        policy_instructions = saved_policy_instructions

    
    
    history = memory.load_memory_variables({})["history"]


    buffer_chunks = []  # Use list instead of string concatenation, IMPORTANT! Strings cause very long lag
    full_response_chunks = []  # Use list instead of string concatenation, IMPORTANT! Strings cause very long lag

    try:
        for chunk in chain.stream({
            "input": user_input,
            "policy_instructions": policy_instructions,
            "policy_content": policy_content,
            "history": memory.load_memory_variables({})["history"]
        }):

            # Enhanced content extraction
            content = None
            if hasattr(chunk, 'content'):
                content = chunk.content
            elif hasattr(chunk, 'message') and hasattr(chunk.message, 'content'):
                content = chunk.message.content
            
            if content:
                buffer_chunks.append(content)
                full_response_chunks.append(content)

                # Join buffer chunks only when we need to check/send
                buffer = ''.join(buffer_chunks)
                while len(buffer) >= 50:
                    send_chunk = buffer[:50]
                    buffer = buffer[50:]
                    buffer_chunks = [buffer]  # Reset buffer_chunks with remaining content
                    send_chunk = send_chunk.replace('\n', '\\n')
                    yield send_chunk

        # Handle any remaining buffer content
        if buffer_chunks:
            final_buffer = ''.join(buffer_chunks)
            if final_buffer:
                final_buffer = final_buffer.replace('\n', '\\n')
                yield final_buffer

        # Join full response chunks only once at the end
        full_response = ''.join(full_response_chunks)

        if not full_response:

            full_response = "I apologize, but I encountered an error processing your request. Could you please rephrase your question?"

        memory.save_context({"input": user_input}, {"output": full_response})

        
    except Exception as e:
        conversation_logger.error(f"Error in chat stream: {str(e)}", exc_info=True)
        yield "I apologize, but I encountered an error. Please try again."

    yield "DONE"


def format_history_for_gemini(history):
    """Format conversation history while maintaining message objects"""


    seen_messages = set()  # Track unique messages
    formatted_messages = []
    
    for i, msg in enumerate(history):
        content = str(msg.content)

        # Only add message if we haven't seen it before
        if content not in seen_messages:
            formatted_messages.append(msg)  # Keep the original message object
            seen_messages.add(content)

    return formatted_messages  # Return list of message objects, not strings


    # Add this diagnostic helper
def log_conversation_state(history, logger):
    """Debug helper to log conversation state"""
    logger.debug("\n=== Conversation State Analysis ===")
    logger.debug(f"Number of messages: {len(history)}")
    total_tokens = 0
    
    for i, msg in enumerate(history):
        msg_content = str(msg.content) if hasattr(msg, 'content') else 'No content'
        msg_length = len(msg_content)
        logger.debug(f"\nMessage {i}:")
        logger.debug(f"Type: {type(msg)}")
        logger.debug(f"Message type: {msg.type if hasattr(msg, 'type') else 'unknown'}")
        logger.debug(f"Length: {msg_length}")
        logger.debug(f"Preview: {truncate_str(msg_content)}")
        total_tokens += msg_length

    logger.debug(f"\nTotal approximate token length: {total_tokens}")
    logger.debug("===================================")


    
def process_pdf_file(policy: Policy, session_state: SessionData):
    '''Create a text file from the pdf file by: 
            1) Converting the .pdf to a text string
            2) Save the text in a file with the same name but with a .txt extentension
            3) Store the path to the converted file in the session_state
            4) Set is_extracted to True in the session_state

    '''
  
    file_contents = extract_text_from_pdf_file (policy)
 
    txt_file_path = write_text_to_txt_file (file_contents, policy)
 
    policy.extracted_file_path = txt_file_path
    policy.is_extracted = True
   

 
def extract_text_from_pdf_file(policy: Policy) -> str:
    try:
        # print("\n=== Container Resource Information ===")
        # print_container_limits()  # Add this here to check limits before starting
        # print(f"Initial resource usage - {get_container_resource_usage()}")
        # print("=====================================\n")
        
        text_parts = []

        with pdfplumber.open(policy.path) as pdf:
            total_pages = len(pdf.pages)

            for i, page in enumerate(pdf.pages):
                
    
                
                extracted_text = page.extract_text()
                

                if extracted_text:  # Guard against None or empty strings
                    text_parts.append(extracted_text)
            
    
         
        return "\n\n".join(text_parts)
    except Exception as e:
        raise PDFExtractionError(f"Failed to extract text from PDF: {str(e)}")


def write_text_to_txt_file (file_contents: str, policy: Policy) -> str:
    
    txt_file_path = create_txt_file_path(policy.path)

    try:
        with open(txt_file_path, 'w', encoding='utf-8') as file:
            file.write(file_contents)
            return(txt_file_path)
    except Exception as e:
        raise FileWriteError(f"Failed to write text to file: {str(e)}")
    

def create_txt_file_path(pdf_file_path: str) -> str:

     # Split the path into the directory path, filename, and extension
    directory, filename = os.path.split(pdf_file_path)
    name, _ = os.path.splitext(filename)
    
    # Create the new filename with .txt extension
    new_filename = name + '.txt'

    # Create full path
    # Join the directory path with the new filename
    txt_file_path = os.path.join(directory, new_filename)
    
    
    return (txt_file_path)


def read_from_extracted_file(file_path: str) -> str:

    try:
        with open(file_path, 'r') as file:
            content = file.read()

        
    except FileNotFoundError:
        print("Error: The file was not found.")
    except IOError:
        print("Error: There was an issue reading the file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    else:
        return(content)
    

####################################
# Policy Selection Handler
####################################

def handle_policy_selection(session_state: SessionData, user_id: str, selected_policy: str) -> None:
   
    
    if selected_policy == "None":
        session_state.selected_policy = 'None'
        session_state.selected_policy_index = None
    else:
        for index, policy in enumerate(session_state.policy_list):
            if policy.print_name == selected_policy:
                session_state.selected_policy = policy
                session_state.selected_policy_index = index
                break
        else:
            print(f"Warning: Selected policy '{selected_policy}' not found")
    

            





####################################
# Clear Button Click Handler
####################################

def handle_clear_button_click(session_state, user_id):
    '''Clear the conversation by resetting memory, policy data, and chain state.The key to clearing the conversation is to clear the memory. But  we should also clear the policy instructions and the policy content. We recreate the chain itself to insure that all values, including history and input are reset. Finally, session state values are reinitialized by setting the selected policy to the str "None" and the selected policy's index to None.
    '''
    global memory, chain, policy_instructions, policy_extracted_content
    

    
    global memory, chain, policy_instructions, policy_extracted_content
    
    # Log memory state before clearing
    initial_history = memory.load_memory_variables({})["history"]

    
    # Clear the Langchain conversation memory
    memory.clear()

    # Verify memory is cleared
    cleared_history = memory.load_memory_variables({})["history"]

    

    # Clear policy instructions and policy content
    policy_instructions = ""
    policy_extracted_content = ""
  
    # Recreate chain to ensure completely fresh state
    chain = create_chain()

    
    # Reset the selected policy
    session_state.selected_policy = "None"
    session_state.selected_policy_index = None


    
#######################
# Debugging utilities
#######################

# docker resource utilities for debugging
def get_container_resource_usage():
    try:
        process = psutil.Process(os.getpid())
        cpu_percent = process.cpu_percent(interval=0.1)
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
        return f"CPU Usage: {cpu_percent}%, Memory: {memory_mb:.2f}MB"
    except Exception as e:
        return f"Error getting resource usage: {e}"

def print_container_limits():
    try:
        with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
            memory_limit = int(f.read().strip()) / (1024 * 1024)  # Convert to MB
            print(f"Container memory limit: {memory_limit:.2f}MB")
    except Exception as e:
        print(f"Could not read container limits: {e}")

