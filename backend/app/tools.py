import os
from langchain_core.tools import tool

from langchain_community.tools import DuckDuckGoSearchRun
from serpapi import GoogleSearch
import yfinance as yf
import psutil
import platform


# ==========================================
# Web Search Tool
# ==========================================
@tool
def get_web_search(query: str):
    """
    Useful for finding latest news, current events, or general information that is not in the training data.
    """
    search = DuckDuckGoSearchRun(region="us-en", safesearch="Moderate")
    return search.invoke(query)

# ==========================================
# Stock Price Tool
# ==========================================
@tool
def get_stock_price(ticker: str):
    """
    Fetches the current stock price for a given company ticker symbol (e.g., 'AAPL' for Apple, 'GOOGL' for Google, 'RELIANCE.NS' for Reliance).
    """
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")['Close'].iloc[-1]
        currency = stock.info.get("currency", "USD")

        return f"The current price of {ticker} is {price:.2f} {currency}."
    except Exception as e:
        return f"Error fetching stock price for {ticker}: {str(e)}"
    
# ==========================================
# Currency Exchange Rate Tool
# ==========================================
@tool
def get_currency_rate(from_currency: str, to_currency: str):
    """
    Fetches the live currency exchange rate.
    Args:
        from_currency: The currency code to convert from (e.g., 'USD', 'EUR', 'INR').
        to_currency: The currency code to convert to (e.g., 'INR', 'GBP', 'JPY').
    """
    # Yahoo Finance format is "EURUSD=X" or "USDINR=X"
    ticker = f"{from_currency}{to_currency}=X".upper()
    
    try:
        data = yf.Ticker(ticker)
        # Get the latest close price (which is the current exchange rate)
        hist = data.history(period="1d")
        
        if hist.empty:
            return f"Could not find exchange rate for {from_currency} to {to_currency}. Please check the currency codes."
            
        rate = hist['Close'].iloc[-1]
        return f"1 {from_currency} = {rate:.4f} {to_currency} (Source: Yahoo Finance)"
        
    except Exception as e:
        return f"Error fetching rate for {ticker}: {str(e)}"


# ==========================================
# Google Flights Search Tool
# ==========================================
@tool
def get_flight_details(departure_id: str, arrival_id: str, date: str):
    """
    Searches for real flight prices using Google Flights.
    Args:
        departure_id: Airport code for departure (e.g., 'BOM' for Mumbai, 'LHR' for London).
        arrival_id: Airport code for arrival (e.g., 'DXB' for Dubai, 'JFK' for New York).
        date: Date of travel in YYYY-MM-DD format (e.g., '2025-12-25').
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return "Error: SERPAPI_KEY is missing in environment variables."

    params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": date,
        "currency": "INR",
        "hl": "en",
        "api_key": api_key
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Check if we got valid results
        if "error" in results:
            return f"Google Flights Error: {results['error']}"
            
        best_flights = results.get("best_flights", [])
        
        if not best_flights:
            return "No flights found for this date/route."

        # Format the top 3 flights
        output = [f"✈️ Flights from {departure_id} to {arrival_id} on {date}:"]
        
        for flight in best_flights[:3]:
            flight_data = flight['flights'][0]
            airline = flight_data.get('airline', 'Unknown Airline')
            price = flight.get('price', 'N/A')
            duration = flight_data.get('duration', 0) // 60  # Convert mins to hours
            
            output.append(
                f"- {airline}: ₹{price} | Duration: {duration}h"
            )
            
        return "\n".join(output)

    except Exception as e:
        return f"Error connecting to Google Flights: {str(e)}"
    
# ==========================================
# System Stats Tool
# ==========================================
@tool
def get_system_stats():
    """
    Returns the current system statistics including CPU usage, RAM usage, Disk space, and OS information. Useful for checking server health or performance.
    """
    # System Info
    uname = platform.uname()
    os_info = f"{uname.system} {uname.release}"
    
    # CPU
    cpu_usage = psutil.cpu_percent(interval=1)
    
    # Memory
    mem = psutil.virtual_memory()
    ram_total = f"{mem.total / (1024**3):.2f} GB"
    ram_used = f"{mem.used / (1024**3):.2f} GB"
    ram_percent = f"{mem.percent}%"
    
    # Disk
    disk = psutil.disk_usage('/')
    disk_total = f"{disk.total / (1024**3):.2f} GB"
    disk_free = f"{disk.free / (1024**3):.2f} GB"
    
    return (
        f"🖥️ **System Status**:\n"
        f"- OS: {os_info}\n"
        f"- CPU Usage: {cpu_usage}%\n"
        f"- RAM: {ram_used} used / {ram_total} total ({ram_percent})\n"
        f"- Disk Free: {disk_free} / {disk_total}"
    )

# ==========================================
# Calculator Tool
# ==========================================
@tool
def get_calculator(expression: str):
    """
    Evaluates a mathematical expression to get a precise answer. Useful for currency conversion math, splitting bills, or flight cost estimation.
    Args:
        expression: A math string like "45000 / 3" or "(120 * 83) + 500"
    """
    allowed_chars = "0123456789+-*/(). "
    if not all(char in allowed_chars for char in expression):
        return "Error: Invalid characters in math expression. Only numbers and basic operators allowed."
    
    try:
        result = eval(expression, {"__builtins__": None}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation Error: {str(e)}"