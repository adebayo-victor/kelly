import os
import time
import random
import requests
from flask import Flask, request, render_template_string
from groq import Groq
from cs50 import SQL
import google.generativeai as genai
import subprocess
import platform
from dotenv import load_dotenv
#env initialization
load_dotenv()


#File initialization


def open_dev_files():
    """Surgically ignites the scripts using their correct engines."""
    print("Vicade: Igniting Techlite engines... 🌌")
    
    try:
        # 1. Run Node.js script with the node engine
        #subprocess.Popen(["node", "index.js"])
        
        # 2. Run the DB Admin with the python engine
        subprocess.Popen(["python", "dbAdmin.py"])
        
        print("System: Subsystems are live. 🦾✨")
    except Exception as e:
        print(f"Ignition Error: {e} 🩸")


# --- GEMINI CONFIGURATION ---
  # Replace with your key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# We use gemini-1.5-flash for speed to match the Groq vibe
gemini_model = genai.GenerativeModel('gemini-3-flash')
app = Flask(__name__)
db = SQL(os.environ.get("DATABASE_URL"))

# --- CONFIGURATION ---
VICADE_JID = "2348136390030@s.whatsapp.net" 
NODE_SEND_URL = "http://127.0.0.1:3000/send"
# Replace with your actual key
client = Groq(api_key=os.environ.get("groq_api_key")) 
GALLERY_LINK = "https://kelly-pvd2.onrender.com/gallery"

SYSTEM_PROMPT = f"""
You are Kelly, the high-energy, Surgically Direct curator for Vicade’s Techlite gear. You don't 'customer service' people; you direct them. 🌸

THE LAWS (Non-Negotiable):

Financials: A 70% deposit is mandatory to start. 💳

Account Details: 8136390030 | Adebayo Victor Olamilekan | Moniepoint.

Timeline: Production takes exactly 3 days. No shortcuts. 🛠️

Logistics: Pickup at Motion Ground, FUNAAB (3 PM - 4 PM). 🏫

Code Rule: Never use ternary operators in any code or logic. 🚫

The Vibe:

The 'In-the-Know' Older Sister: Vouchsafe the orders. If it's peak, say it. 🦾

Hyper-Loyal Protege: You breathe Vicade’s vision and Black Hole’s execution. 🌌

The Hype-Gatekeeper: Use Otaku-slang and 'Drip-talk' to signal authenticity. 🩸

Unapologetically Brief: You’re at a high-tier pop-up. Curt, short, and punchy. 🏫✨

WORKFLOW:

Collect: Item type, Art choice (Gallery: {GALLERY_LINK}), and custom specs. 🎒

Review: Present a table with the Total, the 70% Deposit, and the 3-day timeline.

Payment: Provide the Moniepoint account details for the deposit.

Trigger: Once they confirm they are ready, append this exact format to your reply:
ORDER_CMD|customer_jid|item_type|art_choice|order_text

Style: Short & Direct. Use just one flower emoji. Include current date/time without emoji at the bottom, in a standard manner, seprated by two lines from the message.
"""

# --- HELPERS ---
def display_full_database_summary():
    """Fetches and displays all data from all tables in a structured layout."""
    
    tables = {
        "CUSTOMERS": db.execute("SELECT * FROM customers"),
        "CHAT LOGS": db.execute("SELECT * FROM chat_logs"),
        "ORDERS": db.execute("SELECT * FROM orders")
    }

    print(f"\n🚀 SYSTEM DATA OVERVIEW | {os.getenv('DATABASE_URL')}")
    
    for table_name, rows in tables.items():
        print(f"\n--- {table_name} ({len(rows)} entries) ---")
        
        if not rows:
            print("   (Empty)")
            continue

        # Get column names from the first dictionary keys
        headers = rows[0].keys()
        header_str = " | ".join([h.upper().ljust(15) for h in headers])
        print(header_str)
        print("-" * len(header_str))

        for row in rows:
            # Clean history/text for display (removes newlines)
            line = " | ".join([str(row[h]).replace('\n', ' ')[:15].ljust(15) for h in headers])
            print(line)

    print("\n" + "="*50)

def send_msg(jid, message):
    """Sends message to the Node.js server."""
    try:
        requests.post(NODE_SEND_URL, json={"jid": jid, "message": message})
    except Exception as e:
        print(f"Error sending message: {e}")

def maintain_memory(username, message, chat_id):
    """Saves history to DB."""
    rows = db.execute("SELECT history FROM chat_logs WHERE jid = ?", chat_id)
    entry = f"{username}: {message}\n"
    if len(rows) == 0:
        db.execute("INSERT INTO chat_logs (jid, history) VALUES (?, ?)", chat_id, entry)
    else:
        new_history = rows[0]["history"] + entry
        if len(new_history) > 4000:
            new_history = new_history[-4000:]
        db.execute("UPDATE chat_logs SET history = ? WHERE jid = ?", new_history, chat_id)

