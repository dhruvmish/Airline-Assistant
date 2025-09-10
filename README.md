# Airline-Assistant
Intelligent Airline Chatbot
Overview

The Intelligent Airline Chatbot is a production-ready conversational assistant for airlines, built on FastAPI and powered by AI models for natural language understanding.

It provides:

AI-driven conversational support for flight search, booking, and FAQs.

Secure authentication using JWT stored in HttpOnly cookies.

Mock airline booking APIs to simulate a real-world airline system.

WebSocket support for real-time chat.

The project is containerized and deployed on Render (Free Tier) for live testing and demos.

Features

* AI-powered conversations using OpenAI models via pydantic_ai.
* Secure authentication with JWT (HttpOnly cookie).
* Fast & async backend using FastAPI.
* Mock booking system for flight reservations.
* Deployed on Render (zero-cost prototype hosting).

Tech Stack

Backend: FastAPI, SQLAlchemy, Databases

AI Layer: OpenAI models via pydantic_ai

Auth: JWT (via python-jose), passlib for hashing

Database: SQLite (default, pluggable for PostgreSQL/MySQL)

Deployment: Render (Free Tier)

Live Deployment

The chatbot is live on Render:

(https://airline-assistant-1.onrender.com)


📂 Project Structure
airly4.py           # Main FastAPI application
airline_api.py      # Airline data & mock booking system
.env                # Environment variables (ignored in git)
requirements.txt    # Python dependencies

Local Setup:
1 Clone repository
git clone https://github.com/yourusername/intelligent-airline-chatbot.git
cd intelligent-airline-chatbot

2 Create & activate virtual environment
python -m venv venv
source venv/bin/activate    # macOS/Linux
venv\Scripts\activate       # Windows

3 Install dependencies
pip install -r requirements.txt

4️ Setup environment variables

Create a .env file in the project root:

OPENAI_API_KEY=your_openai_api_key
JWT_SECRET=your_jwt_secret
JWT_ALGORITHM=HS256
DATABASE_URL=sqlite:///./airline.db

5️ Run locally
uvicorn airly4:app --reload


Local server: http://127.0.0.1:8000

🔗 API Endpoints
Authentication

POST /signup → Register new user

POST /login → Login & set JWT cookie

POST /logout → Clear cookie & logout

Chat

GET /chat → Chat interface

WS /ws/chat → Real-time WebSocket chat

Flights

GET /flights?source=A&dest=B&date=YYYY-MM-DD

POST /book → Book a flight

Example Usage
curl -X POST https://your-app-name.onrender.com/login \
  -d "username=testuser&password=secret"

 Deployment on Render

Push code to GitHub.

On Render Dashboard → Create Web Service.

Connect repo → select Free Tier.

Add environment variables in Settings.

Deploy 


# Challenges and Learnings

1. Bot not remembering context after one response

Problem: Initially, every user query was treated independently. The chatbot forgot prior questions (e.g., “What’s the status of flight AA101?” → answered, but if the user followed up with “And when does it land?” the bot had no memory).

Solution: You integrated a short-term memory (message_history) inside the WebSocket session.

Each new agent.run_stream(...) call now gets the message_history.

After every response, you extend message_history with result.new_messages().

This gives the bot short-term conversational memory for that session, enabling contextual follow-ups.

2. Streaming didn’t feel real-time

Problem: At first, responses were buffered and sent only after full generation. Users experienced delays.

Solution: You switched to streaming mode (agent.run_stream with async for chunk in result.stream_text()), pushing chunks to the client immediately.

Now, users see the bot typing word-by-word, which feels real-time.

This matches how OpenAI’s ChatGPT web client streams output.

3. Pause button

Problem: Once the bot started streaming, users couldn’t stop it — they had to wait until completion.

Solution:

You added a pause button in the frontend (pauseBtn).

On click, it sends a "__PAUSE__" signal to the server.

On the server, you check:

if user_message == "__PAUSE__":
    active_tasks[session_id].cancel()


The async task is cancelled mid-stream, and the frontend gets a [END] signal.

This mimics “stop generating” in modern chat UIs.

4. When to use OpenAI API vs. AviationStack API

OpenAI API (pydantic_ai.OpenAIModel)

Used for general conversation, natural language understanding, and intent handling.

Example: interpreting a user’s free-text query like “Is my New York to London flight on time tomorrow?”

The LLM parses intent, extracts entities (origin, destination, date), and decides whether to call a tool.

AviationStack API (AirlineDataAPI)

Used when real flight data is required:

get_flight_status(flight_number) → Live flight status.

search_routes(source, destination, date) → Available routes.

If the API call fails (e.g., rate limits, downtime), your code falls back to backup mock data.

This hybrid approach balances AI reasoning (OpenAI) with real-world facts (AviationStack).

5. Extra design improvements you implemented

JWT Auth in HttpOnly cookies → prevents XSS token theft.

SQLite via SQLAlchemy → lightweight user management.

Responsive frontend UI with modern gradients + animations.

Logout flow → cookie cleared securely.
