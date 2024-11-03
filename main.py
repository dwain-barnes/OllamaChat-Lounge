import streamlit as st
from swarm import Swarm, Agent
import random
import asyncio
import os
import time
import json
from datetime import datetime
import nest_asyncio
import requests
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

nest_asyncio.apply()

# Configure Ollama
os.environ["OPENAI_API_KEY"] = "fake-key"
os.environ["OPENAI_BASE_URL"] = "http://localhost:11434/v1"

# Initialize Swarm client
client = Swarm()

# Function to get local Ollama models
def get_ollama_models():
    try:
        logger.info("🔍 Fetching available Ollama models...")
        response = requests.get('http://localhost:11434/api/tags')
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            logger.info(f"✅ Found models: {model_names}")
            return model_names
        logger.warning("⚠️ Failed to fetch models, using defaults")
        return ["mistral", "llama2", "codellama"]
    except Exception as e:
        logger.error(f"❌ Error fetching models: {str(e)}")
        return ["mistral", "llama2", "codellama"]

# Function to get available remote models
def get_available_remote_models():
    """Get list of models available for download"""
    try:
        return [
            "llama2",
            "mistral",
            "codellama",
            "llama2-uncensored",
            "neural-chat",
            "starling-lm",
            "orca-mini",
            "vicuna",
            "zephyr"
        ]
    except Exception as e:
        logger.error(f"❌ Error getting remote models: {str(e)}")
        return []

# Function to pull model from Ollama
def pull_ollama_model(model_name):
    """Pull a model from Ollama"""
    try:
        logger.info(f"🚀 Starting download of model: {model_name}")
        response = requests.post(
            'http://localhost:11434/api/pull',
            json={'name': model_name},
            stream=True
        )
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if 'status' in data:
                    logger.info(f"📥 {model_name}: {data.get('status')} - {data.get('completed', '')} {data.get('total', '')}")
                    status_text.text(f"Status: {data.get('status')}")
                    
                    if 'completed' in data and 'total' in data:
                        try:
                            progress = int(data['completed']) / int(data['total'])
                            progress_bar.progress(progress)
                        except:
                            pass
                            
                if data.get('status') == 'success':
                    logger.info(f"✅ Successfully downloaded {model_name}")
                    progress_bar.progress(1.0)
                    return True
        return False
    except Exception as e:
        logger.error(f"❌ Error pulling model: {str(e)}")
        return False

def get_agent_response(agent, messages):
    try:
        if agent.name == "Alice":
            model = st.session_state.alice_model
            agent.model = model
            logger.info(f"🔄 Alice is using model: {model}")
        else:
            model = st.session_state.bob_model
            agent.model = model
            logger.info(f"🔄 Bob is using model: {model}")
        
        logger.info(f"📤 {agent.name} sending message: {messages[-1]['content']}")
        
        response = client.run(
            agent=agent,
            messages=messages,
            context_variables={}
        )
        
        if response and response.messages:
            logger.info(f"📥 {agent.name} received response: {response.messages[-1]['content']}")
        
        return response
    except Exception as e:
        logger.error(f"❌ Error with {agent.name}'s response using {model}: {str(e)}")
        st.error(f"Error: {e}")
        return None

def add_message(user, content):
    timestamp = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({
        "user": user,
        "content": content,
        "timestamp": timestamp
    })
    logger.info(f"💬 {user}: {content}")

# Initialize session state
if 'setup_complete' not in st.session_state:
    st.session_state.setup_complete = False
if 'alice_model' not in st.session_state:
    st.session_state.alice_model = "mistral"
if 'bob_model' not in st.session_state:
    st.session_state.bob_model = "mistral"
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'conversation_started' not in st.session_state:
    st.session_state.conversation_started = False
if 'conversation_topic' not in st.session_state:
    st.session_state.conversation_topic = ""
if 'alice_personality' not in st.session_state:
    st.session_state.alice_personality = ""
if 'bob_personality' not in st.session_state:
    st.session_state.bob_personality = ""

