import json
import re
import os
import shutil
import logging
import base64
import struct
from pathlib import Path
from app.utils.png_char_parser import extract_chara_data_from_png


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_png_metadata(png_path):
    """
    Extract embedded JSON metadata from a PNG file (SillyTavern format).
    """
    try:
        with open(png_path, 'rb') as f:
            signature = f.read(8)
            if signature != b'\x89PNG\r\n\x1a\n':
                return None
            
            while True:
                length_bytes = f.read(4)
                if len(length_bytes) < 4:
                    break
                    
                length = struct.unpack('>I', length_bytes)[0]
                chunk_type = f.read(4).decode('ascii', errors='ignore')
                chunk_data = f.read(length)
                crc = f.read(4)
                
                if chunk_type == 'tEXt':
                    try:
                        null_idx = chunk_data.index(b'\x00')
                        keyword = chunk_data[:null_idx].decode('latin-1')
                        value = chunk_data[null_idx + 1:]
                        
                        if keyword == 'chara':
                            try:
                                decoded = base64.b64decode(value)
                                char_data = json.loads(decoded)
                                return char_data
                            except Exception as e:
                                logger.warning(f"Failed to decode chara data: {e}")
                                
                    except ValueError:
                        pass
                
                if chunk_type == 'IEND':
                    break
                    
        return None
        
    except Exception as e:
        logger.error(f"Error reading PNG {png_path}: {e}")
        return None

