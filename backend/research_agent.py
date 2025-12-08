"""
Simple conversational agent with LangGraph.
Maintains conversation history and includes a think tool for reasoning.
"""
import operator
import os
import uuid
from typing import TypedDict, Annotated, List, Optional
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from langgraph.prebuilt import ToolNode

from utils.db_config import create_checkpointer

load_dotenv()

# --- CONFIGURATION ---

# Using Groq model for good reasoning capabilities with streaming enabled
configurable_model = ChatGroq(model="openai/gpt-oss-120b", temperature=0, streaming=True)

# --- STATE DEFINITION ---

class AgentState(TypedDict):
    """State for the conversational agent."""
    conversation_history: Annotated[List[str], operator.add]  # Accumulates conversation messages
    final_response: str  # Final response from the agent
    user_message: str  # Current user message

# --- THINK TOOL ---

@tool
def think(thought: str) -> str:
    """
    Use this tool to share your reasoning process or think through a problem step by step.
    
    Args:
        thought: Your reasoning or thought process to share
        
    Returns:
        Confirmation message
    """
    writer = get_stream_writer()
    if writer:
        writer({"event": "thinking", "thought": thought})
    return f"Thought: {thought}"

# --- AGENT NODE ---

def agent_node(state: AgentState):
    """
    Processes user messages using LLM with conversation history and tool calling.
    """
    try:
        writer = get_stream_writer()
        
        # Get current user message
        user_message = state.get("user_message", "")
        
        # Build conversation history from state
        messages = []
        
        # Add system message
        system_prompt = """You are a helpful conversational assistant. 
You can use the think tool to share your reasoning process when working through complex problems.
Always be helpful, accurate, and concise in your responses."""
        messages.append(SystemMessage(content=system_prompt))
        
        # Reconstruct conversation from history
        # conversation_history is a list of strings, alternating user/assistant messages
        for msg in state.get("conversation_history", []):
            # Simple heuristic: if it starts with "User:" it's a user message, else assistant
            if msg.startswith("User: ") or msg.startswith("Human: "):
                messages.append(HumanMessage(content=msg.replace("User: ", "").replace("Human: ", "")))
            elif msg.startswith("Assistant: ") or msg.startswith("AI: "):
                messages.append(AIMessage(content=msg.replace("Assistant: ", "").replace("AI: ", "")))
            else:
                # Default: treat as user message if we can't determine
                messages.append(HumanMessage(content=msg))
        
        # Add current user message
        messages.append(HumanMessage(content=user_message))
        
        # Bind tools to model
        model_with_tools = configurable_model.bind_tools([think])
        tool_node = ToolNode([think])
        
        # Handle multiple rounds of tool calls until we get a final text response
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        response_text = ""
        
        while iteration < max_iterations:
            iteration += 1
            
            # Stream response from model token by token
            full_response = ""
            response_chunks = []
            
            for chunk in model_with_tools.stream(messages):
                response_chunks.append(chunk)
                
                # Check if this chunk has content to stream
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    full_response += content
                    
                    # Stream each token chunk to the user
                    if writer:
                        writer({
                            "event": "token",
                            "content": content
                        })
            
            # Accumulate all chunks into a single response message for tool call detection
            response = None
            if response_chunks:
                response = response_chunks[0]
                for chunk in response_chunks[1:]:
                    try:
                        response = response + chunk
                    except:
                        # If merging fails, use the last chunk
                        response = chunk
            
            if not response:
                response_text = full_response
                break
            
            tool_calls = getattr(response, 'tool_calls', None) or []
            
            if tool_calls:
                # Emit tool call events
                for tool_call in tool_calls:
                    if writer:
                        tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "unknown")
                        tool_args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
                        writer({
                            "event": "tool_call",
                            "tool": tool_name,
                            "input": tool_args
                        })
                
                # Execute tool calls using ToolNode
                tool_responses = tool_node.invoke({"messages": [response]})
                
                # Add tool responses to messages for next iteration
                messages.append(response)  # Add the tool-calling message
                messages.extend(tool_responses["messages"])  # Add tool responses
                
                # Continue loop to get next response (may have more tool calls or final text)
                continue
            else:
                # No tool calls, this is the final response
                response_text = full_response
                break
        
        # If we hit max iterations, use the last response
        if iteration >= max_iterations and not response_text:
            response_text = full_response if 'full_response' in locals() else ""
        
        # Get existing conversation history from state
        # Note: Due to operator.add, state.get() returns accumulated history from checkpointer
        # When initial_state has conversation_history: [], LangGraph merges it with persisted state
        # So state.get() here should return the persisted history, not what we put in initial_state
        existing_history = state.get("conversation_history", [])
        
        # Update conversation history - append new messages to existing history
        conversation_updates = [
            f"User: {user_message}",
            f"Assistant: {response_text}"
        ]
        
        # Because conversation_history uses operator.add, we only return the NEW messages
        # LangGraph will add them to what's already persisted in the checkpointer
        # Check if we're duplicating - if the last message matches, don't add
        if existing_history and len(existing_history) >= 2:
            last_user = existing_history[-2] if len(existing_history) >= 2 else None
            last_assistant = existing_history[-1] if len(existing_history) >= 1 else None
            if last_user == conversation_updates[0] and last_assistant == conversation_updates[1]:
                conversation_updates = []  # Don't add duplicates
        
        result = {
            "conversation_history": conversation_updates,  # This will be added to existing via operator.add
            "final_response": response_text
        }
        
        # Emit final response event
        if writer:
            writer({"event": "response", "content": response_text})
        
        return result
        
    except Exception as e:
        writer = get_stream_writer()
        if writer:
            writer({"event": "error", "node": "agent", "error": str(e)})
        print(f"Error in agent_node: {e}")
        raise