# CSS Styles
st.markdown("""
<style>
/* Setup page styles */
.setup-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}
.setup-header, .chat-header {
    text-align: center;
    padding: 20px;
    background: linear-gradient(135deg, #FF69B4, #4169E1);
    color: white;
    border-radius: 10px;
    margin-bottom: 20px;
}
.model-select {
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin: 20px 0;
}

/* Chat page styles */
.chat-container {
    display: flex;
    flex-direction: column;
    padding: 10px;
    max-height: 600px;
    overflow-y: auto;
}
.message {
    display: flex;
    align-items: flex-start;
    margin: 10px;
}
.avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    margin: 0 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    color: white;
}
.alice-avatar {
    background-color: #FF69B4;
}
.bob-avatar {
    background-color: #4169E1;
}
.message-bubble {
    max-width: 70%;
    padding: 10px 15px;
    border-radius: 20px;
    margin: 5px;
    position: relative;
}
.alice .message-bubble {
    background-color: #FFE4E1;
    border-top-left-radius: 5px;
}
.bob .message-bubble {
    background-color: #E6E6FA;
    border-top-right-radius: 5px;
}
.message-content {
    font-size: 16px;
    color: #333;
}
.timestamp {
    font-size: 12px;
    color: #888;
    margin-top: 5px;
}
.name {
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 5px;
}
.alice .name {
    color: #FF69B4;
}
.bob .name {
    color: #4169E1;
}
</style>
""", unsafe_allow_html=True)

