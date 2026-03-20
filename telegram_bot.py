import logging
import asyncio
import os
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from character_manager import CharacterParser
from st_client import STClient
from image_client import ImageClient
from tts_client import TTSClient
from asr_client import ASRClient
from database import Database
import config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize modules
db = Database()
char_parser = CharacterParser()
st_client = STClient() # Config loaded from config.py
image_client = ImageClient() # Config loaded from config.py
tts_client = TTSClient()
asr_client = ASRClient()

# --- Helper Functions ---

async def check_user_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Checks if user can send a message.
    Returns True if allowed, False if blocked (and sends rejection msg).
    """
    user = update.effective_user
    tg_id = user.id
    
    # Ensure user exists in DB
    db_user = db.get_user(tg_id)
    if not db_user:
        db_user = db.create_user(tg_id, user.username)
    
    # Check and reset daily limit if needed
    db_user = db.check_and_reset_daily_limit(tg_id)
    
    is_vip = bool(db_user['is_vip'])
    daily_count = db_user['daily_msg_count']
    
    # VIPs are always allowed
    if is_vip:
        return True
        
    # Free users check limit
    if daily_count >= config.DAILY_MSG_LIMIT:
        await update.message.reply_text(
            "🔞 今日免费激情对话额度已用完。\n"
            "订阅 VIP 解锁无限畅聊 & 解锁高清私房照功能！\n"
            "/subscribe"
        )
        return False
        
    return True

# --- Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message."""
    user = update.effective_user
    # Ensure user exists
    db.create_user(user.id, user.username)
    
    await update.message.reply_text(
        f"欢迎来到 Nuomi Circuit ～ {user.first_name}!\n\n"
        "我是你的 AI 伴侣。我们可以聊任何话题。\n"
        "发送 /chars 选择角色。\n"
        "发送 /subscribe 查看会员详情。"
    )

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show subscription info."""
    await update.message.reply_text(
        "💎 **VIP 会员权益**\n\n"
        "1. **无限畅聊**：解除每日 30 条消息限制。\n"
        "2. **私房照解锁**：查看角色发送的高清私密照片。\n"
        "3. **优先响应**：更快的生成速度。\n\n"
        "当前状态：免费用户 (每日额度 30 条)\n"
        "请联系管理员升级：@YourAdminHandle"
    )

async def img_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image generation request."""
    user = update.effective_user
    tg_id = user.id
    db_user = db.get_user(tg_id)
    
    if not db_user:
        db_user = db.create_user(tg_id, user.username)
        
    is_vip = bool(db_user['is_vip'])
    
    if is_vip:
        # Get current char prompt details
        char_name = context.user_data.get("current_char", "beautiful girl")
        char_desc = context.user_data.get("char_description", "")
        
        # User input prompt (e.g. /img wearing swimsuit)
        user_prompt = " ".join(context.args) if context.args else ""
        
        # Construct Prompt
        base_prompt = "masterpiece, best quality, 1girl, solo"
        
        if user_prompt:
            # If user specifies, prioritize user input + char name
            prompt = f"{base_prompt}, {char_name}, {user_prompt}"
        else:
            # Default: use character description (truncated to avoid too long prompt)
            short_desc = char_desc[:100].replace("\n", " ") if char_desc else ""
            prompt = f"{base_prompt}, {char_name}, {short_desc}"

        negative_prompt = "nsfw, low quality, worst quality, bad anatomy"
        
        status_msg = await update.message.reply_text(f"正在为您生成专属私照... ⏳\nPrompt: {prompt[:50]}...")
        
        # Call Image API (runs in thread to avoid blocking event loop)
        loop = asyncio.get_event_loop()
        image_data = await loop.run_in_executor(
            None, 
            image_client.generate_image, 
            prompt, negative_prompt, 512, 768
        )
        
        if image_data:
            await status_msg.delete()
            await context.bot.send_photo(chat_id=tg_id, photo=image_data, caption="你的专属照片已生成 ❤️")
        else:
            await status_msg.edit_text("❌ 图片生成失败，请稍后再试或联系管理员。")
            
    else:
        # Free user rejection
        # You should have a file named 'locked.png' in the bot directory
        locked_img_path = "locked.png" 
        
        # Create a dummy locked image if it doesn't exist for testing
        if not os.path.exists(locked_img_path):
             # Just send text if image missing
             await update.message.reply_text(
                "🔒 **私密照片仅限 VIP 会员查看**\n\n"
                "请输入 /subscribe 解锁全部权益。"
            )
        else:
            await update.message.reply_photo(
                photo=open(locked_img_path, "rb"),
                caption="🔒 **私密照片仅限 VIP 会员查看**\n\n请输入 /subscribe 解锁全部权益。"
            )

