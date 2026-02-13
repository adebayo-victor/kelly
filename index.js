// --- 1. THE TOOLS ---
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom'); 
const qrcode = require('qrcode-terminal'); 
const express = require('express'); 
const axios = require('axios'); 

const app = express();
app.use(express.json()); 

const PYTHON_URL = "http://127.0.0.1:5000/webhook"; 
let sock; 

async function startFummsa() {
    const { state, saveCreds } = await useMultiFileAuthState('auth_session');

    sock = makeWASocket({
        auth: state,
        printQRInTerminal: false, 
        browser: ["Sideswipe FUMMSA", "Windows", "1.0"] 
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (qr) {
            console.log('🦓 SCAN THIS TO LINK SIDESWIPE:');
            qrcode.generate(qr, { small: true });
        }
        
        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect.error instanceof Boom)?.output?.statusCode !== DisconnectReason.loggedOut;
            if (shouldReconnect) startFummsa();
        } else if (connection === 'open') {
            console.log('✅ SIDESWIPE ONLINE: I am watching the chats.');
        }
    });

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return; 

        const msg = messages[0];
        const jid = msg.key.remoteJid; 

        if (!msg.message || msg.key.fromMe || jid === 'status@broadcast' || msg.message.protocolMessage) return; 

        // --- NEW METADATA EXTRACTION ---
        const isGroup = jid.includes('@g.us');
        
        // username: The name they set on WhatsApp
        const username = msg.pushName || "Unknown Recruit";
        
        // sender: If group, get the person's ID. If DM, it's just the jid.
        const senderNumber = isGroup ? msg.key.participant : jid;
        
        // taggedBy: Extract anyone mentioned in the message
        const mentions = msg.message.extendedTextMessage?.contextInfo?.mentionedJid || [];

        // TEXT EXTRACTION
        const body = msg.message.conversation || 
                     msg.message.extendedTextMessage?.text || 
                     msg.message.imageMessage?.caption || "";

        if (!body) return; 

        console.log(`📡 [${isGroup ? 'GROUP' : 'DM'}] From: ${username} (${senderNumber}) | Msg: ${body}`);

        // 6. THE HANDOFF: Send the FULL payload to Python
        try {
            await axios.post(PYTHON_URL, { 
                chatId: jid,           // Where to reply (Group or DM)
                sender: senderNumber, // Who specifically sent it
                username: username,   // What they call themselves
                text: body,
                isGroup: isGroup,
                taggedBy: mentions    // List of tagged people
            });
        } catch (e) {
            console.log("⚠️ Python Brain is offline!");
        }
    });
}

// 7. THE SENDER API: Python hits this to talk back
app.post('/send', async (req, res) => {
    const { jid, message } = req.body;
    try {
        await sock.sendMessage(jid, { text: message });
        res.status(200).json({ status: "Sent" });
    } catch (err) {
        console.error("❌ Send Error:", err.message);
        res.status(500).json({ error: err.message });
    }
});

app.listen(3000, () => {
    console.log('🌐 Node.js Gateway running on Port 3000');
    startFummsa();
});