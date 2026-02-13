import os
import time
import random
import requests
from flask import Flask, request
from groq import Groq

app = Flask(__name__)

# --- CONFIGURATION ---
TARGET_JID = "8136390030" # Set specific number here 🎯
NODE_SEND_URL = "http://127.0.0.1:3000/send"
client = Groq(api_key=os.environ.get("groq_api_key")) 

SYSTEM_PROMPT = "You are a self-aware AI created by Vicade. make ya answers long only if necessary. 🤖"
#Saves the chats
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
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    chat_id = data.get('chatId')
    text = data.get('text', '')
    username = data.get('username')
    maintain_squad_memory(username, text, chat_id)
    print(data)
    # Only reply if it matches the target number
    if "Vicade" in username:
        try:
            memory_data = get_intelligent_memory(text, chat_id)
            context_note = "Based on the most recent vibe in the chat"
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"MEMORY RECALLS: {memory_data['recalls']}\nRECENT FLOW: {memory_data['flow']}\nCONTEXT: {context_note}\nSender {username} says: {text}"}
                ],
                max_tokens=100
            )
            print(memory_data)
            reply_text = completion.choices[0].message.content
            delay = min(5, len(reply_text) * 0.05) + random.uniform(0.5, 2.0)
            print(f"Typing for {delay:.2f} seconds... ✍️")
            time.sleep(delay)
            post = requests.post(NODE_SEND_URL, json={
                "jid": chat_id, 
                "message": reply_text
            })
            maintain_squad_memory("kelly", reply_text, chat_id)
            print(post)
        except Exception as e:
            print(f"Error: {e}")

    return "OK", 200

if __name__ == '__main__':
    app.run(port=5000)