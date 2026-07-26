# Archivo: src/recolector_notbank.py

import time
import csv
import os
from datetime import datetime
from notbank_python_sdk.notbank_client import NotbankClient
from notbank_python_sdk.client_connection_factory import new_restarting_websocket_client_connection
from notbank_python_sdk.requests_models import SubscribeTradesRequest, SubscribeLevel2Request

class CsvRotativo:
    def __init__(self, prefijo_nombre, encabezados):
        self.prefijo = prefijo_nombre
        self.encabezados = encabezados
        self.fecha_actual = datetime.now().date()
        self.archivo_actual = None
        self.writer = None
        
        if not os.path.exists('../data'):
            os.makedirs('../data')
            
        self._abrir_archivo()

    def _abrir_archivo(self):
        nombre_archivo = f"../data/{self.prefijo}_{self.fecha_actual}.csv"
        archivo_existe = os.path.isfile(nombre_archivo)
        
        self.archivo_actual = open(nombre_archivo, mode='a', newline='', encoding='utf-8')
        self.writer = csv.writer(self.archivo_actual)
        
        if not archivo_existe:
            self.writer.writerow(self.encabezados)

    def guardar_fila(self, fila):
        fecha_hoy = datetime.now().date()
        if fecha_hoy != self.fecha_actual:
            self.archivo_actual.close()
            self.fecha_actual = fecha_hoy
            self._abrir_archivo()
            
        self.writer.writerow(fila)
        self.archivo_actual.flush()

trades_csv = CsvRotativo("trades", ["timestamp_local", "trade_id", "precio", "cantidad", "direccion", "taker_side"])
level2_csv = CsvRotativo("level2", ["timestamp_local", "md_update_id", "lado", "precio", "cantidad"])

def manejar_snapshot_trades(trades):
    pass

def manejar_update_trades(trades):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    for t in trades:
        trades_csv.guardar_fila([ahora, t.trade_id, t.price, t.quantity, t.direction, t.taker_side])

def manejar_snapshot_level2(level2_feeds):
    pass

def manejar_update_level2(level2_feeds):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    for f in level2_feeds:
        level2_csv.guardar_fila([ahora, f.market_data_update_id, f.side, f.price, f.quantity])

def iniciar_recolector():
    connection = new_restarting_websocket_client_connection("api.notbank.exchange")
    client = NotbankClient(connection)
    connection.connect()
    
    instrumento = 1 
    
    print("Suscripciones activas. Guardando datos en /data... (Ctrl+C para detener)")
    
    client.subscribe_trades(
        request=SubscribeTradesRequest(instrument_id=instrumento, include_last_count=0),
        snapshot_handler=manejar_snapshot_trades,
        update_handler=manejar_update_trades
    )
    
    client.subscribe_level_2(
        request=SubscribeLevel2Request(instrument_id=instrumento, depth=20),
        snapshot_handler=manejar_snapshot_level2,
        update_handler=manejar_update_level2
    )
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo recolector y cerrando archivos...")
        client.close()

if __name__ == "__main__":
    iniciar_recolector()
