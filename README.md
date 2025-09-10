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
