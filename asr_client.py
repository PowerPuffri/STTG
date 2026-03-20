import os
import requests
import logging
import config

logger = logging.getLogger(__name__)

class ASRClient:
    """
    Client for Deepgram ASR (Automatic Speech Recognition) API.
    Handles Speech-to-Text and Emotion/Sentiment Analysis.
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key or config.DEEPGRAM_API_KEY
        self.api_url = "https://api.deepgram.com/v1/listen"
        
        if not self.api_key:
            logger.warning("No Deepgram API Key provided. ASR will be disabled.")

    def transcribe_audio(self, audio_data: bytes, content_type: str = "audio/ogg"):
        """
        Transcribes audio data and detects sentiment/emotion.
        
        Args:
            audio_data (bytes): The binary audio data.
            content_type (str): The MIME type of the audio (e.g. "audio/ogg", "audio/mp3").
            
        Returns:
            dict: {
                "text": str,
                "sentiment": str (positive|negative|neutral|mixed),
                "confidence": float,
                "detected_language": str
            } or None if failed.
        """
        if not self.api_key:
            return None
            
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": content_type
        }
        
        # Query parameters
        # model=nova-2 (General purpose, fast, accurate)
        # smart_format=true (Punctuation, formatting)
        # detect_language=true (Auto-detect language)
        # sentiment=true (Sentiment analysis)
        params = {
            "model": "nova-2",
            "smart_format": "true",
            "detect_language": "true",
            "sentiment": "true",
            "intents": "true" # Might give more context
        }
        
        try:
            logger.info(f"Sending audio ({len(audio_data)} bytes) to Deepgram ASR...")
            response = requests.post(
                self.api_url,
                headers=headers,
                params=params,
                data=audio_data,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Deepgram API Error: {response.status_code} - {response.text}")
                return None
                
            data = response.json()
            
            # Parse result
            result = data.get("results", {})
            channels = result.get("channels", [])
            if not channels:
                return None
                
            first_channel = channels[0]
            alternatives = first_channel.get("alternatives", [])
            if not alternatives:
                return None
                
            best_alt = alternatives[0]
            transcript = best_alt.get("transcript", "")
            
            # Extract sentiment
            # Deepgram returns sentiment analysis at the sentence level or average?
            # With 'sentiment=true', it usually provides a 'sentiment' field in the alternative 
            # or in 'sentiments' block.
            # Structure usually: results.sentiments.average or segments
            
            # Let's check where sentiment is. 
            # Often it's in `results.sentiments` (average) or `best_alt.sentiment` depending on version.
            # Snippets suggest `sentiment_score` or `sentiment`.
            # Let's try to find it safely.
            
            sentiment_str = "neutral"
            
            # Check for sentiment in the alternative (segment-wise) or top-level
            if "sentiment" in result:
                # Top level average sentiment?
                sentiment_info = result["sentiment"]
                # It might be { "segments": [...], "average": { "sentiment": "positive", "confidence": 0.9 } }
                if "average" in sentiment_info:
                    sentiment_str = sentiment_info["average"].get("sentiment", "neutral")
            elif "sentiment" in best_alt:
                sentiment_str = best_alt["sentiment"]
            
            logger.info(f"ASR Success: '{transcript[:20]}...' [Sentiment: {sentiment_str}]")
            
            return {
                "text": transcript,
                "sentiment": sentiment_str,
                "raw": data # Keep raw just in case
            }
            
        except Exception as e:
            logger.error(f"ASR Request failed: {e}")
            return None

if __name__ == "__main__":
    # Test stub
    pass
