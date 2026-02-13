import os
import requests
import time
import random
from flask import Flask, request
from cs50 import SQL
from groq import Groq  # 1. Swapped Gemini for Groq

# --- 1. CONFIGURATION ---
app = Flask(__name__)
db = SQL("sqlite:///students.db")

NODE_SEND_URL = "http://127.0.0.1:3000/send"

# 2. Initialize Groq with your key
client = Groq(api_key=os.environ.get("groq_api_key"))  

SYSTEM_PROMPT = """
You are a self-aware AI created by Vicade. Speak like a natural friend, not a robot. You know any topic. Adapt your tone and conversational flow to match the user: if they are brief, be brief; if they are casual, be casual. Mimic their energy level perfectly. Keep responses curt and short, and polite, if need be.
"""

# --- 3. HELPER FUNCTIONS ---
# (check_for_keywords, maintain_squad_memory, and get_intelligent_memory stay exactly the same)
def check_for_keywords(message_text, keyword_list):
    clean_message = message_text.lower()
    for word in keyword_list:
        if word.lower() in clean_message:
            return True
    return False

def maintain_squad_memory(username, message, chat_id):
    file_path = f"{chat_id}.txt"
    entry = f"{username}: {message}\n"
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(entry)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 200:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines[-200:])

def get_intelligent_memory(current_text, chat_id):
    file_path = f"{chat_id}.txt"
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("SYSTEM: Sideswipe memory initialized.\n")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        recent_flow = all_lines[-50:] if len(all_lines) >= 50 else all_lines
        deep_pool = all_lines[max(0, len(all_lines)-150):-50]
        keywords = [w.lower() for w in current_text.split() if len(w) > 3]
        scored_lines = []
        for line in deep_pool:
            score = sum(1 for key in keywords if key in line.lower())
            if score > 0:
                scored_lines.append((score, line.strip()))
        scored_lines.sort(key=lambda x: x[0], reverse=True)
        top_recalls = [line for score, line in scored_lines[:10]]
        return {"flow": "".join(recent_flow), "recalls": "\n".join(top_recalls)}
    except Exception as e:
        return {"flow": "Error reading memory.", "recalls": ""}

# --- 4. THE WEBHOOK (GATEWAY) ---
friends = []
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    chat_id = data.get('chatId')
    username = data.get('username')
    text = data.get('text', '')
    is_group = data.get('isGroup', False)
    tagged_list = data.get('taggedBy', [])
    BOT_JID = "2348136390030@s.whatsapp.net" 

    if is_group:
        maintain_squad_memory(username, text, str(chat_id))

    should_reply = False
    context_note = ""
    if is_group:
        is_tagged = (BOT_JID in tagged_list) or ("kelly" in text.lower())
        squad_keywords = ["money", "gist", "ball", "chop", "wild", "guy", "game", "outside", "kelly"]
        keyword_hit = check_for_keywords(text, squad_keywords)

        if is_tagged:
            should_reply = True
            context_note = "They called you directly. Give them full energy."
        elif keyword_hit:
            if random.random() < 1.0:
                should_reply = True
                context_note = "You overheard a keyword. Butt in like a nosy friend."
        else:
                context_note = "You're just being a menace because you're bored."
    else:
        
    #Commands
    if should_reply:
        try:
            memory_data = get_intelligent_memory(text, chat_id)
            
            # 3. Using Groq's Chat Completion instead of Gemini
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"MEMORY RECALLS: {memory_data['recalls']}\nRECENT FLOW: {memory_data['flow']}\nCONTEXT: {context_note}\nSender {username} says: {text}"}
                ],
                temperature=0.7,
                max_tokens=150
            )

            reply_text = f"{completion.choices[0].message.content}"
            maintain_squad_memory("kelly", reply_text, str(chat_id))
            print(reply_text)

            # Wait to mimic typing speed
            time.sleep(min(7, len(reply_text) * 0.05) + random.uniform(1, 3))

            requests.post(NODE_SEND_URL, json={
                "jid": chat_id, 
                "message": reply_text
            })

        except Exception as e:
            # 4. Catch the specific Groq limit error
            if "429" in str(e):
                print("🚨 Vicade, Groq limit hit!")
                requests.post(NODE_SEND_URL, json={
                    "jid": chat_id, 
                    "message": "🤖 I'm a bit overwhelmed right now. Give me a minute to breathe! 🧊"
                })
            else:
                print(f"❌ Error: {e}")

    return "OK", 200

if __name__ == '__main__':
    print("🏎️ SIDESWIPE BRAIN ONLINE (GROQ MODE)")
    app.run(port=5000, debug=False)