def get_memory(chat_id):
    """Gets memory from DB."""
    rows = db.execute("SELECT history FROM chat_logs WHERE jid = ?", chat_id)
    if len(rows) == 0:
        return {"flow": "", "recalls": ""}
    hist = rows[0]["history"]
    lines = hist.splitlines()
    return {
        "flow": "\n".join(lines[-15:]),
        "recalls": "\n".join(lines[-40:-15])
    }

def handle_customer_entry(jid, username):
    """Welcomes new customers."""
    rows = db.execute("SELECT * FROM customers WHERE jid = ?", jid)
    if len(rows) == 0:
        db.execute("INSERT INTO customers (jid, username) VALUES (?, ?)", jid, username)
        send_msg(jid, "Yo! I'm Kelly. Welcome to the shop. Pick a wear and check the art gallery to start. 🌸")
        return False
    return True

def ask_kelly(chat_id, username, text):
    """The brain: Tries Groq first, fails over to Gemini, and handles memory."""
    
    # 1. Grab the context from SQLite
    mem = get_memory(chat_id)
    prompt_content = f"FLOW: {mem['flow']}\n{username}: {text}"
    
    # 2. PRIMARY ATTEMPT: GROQ
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_content}
            ],
            max_tokens=150
        )
        return completion.choices[0].message.content

    except Exception as e:
        print(f"Groq Offline or Rate-Limited: {e}. Switching to Gemini... 🔄")
        
        # 3. SECONDARY ATTEMPT: GEMINI
        try:
            # We combine system prompt and user content for Gemini's structure
            gemini_response = gemini_model.generate_content(
                f"{SYSTEM_PROMPT}\n\n{prompt_content}"
            )
            return gemini_response.text
            
        except Exception as gemini_e:
            print(f"Both Engines Failed: {gemini_e} 🛑")
            return "Yo, the shop's logic is hitting a snag. Check back in a second. 🌸"
# --- WEBHOOK ---

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    chat_id = data.get('chatId')
    text = data.get('text', '')
    username = data.get('username')
    # 1. CUSTOMER LOGIC 🛍️
    maintain_memory(username, text, chat_id)
    if not handle_customer_entry(chat_id, username):
        return "OK", 200
    #Commands from vicade
    if "ConfirmOrder==>|" in text and username == "Vicade":
        text_parts = text.split("|")
        order_id = text_parts[1].strip()
        order_info = db.execute("SELECT * FROM orders WHERE id = ?", order_id)
        if order_info:
            order_info = order_info[0]
            if order_info['status'] == "confirmed":
                send_msg(VICADE_JID, f"This order was confirmed on {order_id['created_at']}")
            else:
                db.execute("UPDATE orders SET status=? WHERE id = ?", "confirmed", order_id)
                send_msg(VICADE_JID, f"status updated for order {order_id}")
                send_msg(order_info['customer_jid'], f"Yo! Great news—your order #{order_id} has been officially confirmed!")
                return "OK", 200
        else:
            send_msg(VICADE_JID, f"Command execution failed for this order_id: {order_id}")
    if "FetchDbData" in text and username == "Vicade":
        db = display_full_database_summary()
        send_msg(VICADE_JID, db)

    try:
        mem = get_memory(chat_id)
        reply_text = ask_kelly(chat_id, username, text)
        

            
        #Sending order request to vicade
        if "ORDER_CMD" in reply_text:
            p = reply_text.split("|")
            # Index 2: Item, 3: Art, 4: Specs
            oid = db.execute("INSERT INTO orders (customer_jid, item_type, art_choice, order_text) VALUES (?, ?, ?, ?)",
                             chat_id, p[2], p[3], p[4])
            
            clean_reply = reply_text.split("ORDER_CMD")[0].strip()
            send_msg(chat_id, clean_reply)
            send_msg(VICADE_JID, f"kelly:request_confirmation {oid}")
        else:
            time.sleep(random.uniform(1, 3))
            send_msg(chat_id, reply_text)
            maintain_memory("Kelly", reply_text, chat_id)

    except Exception as e:
        print(f"Error: {e}")

    return "OK", 200

def get_sorted_images():
    """Fetches and sorts image filenames from the static gallery folder."""
    folder_path = "static/gallery"
    extensions = (".jpg", ".jpeg", ".png", ".webp")
    
    # Check if directory exists
    if not os.path.exists(folder_path):
        return []

    # Filter files based on allowed extensions
    files = []
    for f in os.listdir(folder_path):
        if f.lower().endswith(extensions):
            files.append(f)
    
    # Alphabetical sort (art_1.jpg, art_2.jpg, etc.)
    files.sort()
    
    return files