class CharacterParser:
    """
    Manages character templates and instantiates them for specific users.
    Handles 'VIP_ONLY' magic tags parsing.
    Supports both JSON and PNG (SillyTavern) character cards.
    """
    
    # TTS 专属角色列表
    TTS_EXCLUSIVE_CHARS = ["ray", "ray-your-bunny-bodyguard"]
    
    def __init__(self, templates_dir="templates/characters", data_root="data/users"):
        self.user_templates_dir = "角色卡"
        self.templates_dir = templates_dir
        self.data_root = data_root
        
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.user_templates_dir, exist_ok=True)
        os.makedirs(self.data_root, exist_ok=True)
        
        self._sync_templates()

    def _sync_templates(self):
        """
        Syncs character cards from '角色卡' folder.
        Supports both JSON and PNG formats.
        """
        try:
            if os.path.exists(self.user_templates_dir):
                for filename in os.listdir(self.user_templates_dir):
                    src = os.path.join(self.user_templates_dir, filename)
                    
                    # Handle JSON files
                    if filename.endswith(".json"):
                        dst = os.path.join(self.templates_dir, filename)
                        if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
                            shutil.copy2(src, dst)
                            logger.info(f"Synced JSON template: {filename}")
                    
                    # Handle PNG files (SillyTavern character cards)
                    elif filename.endswith(".png"):
                        char_data = extract_png_metadata(src)
                        if char_data:
                            # Save as JSON
                            json_filename = filename.replace(".png", ".json")
                            dst = os.path.join(self.templates_dir, json_filename)
                            
                            # Check if needs update
                            need_save = True
                            if os.path.exists(dst):
                                with open(dst, 'r', encoding='utf-8') as f:
                                    existing = json.load(f)
                                # Compare modification time
                                if os.path.getmtime(src) <= os.path.getmtime(dst):
                                    need_save = False
                            
                            if need_save:
                                with open(dst, 'w', encoding='utf-8') as f:
                                    json.dump(char_data, f, ensure_ascii=False, indent=2)
                                logger.info(f"Converted PNG to JSON: {filename} -> {json_filename}")
                                
        except Exception as e:
            logger.error(f"Template sync failed: {e}")

    def _process_text(self, text, is_vip):
        """
        Parses {{VIP_ONLY}} tags in a string.
        
        Regex Explanation:
        - `\{\{VIP_ONLY\}\}`: Matches the literal starting tag.
        - `(.*?)`: Non-greedy match for any content inside. `re.DOTALL` allows matching newlines.
        - `\{\{/VIP_ONLY\}\}`: Matches the literal ending tag.
        
        Logic:
        - If is_vip is True: Replace the whole match with just the captured content (group 1).
        - If is_vip is False: Replace the whole match with an empty string (remove it).
        """
        if not isinstance(text, str):
            return text

        pattern = r"\{\{VIP_ONLY\}\}(.*?)\{\{/VIP_ONLY\}\}"
        
        if is_vip:
            # Keep content, remove tags
            # \1 refers to the first captured group (content inside tags)
            return re.sub(pattern, r"\1", text, flags=re.DOTALL)
        else:
            # Remove everything including tags
            return re.sub(pattern, "", text, flags=re.DOTALL)

    def parse_character(self, template_filename, user_id, is_vip=False):
        """
        Reads a template, processes it based on VIP status, and saves it to the user's directory.
        
        Args:
            template_filename (str): Name of the file in templates/characters (e.g., 'Seraphina.json')
            user_id (str/int): Telegram User ID
            is_vip (bool): Whether the user is a VIP
            
        Returns:
            dict: The processed character data
        """
        template_path = os.path.join(self.templates_dir, template_filename)
        if not os.path.exists(template_path):
            logger.error(f"Template not found: {template_path}")
            return None

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                char_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load template {template_filename}: {e}")
            return None

        # Fields to process
        fields_to_process = ['description', 'first_mes', 'personality', 'scenario', 'mes_example']
        
        # Also check 'data' sub-object if it exists (SillyTavern V2 card format)
        if 'data' in char_data:
            target_data = char_data['data']
        else:
            target_data = char_data

        # Process each field
        for field in fields_to_process:
            if field in target_data:
                target_data[field] = self._process_text(target_data[field], is_vip)

        # Create user directory
        user_dir = os.path.join(self.data_root, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        # Save processed character
        # We strip the extension from filename to use as the character ID/name
        char_name = os.path.splitext(template_filename)[0]
        output_path = os.path.join(user_dir, f"{char_name}.json")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(char_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved character {char_name} for user {user_id} (VIP={is_vip})")
            return char_data
        except Exception as e:
            logger.error(f"Failed to save character for user {user_id}: {e}")
            return None

    def get_character(self, user_id, char_name):
        """Retrieves a character for a specific user."""
        char_path = os.path.join(self.data_root, str(user_id), f"{char_name}.json")
        if os.path.exists(char_path):
            with open(char_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def is_tts_exclusive(self, char_name):
        """Check if a character is TTS-only (voice response only)."""
        char_name_lower = char_name.lower()
        for tts_char in self.TTS_EXCLUSIVE_CHARS:
            if tts_char in char_name_lower:
                return True
        return False
    
    def list_available_characters(self):
        """List all available character templates."""
        chars = []
        if os.path.exists(self.templates_dir):
            for filename in os.listdir(self.templates_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.templates_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Handle V2 format
                        char_data = data.get('data', data)
                        name = char_data.get('name', os.path.splitext(filename)[0])
                        
                        # Check if TTS exclusive
                        is_tts = self.is_tts_exclusive(filename)
                        
                        chars.append({
                            'filename': filename,
                            'name': name,
                            'is_tts_exclusive': is_tts
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read {filename}: {e}")
        return chars

if __name__ == "__main__":
    # Test code
    parser = CharacterParser()
    
    # Create a dummy template for testing
    dummy_data = {
        "name": "TestChar",
        "description": "This is a normal description. {{VIP_ONLY}}This is a secret description.{{/VIP_ONLY}}",
        "first_mes": "Hello! {{VIP_ONLY}}Master, {{/VIP_ONLY}}how are you?"
    }
    with open("templates/characters/test_char.json", "w", encoding='utf-8') as f:
        json.dump(dummy_data, f)
        
    print("Testing Non-VIP:")
    res_normal = parser.parse_character("test_char.json", "12345", is_vip=False)
    print(res_normal['description']) # Should not have secret
    
    print("\nTesting VIP:")
    res_vip = parser.parse_character("test_char.json", "67890", is_vip=True)
    print(res_vip['description']) # Should have secret
