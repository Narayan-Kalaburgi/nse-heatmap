from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import yfinance as yf
import pandas as pd

app = FastAPI()

import requests
import re
import io

yf_session = requests.Session()
yf_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
})

fallback_fo_symbols = [
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", "ALKEM", "AMBUJACEM", 
    "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", 
    "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", 
    "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "BSE", "BSOFT", 
    "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", 
    "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", 
    "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", 
    "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", 
    "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", 
    "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", "IPCALAB", "IRCTC", "ITC", 
    "JINDALSTEL", "JKCEMENT", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "L&TFH", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", 
    "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", 
    "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", 
    "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB", 
    "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", 
    "SHREECEM", "SIEMENS", "SRF", "SUNTV", "SUNPHARMA", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", 
    "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", 
    "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"
]

fallback_nifty50_symbols = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", 
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL", 
    "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", 
    "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", 
    "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC", 
    "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT", 
    "LTIM", "M&M", "MARUTI", "NTPC", "NESTLEIND", "ONGC", 
    "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", 
    "TCS", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TECHM", 
    "TITAN", "ULTRACEMCO", "WIPRO", "SHRIRAMFIN"
]

def get_nifty50_symbols():
    try:
        url = 'https://niftyindices.com/IndexConstituent/ind_nifty50list.csv'
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            df = pd.read_csv(io.StringIO(r.text))
            return set(df['Symbol'].tolist())
    except Exception as e:
        print(f"Error fetching Nifty 50 list: {e}")
    return set(fallback_nifty50_symbols)

def get_live_fo_symbols():
    try:
        r = requests.get('https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json', timeout=15)
        data = r.json()
        
        fo_symbols = set()
        for item in data:
            if item.get('exch_seg') == 'NFO' and item.get('instrumenttype') == 'FUTSTK':
                sym = item.get('name')
                # Filter out test stocks and None
                if sym and "NSETEST" not in sym:
                    fo_symbols.add(sym)
                    
        live_symbols = list(fo_symbols)
        if len(live_symbols) > 200:
            return live_symbols
    except Exception as e:
        print(f"Error fetching live F&O list from Angel One: {e}")
        
    return fallback_fo_symbols

# Fetch symbols once on startup, or we can fetch per request. 
# Fetching per request is safer if the app runs for months.
# We will do it inside get_yfinance_data.

from concurrent.futures import ThreadPoolExecutor

def get_yfinance_data():
    try:
        live_fo_symbols = get_live_fo_symbols()
        nifty50_symbols = get_nifty50_symbols()
        
        indices_mapping = {
            "^NSEI": "NIFTY 50",
            "^NSEBANK": "BANK NIFTY",
            "^CNXFIN": "FIN NIFTY",
            "^NSEMDCP50": "MIDCAP NIFTY"
        }
        
        # Ensure all Nifty 50 stocks are tracked even if Angel Broking temporarily drops them
        combined_symbols = set(live_fo_symbols).union(nifty50_symbols)
        all_symbols = list(combined_symbols) + list(indices_mapping.keys())
        
        sym_list = []
        for sym in all_symbols:
            if sym in indices_mapping:
                sym_list.append((sym, indices_mapping[sym], True))
            else:
                sym_list.append((sym + ".NS", sym, False))
                
        # Chunk the symbols into groups of 50 to avoid massive Yahoo Finance latency
        chunk_size = 50
        chunks = [sym_list[i:i + chunk_size] for i in range(0, len(sym_list), chunk_size)]
        
        def fetch_chunk(chunk):
            ticker_str = " ".join([item[0] for item in chunk])
            # Download 5 days of daily data to get robust previous_close
            d1 = yf.download(ticker_str, period="5d", interval="1d", group_by="ticker", progress=False, session=yf_session)
            # Download 1 day of 1-minute data to get robust real-time last_price and volume
            d2 = yf.download(ticker_str, period="1d", interval="1m", group_by="ticker", progress=False, session=yf_session)
            return chunk, d1, d2

        final_result = []
        
        chunk_results = []
        for chunk in chunks:
            try:
                res = fetch_chunk(chunk)
                chunk_results.append(res)
            except Exception as e:
                print(f"Error fetching chunk: {e}")
                
        for chunk, d1, d2 in chunk_results:
            for item in chunk:
                yf_sym, display_sym, is_index = item
                
                try:
                    # Handle single ticker vs multiple tickers return format from yfinance
                    df1m = d2[yf_sym] if len(chunk) > 1 else d2
                    df1d = d1[yf_sym] if len(chunk) > 1 else d1
                
                    closes_1m = df1m['Close'].dropna().values
                    vols_1m = df1m['Volume'].dropna().values
                    closes_1d = df1d['Close'].dropna().values
                    
                    if len(closes_1m) == 0 or len(closes_1d) == 0:
                        continue
                        
                    last_price = float(closes_1m[-1])
                    volume = int(sum(vols_1m))
                    
                    # Previous close is the second to last available daily close
                    if len(closes_1d) >= 2:
                        previous_close = float(closes_1d[-2])
                    else:
                        previous_close = float(closes_1d[-1])
                        
                    if previous_close == 0:
                        continue
                        
                    pChange = ((last_price - previous_close) / previous_close) * 100
                    
                    # Give indices a massive volume so they always appear as large blocks if we want
                    if volume < 100:
                        volume = 500000 if is_index else 1000000
                        
                    final_result.append({
                        "symbol": display_sym,
                        "lastPrice": round(last_price, 2),
                        "pChange": round(pChange, 2),
                        "totalTradedVolume": volume,
                        "totalTradedValue": round(last_price * volume, 2),
                        "isNifty50": display_sym in nifty50_symbols
                    })
                except Exception as e:
                    # Skip any malformed or completely empty tickers safely
                    import traceback
                    print(f"Error for {yf_sym}: {e}")
                    traceback.print_exc()

        return {"data": final_result}
    except Exception as e:
        print(f"Error fetching YFinance data: {e}")
        return None

@app.get("/api/data")
def fetch_data():
    data = get_yfinance_data()
    if not data or len(data['data']) == 0:
        raise HTTPException(status_code=500, detail="Failed to fetch data from Yahoo Finance")
    return data

os.makedirs('static', exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
