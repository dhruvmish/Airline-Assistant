import os
import json
import uuid
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from airline_api import AirlineDataAPI, MockBookingSystem

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Intelligent Airline Chatbot", version="1.2.0")

# --- API Keys ---
openai_api_key = os.getenv("OPENAI_API_KEY")
aviationstack_api_key = os.getenv("AVIATIONSTACK_API_KEY")

# --- Data Tools ---
airline_api = AirlineDataAPI(api_key=aviationstack_api_key)
booking_system = MockBookingSystem()
print("✅ Data tools initialized.")

# --- Agent ---
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

# ---------------- HTML ----------------
@app.get("/", response_class=HTMLResponse)
async def chatbot_ui():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Intelligent Airline Assistant</title>
        <style>
            body { font-family: Arial, sans-serif; background: #1c1c1e; color: #fff;
                   display: flex; justify-content: center; align-items: center;
                   height: 100vh; margin: 0; }
            .chat-container { width: 100%; max-width: 700px; height: 90vh;
                              background: #2a2a2c; border-radius: 20px;
                              display: flex; flex-direction: column; overflow: hidden; }
            .header { background: #3a3a3c; padding: 20px; text-align: center; font-weight: bold; }
            #chatbox { flex-grow: 1; padding: 20px; overflow-y: auto;
                       display: flex; flex-direction: column; gap: 10px; }
            .message { padding: 10px 15px; border-radius: 15px; max-width: 80%; white-space: pre-wrap; }
            .user-message { background: #007aff; align-self: flex-end; }
            .bot-message { background: #3a3a3c; align-self: flex-start; }
            .input-area { display: flex; padding: 10px; gap: 10px; }
            input { flex-grow: 1; padding: 10px; border-radius: 10px; border: none; }
            button { padding: 10px 15px; border: none; border-radius: 10px; cursor: pointer; }
            #pauseBtn { background: red; color: white; display: none; }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="header">✈️ Airline Assistant</div>
            <div id="chatbox"><div class="message bot-message">Hello! I'm Sky. How can I help you today?</div></div>
            <div class="input-area">
                <input type="text" id="messageText" placeholder="Ask about a flight or booking..." onkeydown="handleKey(event)">
                <button onclick="sendMessage()">Send</button>
                <button id="pauseBtn" onclick="pauseResponse()">Pause</button>
            </div>
        </div>
        <script>
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(protocol + '//' + window.location.host + '/ws');
    const chatbox = document.getElementById("chatbox");
    const messageInput = document.getElementById("messageText");
    const pauseBtn = document.getElementById("pauseBtn");

    let currentBotMessage = null;
    let bufferText = ""; // hold full response until END arrives

    function appendMessage(sender, message) {
        const div = document.createElement("div");
        div.className = sender === "user" ? "message user-message" : "message bot-message";
        div.textContent = message || "";
        chatbox.appendChild(div);
        chatbox.scrollTop = chatbox.scrollHeight;
        return div;
    }

    
ws.onmessage = function(event) {
    const data = event.data;

    if (data === "[END]") {
        currentBotMessage = null; // Reset for the next message
        pauseBtn.style.display = "none";
        return;
    }

    if (!currentBotMessage) {
        // Create a new message bubble only for the first chunk
        currentBotMessage = appendMessage("bot", "");
    }

    // The stream sends the cumulative text, so replace the content
    // instead of appending.
    currentBotMessage.textContent = data;
    chatbox.scrollTop = chatbox.scrollHeight; // Keep scrolled to bottom
};


    function sendMessage() {
        const msg = messageInput.value.trim();
        if (!msg) return;
        appendMessage("user", msg);
        ws.send(msg);
        messageInput.value = "";
        pauseBtn.style.display = "inline-block";
    }

    function handleKey(event) { 
        if (event.key === "Enter") sendMessage(); 
    }

    function pauseResponse() {
        ws.send("__PAUSE__");
        pauseBtn.style.display = "none";
    }
</script>

    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ---------------- WebSocket ----------------
active_tasks = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    message_history = []
    print(f"New session connected: {session_id[:8]}...")

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

            # Intent detection
            intent = detect_intent(user_message)
            print(f"Session {session_id[:8]} | User: {user_message} | Intent: {intent}")

            async def stream_response():
                try:
                    # Stream chunks to the client as they arrive
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
                    # Also send the END signal on error to reset the frontend state
                    await websocket.send_text("[END]")

            task = asyncio.create_task(stream_response())
            active_tasks[session_id] = task

    except WebSocketDisconnect:
        print(f"Session {session_id[:8]} disconnected")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Intelligent Airline Chatbot with Pause...")
    uvicorn.run(app, host="0.0.0.0", port=5000)
