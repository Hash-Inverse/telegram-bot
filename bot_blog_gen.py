from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
import aiohttp
import json
from prompts import BLOG_SYSTEM_MESSAGE
import re
from datetime import datetime

# Load environment variables
load_dotenv()

# Replace 'YOUR_BOT_TOKEN' with the token you received from BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

SYSTEM_PROMPT = BLOG_SYSTEM_MESSAGE

async def query_gemini(topic: str) -> str:
    async with aiohttp.ClientSession() as session:
        headers = {"Content-Type": "application/json"}
        prompt = f"{SYSTEM_PROMPT}\n\nWrite a blog post about: {topic}"
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
        
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            return f"Error: {response.status}"

def sanitize_filename(topic: str) -> str:
    # Remove invalid characters and replace spaces with underscores
    sanitized = re.sub(r'[^\w\s-]', '', topic)
    return sanitized.strip().replace(' ', '_')

async def save_blog_to_file(topic: str, content: str) -> str:
    # Create blogs directory if it doesn't exist
    blogs_dir = "blogs"
    os.makedirs(blogs_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = sanitize_filename(topic)
    filename = f"{safe_topic}_{timestamp}.txt"
    filepath = os.path.join(blogs_dir, filename)
    
    # Save content to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I'm your blog post generator bot.\n"
        "Commands:\n"
        "/blog <topic> - Generate and show blog post in chat\n"
        "/blog_file <topic> - Generate and save blog post to file"
    )

async def generate_blog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a topic! Usage: /blog <topic>")
        return
    
    topic = " ".join(context.args)
    await update.message.reply_text(f"Generating blog post about: {topic}...")
    
    try:
        blog_post = await query_gemini(topic)
        # Split long posts into chunks if needed
        if len(blog_post) > 4000:
            chunks = [blog_post[i:i+4000] for i in range(0, len(blog_post), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(blog_post)
            
    except Exception as e:
        await update.message.reply_text(f"Sorry, there was an error: {str(e)}")

async def generate_blog_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a topic! Usage: /blog_file <topic>")
        return
    
    topic = " ".join(context.args)
    await update.message.reply_text(f"Generating blog post file about: {topic}...")
    
    try:
        blog_post = await query_gemini(topic)
        filepath = await save_blog_to_file(topic, blog_post)
        
        await update.message.reply_document(
            document=open(filepath, 'rb'),
            filename=os.path.basename(filepath),
            caption=f"Blog post about: {topic}"
        )
            
    except Exception as e:
        await update.message.reply_text(f"Sorry, there was an error: {str(e)}")

# Define an error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update caused error: {context.error}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("blog", generate_blog))
    application.add_handler(CommandHandler("blog_file", generate_blog_file))

    # Log all errors
    application.add_error_handler(error_handler)

    # Start the bot
    print("Blog Generator Bot started...")
    application.run_polling()

if __name__ == "__main__":
    main()