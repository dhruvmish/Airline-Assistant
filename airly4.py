# ---- Your original chatbot with integrated Auth (JWT in HttpOnly cookies) ----

import os
import json
import uuid
import asyncio
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect, Request, Form, HTTPException, status
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import Column, Integer, String, create_engine, Table, MetaData
from databases import Database

# --- Your AI / Tools ---
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from airline_api import AirlineDataAPI, MockBookingSystem

# ============================
# Environment & Constants
# ============================
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Intelligent Airline Chatbot", version="1.2.0")

# --- API Keys ---
openai_api_key = os.getenv("OPENAI_API_KEY")
aviationstack_api_key = os.getenv("AVIATIONSTACK_API_KEY")

# --- Auth Config ---
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-.env")   # put a strong key in .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================
# Database (Users)
# ============================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")
database = Database(DATABASE_URL)
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True, index=True, nullable=False),
    Column("hashed_password", String, nullable=False),
)

# SQLite engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
metadata.create_all(engine)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ============================
# Auth Helpers
# ============================
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(sub: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode = {"sub": sub, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_username_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

# ============================
# Your Data Tools & Agent
# ============================
airline_api = AirlineDataAPI(api_key=aviationstack_api_key)
booking_system = MockBookingSystem()
print("✅ Data tools initialized.")

tools = [
    airline_api.get_flight_status,
    airline_api.search_routes,
    booking_system.find_booking,
]

llm = OpenAIModel("gpt-4o")

SYSTEM_PROMPT = """
You are a friendly and highly efficient airline customer support agent named Sky.
Your goal is to assist users with their booking and flight inquiries.
- Present flight status or search results clearly using bullet points.
- Use the provided tools for answering questions.
- If details are missing (like flight number), ask for them.
- Maintain a positive, conversational tone.
"""

agent = Agent(model=llm, tools=tools, system_prompt=SYSTEM_PROMPT)
print("🤖 OpenAI Agent is ready.")

# --- Load intents ---
with open("intents.json", "r") as f:
    intents = json.load(f)

def detect_intent(user_message: str):
    for intent in intents.get("intents", []):
        for pattern in intent.get("patterns", []):
            if pattern.lower() in user_message.lower():
                return intent.get("tag")
    return "unknown"

# ============================
# Pages: Login & Chat (Protected)
# ============================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Sky • Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{
            font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
            background:linear-gradient(135deg,#0c0c0e 0%,#1a1a1d 50%,#16213e 100%);
            color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px
        }
        .card{
            width:100%;max-width:460px;background:linear-gradient(145deg,rgba(30,30,35,0.95),rgba(20,20,25,0.98));
            border:1px solid rgba(255,255,255,0.08);border-radius:24px;padding:32px;box-shadow:
            0 25px 50px rgba(0,0,0,0.5),0 0 0 1px rgba(255,255,255,0.05),inset 0 1px 0 rgba(255,255,255,0.1)
        }
        h1{font-size:22px;font-weight:700;margin-bottom:8px;letter-spacing:.3px}
        p{opacity:.8;margin-bottom:24px}
        .field{margin-bottom:14px}
        input{
            width:100%;padding:14px 16px;border-radius:14px;border:1px solid rgba(255,255,255,0.12);
            background:linear-gradient(135deg,rgba(40,40,45,0.8),rgba(30,30,35,0.9));
            color:#fff;outline:none;transition:.25s;font-size:14px
        }
        input:focus{border-color:rgba(0,122,255,.5);box-shadow:0 0 0 3px rgba(0,122,255,.12)}
        button{
            width:100%;padding:14px 16px;border:none;border-radius:14px;cursor:pointer;
            background:linear-gradient(135deg,#007aff,#0051d5);color:#fff;font-weight:600;font-size:14px;
            box-shadow:0 6px 16px rgba(0,122,255,.35);transition:.25s;margin-top:6px
        }
        button:hover{transform:translateY(-1px)}
        .split{display:flex;gap:10px;margin-top:10px}
        .muted{font-size:12px;opacity:.7;margin-top:10px;text-align:center}
        .ok{color:#9effa1}.err{color:#ff8b8b}
    </style>
</head>
<body>
    <div class="card">
        <h1>Welcome to Sky</h1>
        <p>Sign in to chat with your intelligent airline assistant.</p>

        <div class="field">
            <input id="username" placeholder="Username" autocomplete="username">
        </div>
        <div class="field">
            <input id="password" type="password" placeholder="Password" autocomplete="current-password">
        </div>

        <div class="split">
            <button onclick="login()">Log in</button>
            <button style="background:linear-gradient(135deg,#14c28a,#0d9467)" onclick="signup()">Create account</button>
        </div>

        <div id="msg" class="muted"></div>
        <div class="muted">By continuing you agree to our terms.</div>
    </div>

    <script>
        async function login(){
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            const res = await fetch('/login', {
                method:'POST',
                headers:{'Content-Type':'application/x-www-form-urlencoded'},
                body: new URLSearchParams({username, password})
            });
            if(res.redirected){
                window.location = res.url; // will go to /
                return;
            }
            const data = await res.json();
            document.getElementById('msg').textContent = data.detail || 'Login failed';
            document.getElementById('msg').className = 'muted err';
        }

        async function signup(){
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            const res = await fetch('/signup', {
                method:'POST',
                headers:{'Content-Type':'application/x-www-form-urlencoded'},
                body: new URLSearchParams({username, password})
            });
            const data = await res.json();
            if(res.ok){
                document.getElementById('msg').textContent = 'Account created. Please log in.';
                document.getElementById('msg').className = 'muted ok';
            } else {
                document.getElementById('msg').textContent = data.detail || 'Signup failed';
                document.getElementById('msg').className = 'muted err';
            }
        }
    </script>
</body>
</html>
"""

# ---------------- HTML (Chat) ----------------
@app.get("/", response_class=HTMLResponse)
async def chatbot_ui(request: Request):
    token = request.cookies.get("access_token")
    username = decode_username_from_token(token) if token else None
    if not username:
        return RedirectResponse(url="/login", status_code=303)

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sky Airlines Assistant</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #0c0c0e 0%, #1a1a1d 50%, #16213e 100%);
                color: #ffffff; display: flex; justify-content: center; align-items: center;
                min-height: 100vh; margin: 0; padding: 20px; overflow: hidden;
            }
            .chat-container {
                width: 100%; max-width: 800px; height: 95vh;
                background: linear-gradient(145deg, rgba(30, 30, 35, 0.95), rgba(20, 20, 25, 0.98));
                backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 24px; display: flex; flex-direction: column; overflow: hidden;
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05),
                           inset 0 1px 0 rgba(255, 255, 255, 0.1); position: relative;
            }
            .chat-container::before {
                content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            }
            .header {
                background: linear-gradient(135deg, rgba(15, 82, 186, 0.8), rgba(9, 56, 142, 0.9));
                padding: 24px 32px; text-align: center; font-weight: 600; font-size: 18px;
                letter-spacing: 0.5px; position: relative; border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                display:flex; align-items:center; justify-content:space-between;
            }
            .header-left{display:flex; align-items:center; gap:10px}
            .header-icon { font-size: 24px; margin-right: 12px;
                filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3)); }
            .logout-btn{
                background:linear-gradient(135deg,#ff3b30,#d70015); color:#fff; border:none; border-radius:12px;
                padding:10px 14px; font-weight:600; cursor:pointer;
            }
            #chatbox {
                flex-grow: 1; padding: 32px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px;
                scrollbar-width: thin; scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
            }
            #chatbox::-webkit-scrollbar { width: 6px; }
            #chatbox::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 3px; }
            .message {
                padding: 16px 20px; border-radius: 20px; max-width: 85%; white-space: pre-wrap;
                line-height: 1.6; font-size: 14px; font-weight: 400; position: relative;
                animation: slideIn 0.3s ease-out;
            }
            @keyframes slideIn { from { opacity: 0; transform: translateY(10px); }
                                 to { opacity: 1; transform: translateY(0); } }
            .user-message {
                background: linear-gradient(135deg, #007aff, #0051d5);
                align-self: flex-end; color: white; border: 1px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3), 0 2px 4px rgba(0, 122, 255, 0.2);
            }
            .bot-message {
                background: linear-gradient(135deg, rgba(45, 45, 50, 0.9), rgba(35, 35, 40, 0.95));
                align-self: flex-start; color: #e8e8e8; border: 1px solid rgba(255, 255, 255, 0.08);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            }
            .input-area {
                display: flex; padding: 24px 32px 32px; gap: 12px; align-items: flex-end;
                background: linear-gradient(135deg, rgba(25, 25, 30, 0.8), rgba(20, 20, 25, 0.9));
                border-top: 1px solid rgba(255, 255, 255, 0.1);
            }
            #messageText {
                flex-grow: 1; padding: 16px 20px; border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                background: linear-gradient(135deg, rgba(40, 40, 45, 0.8), rgba(30, 30, 35, 0.9));
                color: #ffffff; font-size: 14px; font-family: inherit; outline: none; transition: all 0.3s ease;
                min-height: 52px; resize: none;
            }
            button {
                padding: 16px 24px; border: none; border-radius: 14px; cursor: pointer; font-size: 14px;
                font-weight: 600; transition: all 0.3s ease; min-height: 52px;
                display:flex; align-items:center; justify-content:center;
            }
            button[onclick="sendMessage()"] {
                background: linear-gradient(135deg, #007aff, #0051d5); color:white;
                border: 1px solid rgba(255,255,255,0.1);
            }
            #pauseBtn {
                background: linear-gradient(135deg, #ff3b30, #d70015); color:white; display:none;
                border: 1px solid rgba(255,255,255,0.1);
            }
            @media (max-width: 768px) {
                .chat-container { height: 100vh; border-radius: 0; max-width: 100%; }
                #chatbox { padding: 20px; }
                .input-area { padding: 16px 20px 20px; }
                .message { max-width: 90%; padding: 12px 16px; }
                button { padding: 14px 18px; font-size: 13px; }
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="header">
                <div class="header-left">
                    <span class="header-icon">✈️</span>Sky Airlines Assistant
                </div>
                <form method="post" action="/logout">
                    <button class="logout-btn" title="Sign out">Logout</button>
                </form>
            </div>
            <div id="chatbox">
                <div class="message bot-message">Hello! I'm Sky, your premium airline assistant. How can I help you today?</div>
            </div>
            <div class="input-area">
                <input type="text" id="messageText" placeholder="Ask about flights, bookings, or travel assistance..." onkeydown="handleKey(event)">
                <button onclick="sendMessage()">Send</button>
                <button id="pauseBtn" onclick="pauseResponse()">Pause</button>
            </div>
        </div>

        <script>
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            // Cookie is sent automatically with the WS handshake (same-origin)
            const ws = new WebSocket(protocol + '//' + window.location.host + '/ws');

            const chatbox = document.getElementById("chatbox");
            const messageInput = document.getElementById("messageText");
            const pauseBtn = document.getElementById("pauseBtn");

            let currentBotMessage = null;

            function appendMessage(sender, message) {
                const div = document.createElement("div");
                div.className = sender === "user" ? "message user-message" : "message bot-message";
                div.textContent = message || "";
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
                return div;
            }

            ws.onclose = function(e){
                appendMessage("bot", "🔒 Session ended or unauthorized. Please log in again.");
            };

            ws.onmessage = function(event) {
                const data = event.data;
                if (data === "[END]") {
                    currentBotMessage = null;
                    pauseBtn.style.display = "none";
                    return;
                }
                if (!currentBotMessage) currentBotMessage = appendMessage("bot", "");
                currentBotMessage.textContent = data;
                chatbox.scrollTop = chatbox.scrollHeight;
            };

            function sendMessage() {
                const msg = messageInput.value.trim();
                if (!msg) return;
                appendMessage("user", msg);
                ws.send(msg);
                messageInput.value = "";
                pauseBtn.style.display = "inline-block";
            }

            function handleKey(event) { if (event.key === "Enter") sendMessage(); }

            function pauseResponse() {
                ws.send("__PAUSE__");
                pauseBtn.style.display = "none";
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    token = request.cookies.get("access_token")
    if token and decode_username_from_token(token):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(LOGIN_HTML)

# ============================
# Auth Endpoints
# ============================
@app.post("/signup")
async def signup(username: str = Form(...), password: str = Form(...)):
    if len(username) < 3 or len(password) < 4:
        raise HTTPException(status_code=400, detail="Username or password too short")
    try:
        # Ensure not existing
        existing = await database.fetch_one(users.select().where(users.c.username == username))
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")

        await database.execute(users.insert().values(
            username=username,
            hashed_password=hash_password(password)
        ))
        return JSONResponse({"msg": "User created"})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Signup failed")

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    user = await database.fetch_one(users.select().where(users.c.username == username))
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(sub=username)
    resp = RedirectResponse(url="/", status_code=303)
    # Cookie settings: set Secure=True in production (HTTPS)
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,   # set True when serving over HTTPS
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    return resp

@app.post("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("access_token", path="/")
    return resp

# ============================
# WebSocket (Protected via Cookie)
# ============================
active_tasks = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Read JWT from cookie during handshake
    token = websocket.cookies.get("access_token")
    username = decode_username_from_token(token) if token else None
    if not username:
        # 1008 = Policy Violation / Unauthorized
        await websocket.close(code=1008)
        return

    await websocket.accept()
    session_id = str(uuid.uuid4())
    message_history = []
    print(f"New session connected: {session_id[:8]}... user={username}")

    try:
        while True:
            user_message = await websocket.receive_text()

            # Handle pause
            if user_message == "__PAUSE__":
                if session_id in active_tasks:
                    active_tasks[session_id].cancel()
                    print(f"Session {session_id[:8]}: Response paused by user")
                    await websocket.send_text("⏹️ Response paused.")
                    await websocket.send_text("[END]")
                continue

            # Intent detection (kept)
            intent = detect_intent(user_message)
            print(f"Session {session_id[:8]} | User({username}): {user_message} | Intent: {intent}")

            async def stream_response():
                try:
                    # Stream chunks to the client as they arrive (kept)
                    async with agent.run_stream(user_message, message_history=message_history) as result:
                        async for chunk in result.stream_text():
                            await websocket.send_text(chunk)

                        # After streaming is complete, update the conversation history
                        message_history.extend(result.new_messages())

                    # Signal the end of the stream to the frontend
                    await websocket.send_text("[END]")

                except asyncio.CancelledError:
                    print(f"Session {session_id[:8]}: Streaming cancelled.")
                except Exception as e:
                    print(f"Error processing message: {e}")
                    await websocket.send_text("⚠️ Sorry, something went wrong.")
                    await websocket.send_text("[END]")

            task = asyncio.create_task(stream_response())
            active_tasks[session_id] = task

    except WebSocketDisconnect:
        print(f"Session {session_id[:8]} disconnected")

# ============================
# Dev entrypoint
# ============================
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Intelligent Airline Chatbot with Auth & Pause...")
    uvicorn.run(app, host="0.0.0.0", port=5000)