# --- GRAPH SETUP ---

# Create checkpointer if database is configured
_checkpointer = create_checkpointer()
_checkpointer_setup_done = False

def ensure_checkpointer_setup():
    """Ensure checkpointer setup is called once."""
    global _checkpointer_setup_done, _checkpointer
    if _checkpointer and not _checkpointer_setup_done:
        try:
            if hasattr(_checkpointer, 'setup'):
                _checkpointer.setup()
            _checkpointer_setup_done = True
        except Exception as e:
            print(f"Warning: Failed to setup checkpointer: {e}")
            print("Continuing without checkpointing...")
            _checkpointer = None

# Build graph
builder = StateGraph(AgentState)
builder.add_node("agent", agent_node)
builder.add_edge(START, "agent")
builder.add_edge("agent", END)

# Compile graph with checkpointer if available
if _checkpointer:
    ensure_checkpointer_setup()
    if _checkpointer:
        agent_graph = builder.compile(checkpointer=_checkpointer)
    else:
        agent_graph = builder.compile()
else:
    agent_graph = builder.compile()

# --- EXECUTION FUNCTION ---

def run_agent(message: str, thread_id: Optional[str] = None):
    """
    Run the conversational agent with streaming support.
    
    Args:
        message: The user's message
        thread_id: Optional thread ID for checkpointing. If None and checkpointing is available,
                   a new thread_id will be generated.
    
    Yields:
        Tuples of (mode, data) from LangGraph stream
    """
    # Generate thread_id if not provided and checkpointing is available
    if thread_id is None and _checkpointer:
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    
    # Create config with thread_id if checkpointing is available
    config = {}
    if _checkpointer and thread_id:
        config = {"configurable": {"thread_id": thread_id}}
    
    # Check if this is a follow-up (existing thread with state)
    is_follow_up = False
    existing_state = None
    if _checkpointer and thread_id:
        try:
            existing_state_snapshot = agent_graph.get_state(config)
            if existing_state_snapshot and existing_state_snapshot.values:
                existing_state = existing_state_snapshot.values
                is_follow_up = True
        except Exception:
            # Thread doesn't exist yet, start fresh
            pass
    
    # Initialize state
    # IMPORTANT: Do NOT include conversation_history in initial_state when using operator.add
    # The agent_node will read it from the checkpointer state via state.get() which gets the persisted state
    # Including it here causes duplication because operator.add adds returned values to what's in initial_state
    if is_follow_up and existing_state:
        initial_state = {
            "user_message": message,
            "conversation_history": [],  # Start empty - agent_node reads from checkpointer state
            "final_response": existing_state.get("final_response", "")
        }
    else:
        initial_state = {
            "user_message": message,
            "conversation_history": [],
            "final_response": ""
        }
    
    # Stream graph execution
    # Note: thread_id will be available in config for checkpointing
    # We yield it as a special event before streaming
    if thread_id:
        yield ("custom", {"event": "thread_id", "thread_id": thread_id})
    
    for mode, data in agent_graph.stream(initial_state, config=config if config else None, stream_mode=["custom", "updates"]):
        yield mode, data

