# ✈️ AeroMate - AI Agent

AeroMate is an AI-powered virtual assistant designed to enhance your travel experience. Whether you need assistance like flight detials or want to locate missing luggage at any specific airport, AeroMate is here to help!

## Features

- **Flight Information**: Get real-time updates on flight status, delays, and gate information.
- **Luggage Assistance**: Locate missing luggage and get updates on its status.
- **Airport Services**: Find amenities, lounges, and services available at the airport.
- **Travel Tips**: Receive personalized travel tips and recommendations.
- **Multi-Language Support**: Communicate in multiple languages for a seamless experience.
- **24/7 Availability**: Access assistance anytime, anywhere.

## Run

1. docker run -p 8000:8000 --env-file .env aeromate-backend 
2. docker run -p 8501:8501 --env-file .env aeromate-frontend
3. Open your browser and navigate to `http://localhost:8501` to interact with AeroMate.