# Setup Page
if not st.session_state.setup_complete:
    st.markdown('<div class="setup-header"><h1>🤖 Chat Setup</h1></div>', unsafe_allow_html=True)
    
    # Add tabs for setup options
    tab1, tab2, tab3 = st.tabs(["Select Models", "Configure Conversation", "Download New Models"])
    
    with tab1:
        available_models = get_ollama_models()
        
        with st.container():
            st.markdown('<div class="setup-container">', unsafe_allow_html=True)
            
            st.markdown("### Select Models for Agents")
            st.markdown("Choose which AI model each agent will use during the chat.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="model-select">', unsafe_allow_html=True)
                st.markdown("#### Alice's Model")
                st.session_state.alice_model = st.selectbox(
                    "Select model for Alice",
                    available_models,
                    index=available_models.index(st.session_state.alice_model) if st.session_state.alice_model in available_models else 0,
                    key="alice_model_select"
                )
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col2:
                st.markdown('<div class="model-select">', unsafe_allow_html=True)
                st.markdown("#### Bob's Model")
                st.session_state.bob_model = st.selectbox(
                    "Select model for Bob",
                    available_models,
                    index=available_models.index(st.session_state.bob_model) if st.session_state.bob_model in available_models else 0,
                    key="bob_model_select"
                )
                st.markdown("</div>", unsafe_allow_html=True)
    
    with tab2:
        st.markdown("### Configure Conversation")
        st.markdown("Customize how the agents will interact with each other.")
        
        # Conversation topic
        st.markdown('<div class="model-select">', unsafe_allow_html=True)
        st.markdown("#### Conversation Topic")
        st.text_area(
            "What should Alice and Bob talk about?",
            value=st.session_state.conversation_topic,
            key="topic_input",
            placeholder="Example: Discuss favorite movies and debate which ones are the best",
            help="Enter a topic or scenario for the conversation"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="model-select">', unsafe_allow_html=True)
            st.markdown("#### Alice's Personality")
            st.text_area(
                "Define Alice's personality and behavior",
                value=st.session_state.alice_personality,
                key="alice_personality_input",
                placeholder="Example: Enthusiastic movie buff who loves action films",
                help="Describe how Alice should behave in the conversation"
            )
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="model-select">', unsafe_allow_html=True)
            st.markdown("#### Bob's Personality")
            st.text_area(
                "Define Bob's personality and behavior",
                value=st.session_state.bob_personality,
                key="bob_personality_input",
                placeholder="Example: Cinema critic who prefers art house films",
                help="Describe how Bob should behave in the conversation"
            )
            st.markdown("</div>", unsafe_allow_html=True)
        
        if st.button("Save Configuration", use_container_width=True):
            st.session_state.conversation_topic = st.session_state.topic_input
            st.session_state.alice_personality = st.session_state.alice_personality_input
            st.session_state.bob_personality = st.session_state.bob_personality_input
            st.success("Configuration saved! You can now start the chat.")
    
    with tab3:
        st.markdown("### Download New Models")
        st.markdown("Select and download additional models from Ollama.")
        
        remote_models = get_available_remote_models()
        
        col1, col2 = st.columns([3, 1])
        with col1:
            model_to_download = st.selectbox(
                "Select model to download",
                remote_models,
                key="model_download_select"
            )
        with col2:
            if st.button("Download", use_container_width=True):
                with st.spinner(f"Downloading {model_to_download}..."):
                    if pull_ollama_model(model_to_download):
                        st.success(f"Successfully downloaded {model_to_download}")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"Failed to download {model_to_download}")
        
        st.markdown("### Currently Available Models")
        local_models = get_ollama_models()
        st.write("Installed models:", ", ".join(local_models))

    if st.button("Start Chat", use_container_width=True):
        if not st.session_state.conversation_topic:
            st.error("Please configure a conversation topic before starting the chat.")
        else:
            logger.info(f"✨ Chat starting with models:")
            logger.info(f"👩 Alice: {st.session_state.alice_model}")
            logger.info(f"👨 Bob: {st.session_state.bob_model}")
            logger.info(f"💭 Topic: {st.session_state.conversation_topic}")
            st.session_state.setup_complete = True
            st.rerun()

# Chat Page
else:
    # Create agents with custom personalities
    alice_agent = Agent(
        name="Alice",
        instructions=f"""You're Alice. {st.session_state.alice_personality if st.session_state.alice_personality else 'Keep responses casual and short.'}
        Stay on topic discussing: {st.session_state.conversation_topic}. 
        Keep responses to one sentence. Refer to previous messages naturally.""",
        functions=[],
        model=st.session_state.alice_model
    )

    bob_agent = Agent(
        name="Bob",
        instructions=f"""You're Bob. {st.session_state.bob_personality if st.session_state.bob_personality else 'Keep responses casual and short.'}
        Stay on topic discussing: {st.session_state.conversation_topic}. 
        Keep responses to one sentence. Refer to previous messages naturally.""",
        functions=[],
        model=st.session_state.bob_model
    )

    st.markdown('<div class="chat-header"><h1>💭 Group Chat</h1></div>', unsafe_allow_html=True)
    
    # Display chat messages
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        user = message["user"]
        is_alice = user == "Alice"
        avatar_class = "alice-avatar" if is_alice else "bob-avatar"
        message_class = "alice" if is_alice else "bob"
        
        st.markdown(f"""
        <div class="message {message_class}">
            <div class="avatar {avatar_class}">{user[0]}</div>
            <div class="message-content">
                <div class="name">{user}</div>
                <div class="message-bubble">
                    <div class="message-text">{message["content"]}</div>
                    <div class="timestamp">{message["timestamp"]}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Auto-generate messages
    if (datetime.now() - st.session_state.last_update).seconds >= 2:
        if not st.session_state.conversation_started:
            current_agent = random.choice([alice_agent, bob_agent])
            logger.info(f"🎯 Starting new conversation about: {st.session_state.conversation_topic}")
            add_message(current_agent.name, f"Hey, let's talk about {st.session_state.conversation_topic}...")
            st.session_state.conversation_started = True
        else:
            last_speaker = st.session_state.messages[-1]["user"]
            current_agent = bob_agent if last_speaker == "Alice" else alice_agent
            logger.info(f"🔄 Switching to {current_agent.name}")
            
            api_messages = [{"role": "user", "content": msg["content"]} for msg in st.session_state.messages]
            
            # Get response from current agent
            response = get_agent_response(
                current_agent,
                api_messages
            )
            
            if response and response.messages:
                content = response.messages[-1]['content']
                add_message(current_agent.name, content)
        
        st.session_state.last_update = datetime.now()

    # Add a reset button in the sidebar
    with st.sidebar:
        st.markdown("### Chat Controls")
        if st.button("Change Models", use_container_width=True):
            # Reset to setup screen
            st.session_state.setup_complete = False
            st.session_state.conversation_started = False
            st.session_state.messages = []
            st.rerun()
        
        # Show current models
        st.markdown("### Current Models")
        st.markdown(f"**Alice**: {st.session_state.alice_model}")
        st.markdown(f"**Bob**: {st.session_state.bob_model}")
        
        # Show conversation settings
        st.markdown("### Conversation Settings")
        st.markdown(f"**Topic**: {st.session_state.conversation_topic}")
        if st.session_state.alice_personality:
            st.markdown(f"**Alice's Personality**: {st.session_state.alice_personality}")
        if st.session_state.bob_personality:
            st.markdown(f"**Bob's Personality**: {st.session_state.bob_personality}")
        
        # Show debug info
        if st.checkbox("Show Debug Info"):
            st.markdown("### Debug Information")
            st.markdown("#### Message Count")
            st.write(f"Total messages: {len(st.session_state.messages)}")
            st.markdown("#### Last Update")
            st.write(f"Last update: {st.session_state.last_update.strftime('%H:%M:%S')}")

    # Auto-refresh
    time.sleep(2)
    st.rerun()

# Run the app
if __name__ == "__main__":
    logging.info("🚀 Starting Chat Application")
