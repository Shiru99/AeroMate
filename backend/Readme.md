# ✈️ AeroMate Backend - AI Agent

AeroMate Backend is the server-side component of the AeroMate AI-powered virtual assistant. It handles requests from the frontend, processes user queries, and interacts with various APIs to provide real-time flight information, luggage tracking, and airport services.

## Setup

1. python3 -m venv venv
2. source venv/bin/activate
3. pip install -r requirements.txt
4. uvicorn app.app:app --reload


## Run

1. docker build -t aeromate-backend .
2. docker run -p 8000:8000 --env-file .env aeromate-backend