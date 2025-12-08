# ✈️ AeroMate Frontend - AI Agent

AeroMate Frontend is the user interface for the AeroMate AI-powered virtual assistant. It allows users to interact with the backend services to get real-time flight information, locate missing luggage, and access various airport services.

## Requirements

- Python 3.8+
- Streamlit
- Requests
- Virtualenv

## Run

1. docker build -t aeromate-frontend .
2. docker run -p 8501:8501 --env-file .env aeromate-frontend
