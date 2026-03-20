# ASR & Emotion Recognition Proposal

## Overview
This document outlines the proposed architecture for integrating Automatic Speech Recognition (ASR) and Speech Emotion Recognition (SER) into the Telegram bot.

## 1. Speech-to-Text (ASR)
Since the user needs to recognize voice messages from Telegram (Ogg/Opus format), we need a robust ASR engine.

### Option A: Groq (Recommended for Speed/Cost)
- **Model**: `whisper-large-v3`
- **Cost**: Free tier available, extremely fast.
- **Integration**:
  1.  Convert Ogg -> MP3/WAV using `ffmpeg`.
  2.  Send to Groq API.
  3.  Get text transcription.

### Option B: OpenAI Whisper
- **Model**: `whisper-1`
- **Cost**: Paid.
- **Integration**: Standard OpenAI API.

### Recommendation
Use **Groq** if an API key is available, otherwise fallback to OpenAI or local (if resources permit). Given the current environment (Z.AI / ElevenLabs), we might need a separate key for Groq/OpenAI.

**Current Status**: We do not have a dedicated ASR key configured.

## 2. Emotion Recognition (SER)
The user requested recognizing "emotional state" from voice.

### Approach 1: Text-Based Inference (Pragmatic)
- **Logic**: Use the transcribed text + LLM (GLM-4.7) to infer emotion.
- **Prompting**: "Analyze the following user input for emotional tone (e.g., Angry, Happy, Sad). Input: {text}"
- **Pros**: No extra cost, uses existing GLM-4.7 intelligence.
- **Cons**: Misses tonal cues (sarcasm, shouting).

### Approach 2: Audio-Based Inference (Advanced)
- **Tools**: Hume AI (EVI), Hume Expression Measurement.
- **Pros**: Detects prosody, laughter, sighs.
- **Cons**: Requires separate API key and integration.

### Proposed Solution
For the MVP, we will implement **Approach 1 (Text-Based)** combined with **ASR**.
If the user provides a specific "Audio Emotion API Key" (e.g., Hume), we can upgrade to Approach 2.

## Implementation Plan

1.  **Add `asr_client.py`**:
    -   Handle audio file conversion (`pydub` + `ffmpeg`).
    -   Call ASR API (Mock or Real).
2.  **Update `telegram_bot.py`**:
    -   Add `filters.VOICE` handler.
    -   Download voice -> Convert -> Transcribe -> Analyze Emotion -> Reply.

## Next Steps
-   Please provide an **OpenAI API Key** or **Groq API Key** for ASR.
-   Or confirm if we should use a mock/placeholder for now.
