#!/usr/bin/env python3
"""
PNG Character Card Parser
Extracts embedded JSON metadata from SillyTavern-style PNG character cards.

SillyTavern PNG cards store character data in the tEXt chunk with keyword "chara".
The data is base64 encoded JSON.
"""

import base64
import json
import struct
import zlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def extract_png_metadata(png_path):
    """
    Extract embedded JSON metadata from a PNG file.
    
    SillyTavern character cards embed data in tEXt chunks.
    Returns the parsed JSON data or None if not found.
    """
    try:
        with open(png_path, 'rb') as f:
            # Check PNG signature
            signature = f.read(8)
            if signature != b'\x89PNG\r\n\x1a\n':
                logger.error(f"Not a valid PNG file: {png_path}")
                return None
            
            # Read chunks
            while True:
                # Each chunk: 4 bytes length, 4 bytes type, data, 4 bytes CRC
                length_bytes = f.read(4)
                if len(length_bytes) < 4:
                    break
                    
                length = struct.unpack('>I', length_bytes)[0]
                chunk_type = f.read(4).decode('ascii', errors='ignore')
                chunk_data = f.read(length)
                crc = f.read(4)  # We don't verify CRC for speed
                
                # Look for tEXt chunk
                if chunk_type == 'tEXt':
                    # Format: keyword\0value
                    try:
                        null_idx = chunk_data.index(b'\x00')
                        keyword = chunk_data[:null_idx].decode('latin-1')
                        value = chunk_data[null_idx + 1:]
                        
                        # SillyTavern uses "chara" as keyword
                        if keyword == 'chara':
                            # Value is base64 encoded JSON
                            try:
                                decoded = base64.b64decode(value)
                                char_data = json.loads(decoded)
                                logger.info(f"Found character data in {png_path}")
                                return char_data
                            except Exception as e:
                                logger.warning(f"Failed to decode chara data: {e}")
                                
                    except ValueError:
                        pass
                
                # Stop after IEND chunk
                if chunk_type == 'IEND':
                    break
                    
        return None
        
    except Exception as e:
        logger.error(f"Error reading PNG {png_path}: {e}")
        return None


def scan_character_cards(directory):
    """
    Scan a directory for PNG character cards and extract their metadata.
    Returns a list of (filename, char_data) tuples.
    """
    cards = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        logger.error(f"Directory not found: {directory}")
        return cards
    
    for png_file in dir_path.glob("*.png"):
        char_data = extract_png_metadata(png_file)
        if char_data:
            cards.append((png_file.name, char_data))
            
    return cards


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    # Test with the new character cards
    char_dir = "/Users/zhipu_glm/Desktop/STTG/角色卡"
    
    print(f"Scanning {char_dir} for character cards...\n")
    
    cards = scan_character_cards(char_dir)
    
    for filename, char_data in cards:
        print(f"\n{'='*50}")
        print(f"File: {filename}")
        print(f"{'='*50}")
        
        # Print key info
        if isinstance(char_data, dict):
            # V2 format might have 'data' nested
            data = char_data.get('data', char_data)
            
            name = data.get('name', 'Unknown')
            description = data.get('description', '')[:200]
            personality = data.get('personality', '')[:100]
            
            print(f"Name: {name}")
            print(f"Description: {description}...")
            print(f"Personality: {personality}...")
            
            # Check for TTS-friendly attributes
            tags = data.get('tags', [])
            system_prompt = data.get('system_prompt', '')
            post_history_instructions = data.get('post_history_instructions', '')
            
            print(f"Tags: {tags}")
            print(f"Has System Prompt: {bool(system_prompt)}")
            print(f"Has Post-History Instructions: {bool(post_history_instructions)}")
        else:
            print(f"Unexpected data format: {type(char_data)}")
    
    print(f"\n\nTotal cards found: {len(cards)}")
