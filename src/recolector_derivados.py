# Archivo: src/recolector_derivados.py

import time
import requests
from datetime import datetime
from recolector_notbank import CsvRotativo 

def recolectar_derivados_globales():
    derivados_csv = CsvRotativo("derivados_globales", ["timestamp_local", "open_interest", "funding_rate"])
    print("Iniciando recolección de derivados globales (Open Interest y Funding Rate)...")
    
    oi_url = "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"
    funding_url = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
    
    try:
        while True:
            ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            
            oi_response = requests.get(oi_url).json()
            open_interest = oi_response.get("openInterest", 0)
            
            funding_response = requests.get(funding_url).json()
            funding_rate = funding_response.get("lastFundingRate", 0)
            
            derivados_csv.guardar_fila([ahora, open_interest, funding_rate])
            time.sleep(60) 
            
    except KeyboardInterrupt:
        print("\nDeteniendo recolector de derivados...")

if __name__ == "__main__":
    recolectar_derivados_globales()