async def admin_reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reload character templates (Admin only)."""
    user = update.effective_user
    if user.id != config.ADMIN_ID:
        return
    
    # In this architecture, we don't hold much state in memory for chars,
    # but we could clear any caches if we added them later.
    # For now, just a confirmation since we parse file on demand.
    await update.message.reply_text("✅ 角色模板缓存已刷新 (逻辑上)。")

async def chars_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List available characters."""
    try:
        # Use the new list_available_characters method
        chars = char_parser.list_available_characters()
        
        if not chars:
            await update.message.reply_text("暂无可用角色。")
            return

        keyboard = []
        for char_info in chars:
            display_name = char_info['name']
            char_id = char_info['filename'].replace(".json", "")
            is_tts = char_info['is_tts_exclusive']
            
            # Add emoji for TTS exclusive characters
            if is_tts:
                display_name = f"🎙️ {display_name}"
            
            callback_data = f"char_{char_id}"
            if len(callback_data.encode('utf-8')) > 64:
                safe_id = char_id[:20] 
                callback_data = f"char_{safe_id}"
            
            keyboard.append([InlineKeyboardButton(display_name, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "请选择要对话的角色：\n\n🎙️ = 语音专属角色（仅语音回复）", 
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error listing chars: {e}")
        await update.message.reply_text("获取角色列表失败。")

async def char_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle character selection."""
    query = update.callback_query
    await query.answer()
    
    selected_data = query.data.replace("char_", "")
    
    # Re-find the full character name from the directory if we truncated it
    # This is a bit inefficient but safe
    files = os.listdir("templates/characters")
    chars = [f.replace(".json", "") for f in files if f.endswith(".json")]
    
    char_name = selected_data # Default
    
    # If the data matches a char exactly, use it.
    if selected_data in chars:
        char_name = selected_data
    else:
        # Fuzzy match or find by prefix if we truncated
        for c in chars:
            if c.startswith(selected_data):
                char_name = c
                break
    
    context.user_data["current_char"] = char_name
    
    # Load character to get greeting
    tg_id = query.from_user.id
    db_user = db.get_user(tg_id)
    is_vip = bool(db_user['is_vip']) if db_user else False
    
    # Parse character (this also handles VIP/Free logic for description)
    char_data = char_parser.parse_character(f"{char_name}.json", tg_id, is_vip)
    
    if char_data:
        # Handle V2 data structure
        data = char_data.get('data', char_data)
        
        # Get real name for display
        real_name = data.get('name', char_name)
        
        # Store description for image generation
        context.user_data["char_description"] = data.get("description", "")
        
        # Determine greeting
        # If first_mes is too long (>300 chars), generate a short one using LLM
        raw_greeting = data.get('first_mes', "你好~")
        greeting = raw_greeting
        
        if len(raw_greeting) > 300:
            await query.edit_message_text(f"✅ 已切换到角色：{real_name}\n\n正在生成开场白...")
            
            # Detect user language preference
            user_lang = query.from_user.language_code or "en"
            lang_instruction = "in English"
            if "zh" in user_lang:
                lang_instruction = "in Chinese"
                
            # Construct a prompt for the greeting
            # We want to use the character's persona but instruct it to be brief.
            # Instead of appending to history, let's override the messages list in construct_payload manually or just simplify.
            # To be safe and avoid 400 errors from complex system prompt structures, 
            # let's just use a simple direct prompt approach for this specific task.
            
            prompt_content = f"""
Character Name: {real_name}
Description: {data.get('description', '')}
Personality: {data.get('personality', '')}

Instruction: Write a short, in-character opening greeting (under 50 words) {lang_instruction}. Output ONLY the greeting text.
"""
            gen_payload = {
                "model": config.LLM_MODEL, # Use default model (glm-4-plus verified)
                "messages": [
                    {"role": "user", "content": prompt_content}
                ],
                "stream": True,
                "max_tokens": 1024,
                "temperature": 0.7
            }
            
            # Generate
            try:
                full_response = ""
                # generate_response is now an async generator
                async for chunk in st_client.generate_response(gen_payload):
                    full_response += chunk
                if full_response.strip():
                    greeting = full_response.strip()
            except Exception as e:
                logger.error(f"Failed to gen greeting: {e}")
                # Fallback: truncate
                greeting = raw_greeting[:200] + "..."

        # Remove parse_mode="Markdown" to avoid errors with special characters in char_name or greeting
        await query.edit_message_text(f"✅ 已切换到角色：{real_name}\n\n{greeting}")
        
        # Reset chat history for this user
        context.user_data["history"] = []
    else:
        await query.edit_message_text("❌ 加载角色失败。")

# --- Message Handler ---

async def debug_log_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log every update for debugging."""
    if update.message:
        logger.info(f"Received message: {update.message.message_id} from {update.effective_user.id}")
        if update.message.voice:
            logger.info(f"Message contains VOICE. File ID: {update.message.voice.file_id}")
        elif update.message.audio:
            logger.info(f"Message contains AUDIO. File ID: {update.message.audio.file_id}")
        elif update.message.text:
            logger.info(f"Message contains TEXT: {update.message.text[:20]}...")
        else:
            logger.info("Message contains unknown content type.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages."""
    logger.info("Entering handle_voice...")
    user = update.effective_user
    tg_id = user.id
    
    # 1. Check Access
    if not await check_user_access(update, context):
        return

    # 2. Check Char
    char_name = context.user_data.get("current_char")
    if not char_name:
        await update.message.reply_text("请先选择一个角色：/chars")
        return

    # 3. Download Voice
    try:
        status_msg = await update.message.reply_text("🎧 正在聆听...")
        
        # Check if voice or audio
        file_obj = None
        if update.message.voice:
            file_obj = update.message.voice
        elif update.message.audio:
            file_obj = update.message.audio
        
        if not file_obj:
             await status_msg.edit_text("❌ 未找到音频文件。")
             return

        voice_file = await context.bot.get_file(file_obj.file_id)
        
        # Download to memory or temp file
        # We need bytes for ASR
        from io import BytesIO
        voice_data = BytesIO()
        await voice_file.download_to_memory(voice_data)
        voice_bytes = voice_data.getvalue()
        
        # 4. ASR (Speech to Text)
        asr_result = asr_client.transcribe_audio(voice_bytes, content_type="audio/ogg")
        
        if not asr_result or not asr_result.get("text"):
            await status_msg.edit_text("❌ 无法识别语音，请重试。")
            return
            
        user_text = asr_result.get("text")
        sentiment = asr_result.get("sentiment", "neutral")
        
        # Inform user what was heard (optional, but good for UX)
        await status_msg.edit_text(f"🗣️ 听到：{user_text}\n(情绪: {sentiment})")
        
        # 5. Process Chat (Generate Response)
        # Inject sentiment into the user message for the LLM
        # e.g. "[Sentiment: Happy] Hello there!"
        annotated_text = f"[Sentiment: {sentiment}] {user_text}"
        
        # Reuse logic? We need to call the generation logic.
        # Since handle_message is coupled with Update, we'll manually call a helper.
        # Let's call a shared helper `process_turn`.
        
        response_text, image_prompt = await process_turn(update, context, annotated_text, user_text_display=user_text)
        
        if not response_text and not image_prompt:
             await status_msg.edit_text("Error: Empty response.")
             return

        # 6. Text Response (Edit status message to show text reply)
        await status_msg.edit_text(f"🗣️ {user_text}\n\n💬 {response_text}")
        
        # 7. TTS (Text to Speech)
        if response_text:
            # Send "Recording..." action
            await context.bot.send_chat_action(chat_id=tg_id, action="record_voice")
            
            audio_bytes = await tts_client.generate_speech(response_text)
            if audio_bytes:
                await context.bot.send_voice(chat_id=tg_id, voice=audio_bytes, caption="Audio Reply")
            else:
                # If TTS fails, we already showed text.
                pass
                
        # 8. Image Prompt
        if image_prompt:
            # Handle image generation (reuse logic or copy)
            # For brevity, let's call the image generation block if we can extract it.
            # Or just ignore image in voice mode for now to keep it simple?
            # User wants "Roleplay", so image is important.
            # We'll duplicate the image logic for now or extract it later.
            await handle_image_generation(update, context, image_prompt)

    except Exception as e:
        logger.error(f"Voice handle error: {e}")
        await update.message.reply_text("⚠️ 语音处理出错。")

async def process_turn(update: Update, context: ContextTypes.DEFAULT_TYPE, input_text: str, user_text_display: str = None):
    """
    Core logic for processing a turn.
    Returns (response_text, image_prompt).
    Does NOT send messages (except logging).
    Updates history.
    """
    user = update.effective_user
    tg_id = user.id
    
    # Load Character
    char_name = context.user_data.get("current_char")
    db_user = db.get_user(tg_id)
    is_vip = bool(db_user['is_vip']) if db_user else False
    
    char_data = char_parser.get_character(tg_id, char_name)
    if not char_data:
        char_data = char_parser.parse_character(f"{char_name}.json", tg_id, is_vip)
        
    # Update History
    if "history" not in context.user_data:
        context.user_data["history"] = []
    
    # Use the clean text for history if possible, or annotated?
    # Annotated is better for LLM context.
    context.user_data["history"].append({"role": "user", "content": input_text})
    
    # Summarization Check
    if len(context.user_data["history"]) > 20:
        to_summarize = context.user_data["history"][:10]
        context.user_data["history"] = context.user_data["history"][10:]
        asyncio.create_task(summarize_memory(context, to_summarize))

    # Construct Payload
    current_summary = context.user_data.get("summary", "")
    import copy
    runtime_char_data = copy.deepcopy(char_data)
    target = runtime_char_data.get('data', runtime_char_data)
    if current_summary:
        target['scenario'] = target.get('scenario', '') + f"\n\n[Previous Conversation Summary]: {current_summary}"

    payload = st_client.construct_payload(
        runtime_char_data, 
        context.user_data["history"], 
        user.first_name or "User"
    )
    
    # Generate Response
    full_response = ""
    async for chunk in st_client.generate_response(payload):
        full_response += chunk
        
    # Parse tags
    import re
    reply_match = re.search(r"<reply>(.*?)</reply>", full_response, re.DOTALL)
    img_match = re.search(r"<image_prompt>(.*?)</image_prompt>", full_response, re.DOTALL)
    
    final_text = ""
    if reply_match:
        final_text = reply_match.group(1).strip()
    elif not img_match:
        final_text = full_response
        
    # Update History with Assistant response
    context.user_data["history"].append({"role": "assistant", "content": full_response})
    
    if not is_vip:
        db.increment_msg_count(tg_id)
        
    image_prompt = img_match.group(1).strip() if img_match else None
    
    return final_text, image_prompt

async def handle_image_generation(update, context, raw_prompt):
    """Helper for image generation."""
    user = update.effective_user
    tg_id = user.id
    db_user = db.get_user(tg_id)
    is_vip = bool(db_user['is_vip']) if db_user else False
    
    if is_vip:
        status_msg = await update.message.reply_text("📸 正在接收图片... ⏳")
        base_prompt = "masterpiece, best quality"
        char_desc = context.user_data.get("char_description", "")
        short_desc = char_desc[:100].replace("\n", " ") if char_desc else ""
        full_img_prompt = f"{base_prompt}, {raw_prompt}, {short_desc}"
        
        loop = asyncio.get_event_loop()
        image_data = await loop.run_in_executor(
            None, 
            image_client.generate_image, 
            full_img_prompt, 
            "nsfw, low quality, worst quality, bad anatomy", 
            1024, 1024
        )
        
        if image_data:
            await status_msg.delete()
            await context.bot.send_photo(chat_id=tg_id, photo=image_data, caption="📸")
            db.increment_img_count(tg_id)
        else:
            await status_msg.edit_text("❌ 图片生成失败。")
    else:
        locked_img_path = "locked.png"
        caption = "🔞 **AI 想要给你发一张私密照**\n但被 VIP 锁拦截了。\n/subscribe 解锁查看。"
        if os.path.exists(locked_img_path):
            await update.message.reply_photo(photo=open(locked_img_path, "rb"), caption=caption)
        else:
            await update.message.reply_text(caption)

async def summarize_memory(context, messages):
    """
    Compresses a list of messages into a summary and updates user_data.
    """
    try:
        conversation_text = ""
        for msg in messages:
            role = msg.get('role')
            content = msg.get('content')
            conversation_text += f"{role}: {content}\n"
            
        previous_summary = context.user_data.get("summary", "")
        
        prompt = f"""
Please summarize the following conversation fragment, merging it with the previous summary.
Keep important details (names, preferences, key events). Keep it concise.

Previous Summary:
{previous_summary}

New Conversation:
{conversation_text}

New Summary:
"""
        payload = {
            "model": config.LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.5,
            "stream": False
        }
        
        new_summary = ""
        async for chunk in st_client.generate_response(payload):
            new_summary += chunk
            
        if new_summary.strip():
            context.user_data["summary"] = new_summary.strip()
            logger.info(f"Memory summarized. New length: {len(new_summary)}")
            
    except Exception as e:
        logger.error(f"Summarization failed: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    user = update.effective_user
    text = update.message.text
    
    # 1. Check Access (Daily Limit)
    if not await check_user_access(update, context):
        return

    # 2. Check if char selected
    char_name = context.user_data.get("current_char")
    if not char_name:
        await update.message.reply_text("请先选择一个角色：/chars")
        return

    # 3. Load Character
    tg_id = user.id
    db_user = db.get_user(tg_id)
    is_vip = bool(db_user['is_vip']) if db_user else False
    
    char_data = char_parser.get_character(tg_id, char_name)
    if not char_data:
        # Try to parse again if missing
        char_data = char_parser.parse_character(f"{char_name}.json", tg_id, is_vip)
        if not char_data:
            await update.message.reply_text("角色数据丢失，请重新选择 /chars")
            return

    # 4. Update History
    if "history" not in context.user_data:
        context.user_data["history"] = []
    
    logger.info(f"User {tg_id} ({user.first_name}) sent: {text}")

    # Store summary if not exists
    if "summary" not in context.user_data:
        context.user_data["summary"] = ""
        
    context.user_data["history"].append({"role": "user", "content": text})
    
    # --- Memory Summarization Logic ---
    # Trigger summarization every 10 turns if history is getting long
    if len(context.user_data["history"]) > 20:
        # Get the oldest 10 messages to summarize
        to_summarize = context.user_data["history"][:10]
        # Keep the rest
        context.user_data["history"] = context.user_data["history"][10:]
        
        # Async summarization (fire and forget for now, or await if critical)
        # We'll run it in background to not block reply
        asyncio.create_task(summarize_memory(context, to_summarize))

    # 5. Construct Payload
    # Inject summary into char_data or scenario temporarily
    current_summary = context.user_data.get("summary", "")
    if current_summary:
        # Append summary to scenario or description for the model to see
        # We copy char_data to avoid modifying the cache
        import copy
        runtime_char_data = copy.deepcopy(char_data)
        if 'data' in runtime_char_data:
            target = runtime_char_data['data']
        else:
            target = runtime_char_data
            
        target['scenario'] = target.get('scenario', '') + f"\n\n[Previous Conversation Summary]: {current_summary}"
    else:
        runtime_char_data = char_data

    payload = st_client.construct_payload(
        runtime_char_data, 
        context.user_data["history"], 
        user.first_name or "User"
    )

    # 6. Generate Response (Streaming)
    msg = await update.message.reply_text("...")
    full_response = ""
    
    try:
        # Stream from STClient
        chunk_count = 0
        async for chunk in st_client.generate_response(payload):
            full_response += chunk
            chunk_count += 1
            # Update Telegram message every ~20 chunks to avoid rate limits
            if chunk_count % 20 == 0:
                try:
                    # Temporary display raw output for debugging or immediate feedback
                    # Ideally we want to parse streaming but regex on stream is hard.
                    # We will update with full response later.
                    await msg.edit_text(full_response + "...") 
                except Exception:
                    pass 
        
        # --- Post-Processing: Parse <reply> and <image_prompt> ---
        
        # Regex to find tags
        reply_match = re.search(r"<reply>(.*?)</reply>", full_response, re.DOTALL)
        img_match = re.search(r"<image_prompt>(.*?)</image_prompt>", full_response, re.DOTALL)
        
        final_text = ""
        if reply_match:
            final_text = reply_match.group(1).strip()
        elif not img_match:
            # Fallback: if no tags found, assume whole text is reply (compatibility)
            final_text = full_response
            
        logger.info(f"Bot response to {tg_id}: {final_text[:200]}...")

        # 1. Send Text Reply
        # Check if this is a TTS-exclusive character
        is_tts_exclusive = char_parser.is_tts_exclusive(char_name)
        
        if final_text:
            if is_tts_exclusive:
                # TTS Exclusive: Send voice only, no text
                await msg.delete()  # Remove the "..." placeholder
                
                # Generate TTS
                await context.bot.send_chat_action(chat_id=tg_id, action="record_voice")
                
                # Check user language or character traits to select voice
                # For Ray (English/Rabbit), maybe use English or default?
                # Let's detect if text is mostly English
                voice_id = "default"
                if len(final_text.encode('utf-8')) == len(final_text):
                    voice_id = "english"
                
                audio_bytes = await tts_client.generate_speech(final_text, voice_id=voice_id)
                
                if audio_bytes:
                    await context.bot.send_voice(chat_id=tg_id, voice=audio_bytes)
                else:
                    # Fallback to text if TTS fails
                    await update.message.reply_text(final_text)
            else:
                # Normal character: Send text
                await msg.edit_text(final_text)
            
            # Update history
            context.user_data["history"].append({"role": "assistant", "content": full_response})
            
            if not is_vip:
                db.increment_msg_count(tg_id)
        else:
            # If only image prompt or empty
            if img_match:
                await msg.delete() # Remove the "..." placeholder
            else:
                await msg.edit_text("Error: Empty response.")

        # 2. Handle Image Prompt
        if img_match:
            raw_prompt = img_match.group(1).strip()
            
            # --- Business Logic: Check Access ---
            if is_vip:
                # VIP: Allow generation
                status_msg = await update.message.reply_text("📸 正在接收图片... ⏳")
                
                # Construct full prompt
                base_prompt = "masterpiece, best quality"
                char_desc = context.user_data.get("char_description", "")
                short_desc = char_desc[:100].replace("\n", " ") if char_desc else ""
                full_img_prompt = f"{base_prompt}, {raw_prompt}, {short_desc}"
                
                # Async generation
                loop = asyncio.get_event_loop()
                image_data = await loop.run_in_executor(
                    None, 
                    image_client.generate_image, 
                    full_img_prompt, 
                    "nsfw, low quality, worst quality, bad anatomy", 
                    1024, 1024
                )
                
                if image_data:
                    await status_msg.delete()
                    await context.bot.send_photo(chat_id=tg_id, photo=image_data, caption="📸")
                    db.increment_img_count(tg_id) # Track usage
                else:
                    await status_msg.edit_text("❌ 图片生成失败。")
            
            else:
                # Free User: Intercept
                locked_img_path = "locked.png"
                caption = "🔞 **AI 想要给你发一张私密照**\n但被 VIP 锁拦截了。\n/subscribe 解锁查看。"
                
                if os.path.exists(locked_img_path):
                    await update.message.reply_photo(photo=open(locked_img_path, "rb"), caption=caption)
                else:
                    await update.message.reply_text(caption)

    except Exception as e:
        logger.error(f"Generation error: {e}")
        await msg.edit_text("⚠️ 生成对话时出现错误，请稍后再试。")

# --- Main ---

def main():
    """Start the bot."""
    if not config.BOT_TOKEN:
        logger.error("No BOT_TOKEN provided!")
        return

    application = Application.builder().token(config.BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("img", img_command))
    application.add_handler(CommandHandler("chars", chars_command))
    application.add_handler(CommandHandler("admin_reload", admin_reload_command))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(char_selection_callback, pattern="^char_"))

    # Messages
    # Debug handler (TypeHandler catches all updates if placed first, or use MessageHandler(filters.ALL))
    # application.add_handler(MessageHandler(filters.ALL, debug_log_middleware), group=-1)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    # Run
    logger.info("Bot started...")
    application.run_polling()

if __name__ == "__main__":
    main()
