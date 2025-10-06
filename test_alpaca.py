# Test your Alpaca connection
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from datetime import datetime, timedelta

api_key = "PKD7XKAELXF6RMQNJVUF"
api_secret = "wSaEshT8JECzLRXaz6BPWLBzk2X5ozKWCGKbBgkf"

try:
    client = StockHistoricalDataClient(api_key, api_secret)
    
    # Try a simple request
    end = datetime.now()
    start = end - timedelta(days=7)
    
    request = StockBarsRequest(
        symbol_or_symbols="AAPL",
        timeframe=TimeFrame(1, TimeFrameUnit.Minute),
        start=start,
        end=end,
        feed="iex"
    )
    
    print("Attempting data request...")
    bars = client.get_stock_bars(request)
    print(f"Success! Got {len(bars.data.get('AAPL', []))} bars")
    
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")
