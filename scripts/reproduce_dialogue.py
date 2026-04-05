import asyncio
import logging
from st_client import STClient
from character_manager import CharacterParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reproduce_dialogue():
    # 1. Setup
    st_client = STClient()
    char_parser = CharacterParser()
    
    # Load Ray
    # We use the filename we found earlier
    char_filename = "main_ray-your-bunny-bodyguard-929f59dcbfab_spec_v2.json"
    
    # Mock user ID
    user_id = 123456
    
    # Parse character
    # Note: We need to ensure the file exists in templates/characters
    # The parser syncs from "角色卡" to "templates/characters"
    # We can just use the parser to get it.
    char_data = char_parser.parse_character(char_filename, user_id, is_vip=True)
    
    if not char_data:
        print("Error: Could not load Ray character data.")
        return

    print(f"Loaded Character: {char_data.get('name', 'Unknown')}")
    
    # 2. Define Conversation History
    # We simulate the flow
    history = []
    
    user_inputs = [
        "hello",
        "please stay with me.",
        "can I look your picture?",
        "ur just talk with me by voice?"
    ]
    
    print("\n--- Starting Conversation Reproduction ---\n")
    
    for user_text in user_inputs:
        print(f"User: {user_text}")
        
        # Add to history
        history.append({"role": "user", "content": user_text})
        
        # Construct payload
        payload = st_client.construct_payload(
            char_data, 
            history, 
            user_name="Doctor"
        )
        
        # Generate response
        full_response = ""
        print("Ray: ", end="", flush=True)
        
        async for chunk in st_client.generate_response(payload):
            full_response += chunk
            print(chunk, end="", flush=True)
            
        print("\n")
        
        # Add assistant response to history for context
        history.append({"role": "assistant", "content": full_response})
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(reproduce_dialogue())