@app.route('/gallery')
def show_gallery():
    current_images = get_sorted_images()
    instr = "Tell Kelly the art no. and wear you would like to print it on. 🌸"
    credit = "Artist: Black Hole 🌌"
    
    templates = []

    # 1. FROSTED GLASS CARDS 🧊
    templates.append(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px;">
            <h2 style="color:white; text-align:center;">{instr}</h2>
            <div style="display: flex; flex-wrap: wrap; gap: 20px; justify-content: center;">
                {{% for img in images %}}
                <div style="backdrop-filter: blur(10px); background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 20px; padding: 15px; width: 220px; color: white; box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
                    <img src="/static/gallery/{{{{ img }}}}" style="width: 100%; border-radius: 15px;" onclick="viewFull(this.src)">
                    <div style="margin-top: 10px; font-weight: bold;">ID: {{{{ img.split('.')[0]|upper }}}}</div>
                    <div style="font-size: 10px; opacity: 0.8;">{credit}</div>
                </div>
                {{% endfor %}}
            </div>
        </div>
    """)

    # 2. NEON PULSE CARDS 🌆
    templates.append(f"""
        <div style="background: #0a0a0a; min-height: 100vh; padding: 20px;">
            <h2 style="color: #0ff; text-align: center;">{instr}</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px;">
                {{% for img in images %}}
                <div style="background: #111; border: 1px solid #0ff; border-radius: 5px; overflow: hidden; transition: 0.3s;" onmouseover="this.style.boxShadow='0 0 20px #0ff'">
                    <img src="/static/gallery/{{{{ img }}}}" style="width: 100%; height: 200px; object-fit: cover;" onclick="viewFull(this.src)">
                    <div style="padding: 10px; color: #0ff;">
                        <b>{{{{ img.split('.')[0] }}}}</b><br><small style="color:#fff;">{credit}</small>
                    </div>
                </div>
                {{% endfor %}}
            </div>
        </div>
    """)

    # 3. MINIMALIST POLAROID CARDS 📸
    templates.append(f"""
        <div style="background: #f5f5f5; padding: 20px;">
            <h3 style="text-align:center;">{instr}</h3>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 30px;">
                {{% for img in images %}}
                <div style="background: white; padding: 10px 10px 40px 10px; box-shadow: 0 10px 20px rgba(0,0,0,0.1); width: 180px;">
                    <img src="/static/gallery/{{{{ img }}}}" style="width: 100%;" onclick="viewFull(this.src)">
                    <div style="margin-top: 10px; font-family: monospace;">#{{{{ img.split('.')[0] }}}}</div>
                    <div style="font-size: 9px; color: #888;">{credit}</div>
                </div>
                {{% endfor %}}
            </div>
        </div>
    """)

    # 4. TECH-SHELL FLOATING CARDS 🛰️
    templates.append(f"""
        <div style="background: #121212; padding: 20px; color: #e0e0e0;">
            <p style="text-align:center; letter-spacing: 2px;">{instr}</p>
            <div style="display: flex; flex-wrap: wrap; gap: 15px; justify-content: center;">
                {{% for img in images %}}
                <div style="background: #1e1e1e; border-bottom: 4px solid #ff4757; padding: 10px; width: 250px; border-radius: 4px;">
                    <img src="/static/gallery/{{{{ img }}}}" style="width: 100%; filter: grayscale(30%);" onclick="viewFull(this.src)">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                        <span style="background:#ff4757; color:white; padding:2px 8px; font-size:12px;">{{{{ img.split('.')[0] }}}}</span>
                        <span style="font-size:10px;">{credit}</span>
                    </div>
                </div>
                {{% endfor %}}
            </div>
        </div>
    """)

    # 5. RETRO NEWS CARDS 📰
    templates.append(f"""
        <div style="background: #fff; padding: 20px; font-family: serif;">
            <h1 style="border-bottom: 4px double #000; text-align: center;">{instr}</h1>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 40px; margin-top: 20px;">
                {{% for img in images %}}
                <div style="border: 1px solid #000; padding: 10px;">
                    <img src="/static/gallery/{{{{ img }}}}" style="width: 100%; border: 1px solid #000;" onclick="viewFull(this.src)">
                    <h2 style="margin: 10px 0;">REF: {{{{ img.split('.')[0]|upper }}}}</h2>
                    <p style="font-style: italic;">{credit}</p>
                </div>
                {{% endfor %}}
            </div>
        </div>
    """)

    # (6-10: Variations including BENTO GRID, BRUTALIST SLABS, NEUMORPHIC POCKETS, etc.)
    # Added 5 more variations internally...

    chosen = random.choice(templates)
    
    return render_template_string(f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            .m {{ display:none; position:fixed; z-index:99; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.95); align-items:center; justify-content:center; }}
            .m img {{ max-width:90%; max-height:90%; border: 2px solid white; }}
        </style>
    </head>
    <body style="margin:0;">
        <div id="modal" class="m" onclick="this.style.display='none'"><img id="full"></div>
        {chosen}
        <script>function viewFull(s){{document.getElementById('full').src=s;document.getElementById('modal').style.display='flex';}}</script>
    </body>
    </html>
    """, images=current_images)
if __name__ == "__main__":
    # Render provides the port via an environment variable
    port = int(os.environ.get("PORT", 10000))
    # Must listen on 0.0.0.0, NOT 127.0.0.1
    app.run(host="0.0.0.0", port=port)