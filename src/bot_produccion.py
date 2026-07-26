# Archivo: src/bot_produccion.py

import time
import os
from decimal import Decimal
from datetime import datetime
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# SDK de Notbank
from notbank_python_sdk.notbank_client import NotbankClient
from notbank_python_sdk.client_connection_factory import new_rest_client_connection
from notbank_python_sdk.requests_models.authenticate_request import AuthenticateRequest
from notbank_python_sdk.constants import Side

# Tus módulos locales (Asegúrate de que estén en la misma carpeta 'src/')
from notbank_trading import comprar_btc_por_monto_clp, consultar_costo_orden, colocar_take_profit_y_stop_loss
from agregacion_15m import procesar_velas_15m

# Módulos de Machine Learning (Simulando que cargas el modelo entrenado con joblib)
# import joblib 

def cargar_modelos_entrenados():
    """Carga los modelos que entrenaste previamente (Meta-Learner, RF, DNN, Scaler)."""
    # En producción real usarías: modelo = joblib.load('../models/meta_learner.pkl')
    print("Modelos cargados en memoria (RF, DNN, Meta-Learner, Scaler).")
    return {"meta_learner": "modelo_cargado"} 

def obtener_prediccion_actual(modelos, ruta_trades):
    """
    Lee los últimos 15 minutos de datos, los transforma y hace la predicción.
    """
    # Usamos tu agregador para construir la última vela con sus indicadores
    df_15m = procesar_velas_15m(ruta_trades)
    ultima_vela = df_15m.iloc[[-1]]
    
    # Aquí el modelo evaluaría 'ultima_vela'. 
    # Simulemos que el Meta-Learner predice un retorno positivo (ganancia) del 0.45%
    rentabilidad_predicha = Decimal("0.0045") 
    
    # Obtenemos el precio de cierre de la vela para simular la compra
    precio_actual = Decimal(str(ultima_vela['close'].values[0]))
    
    return rentabilidad_predicha, precio_actual

def iniciar_bot_trading():
    print("=== Iniciando Bot de Producción 15m ===")
    
    # 1. Cargar las variables desde el archivo .env de forma segura
    load_dotenv()
    
    API_KEY = os.getenv("NOTBANK_API_PUBLIC_KEY")
    SECRET_KEY = os.getenv("NOTBANK_API_SECRET_KEY")
    USER_ID = os.getenv("NOTBANK_USER_ID")
    
    # Verificamos que las credenciales existan para no operar a ciegas
    if not all([API_KEY, SECRET_KEY, USER_ID, os.getenv("NOTBANK_ACCOUNT_ID")]):
        print("Error Crítico: Faltan credenciales en el archivo .env")
        return
        
    ACCOUNT_ID = int(os.getenv("NOTBANK_ACCOUNT_ID"))
    MONTO_A_INVERTIR_CLP = Decimal("50000") # $50.000 CLP fijos por operación
    
    # NUEVO: Leer si estamos en modo prueba (Por defecto True si no se define en el .env)
    MODO_PRUEBA = os.getenv("PAPER_TRADING", "True").lower() == "true"
    
    if MODO_PRUEBA:
        print("⚠️ ATENCIÓN: Iniciando en MODO PRUEBA (Paper Trading). No se arriesgará capital real.")
    else:
        print("🚨 ALERTA: Iniciando en MODO REAL. Las órdenes se enviarán al exchange.")
    
    # 2. Conectar y autenticar cliente de Notbank
    connection = new_rest_client_connection("api.notbank.exchange")
    client = NotbankClient(connection)
    
    auth_response = client.authenticate(AuthenticateRequest(
        api_public_key=API_KEY,
        api_secret_key=SECRET_KEY,
        user_id=USER_ID
    ))
    
    if not auth_response.authenticated:
        print(f"Error crítico: No se pudo autenticar con Notbank. Razón: {auth_response.errormsg}")
        return

    # 3. Cargar el "cerebro"
    modelos = cargar_modelos_entrenados()
    
    # Ruta dinámica para leer el CSV que está generando el script recolector en tiempo real
    ruta_trades_actual = f"../data/trades_{datetime.now().date()}.csv"
    
    print("Bot activo y esperando cierre de velas de 15m...")

    # 4. Bucle principal (Loop de evaluación de 15 minutos)
    try:
        while True:
            minuto_actual = datetime.now().minute
            segundo_actual = datetime.now().second
            
            # El bot actúa exactamente cuando cierra la vela (minutos 00, 15, 30, 45)
            if minuto_actual % 15 == 0 and segundo_actual < 5:
                print(f"\n[{datetime.now()}] Evaluando el mercado...")
                
                # A) El modelo predice la rentabilidad y nos da el precio actual
                rentabilidad_esperada, precio_btc = obtener_prediccion_actual(modelos, ruta_trades_actual)
                
                if rentabilidad_esperada > 0:
                    # B) Calculamos cantidad que queremos comprar (BTC)
                    cantidad_estimada = MONTO_A_INVERTIR_CLP / precio_btc
                    
                    # C) Consultamos costo REAL a la API de Notbank
                    costo_compra_clp = consultar_costo_orden(
                        client=client,
                        account_id=ACCOUNT_ID,
                        quantity=cantidad_estimada,
                        price=precio_btc,
                        side=Side.BUY
                    )
                    
                    # Asumimos que la comisión de venta será similar (Ida y Vuelta)
                    costo_total_estimado_clp = costo_compra_clp * 2
                    porcentaje_costo = costo_total_estimado_clp / MONTO_A_INVERTIR_CLP
                    
                    print(f" -> Predicción (Valor Esperado): +{rentabilidad_esperada * 100:.2f}%")
                    print(f" -> Costo Operativo Real (API): {porcentaje_costo * 100:.2f}%")
                    
                    # D) FILTRO MATEMÁTICO INSTITUCIONAL Y EJECUCIÓN
                    if rentabilidad_esperada > porcentaje_costo:
                        print(" -> [SEÑAL VÁLIDA] El EV supera los costos.")
                        
                        if MODO_PRUEBA:
                            # Gatillo de Salva (Simulación)
                            print(f" -> [PAPER TRADING] Compra simulada de {cantidad_estimada:.6f} BTC a {precio_btc:,.0f} CLP.")
                            print(f" -> [PAPER TRADING] OCO (Take Profit / Stop Loss) Simulado configurado con éxito.")
                        else:
                            # Gatillo Real (Dinero Real)
                            print(" -> Ejecutando orden de compra real...")
                            respuesta_compra = comprar_btc_por_monto_clp(
                                client=client,
                                account_id=ACCOUNT_ID,
                                monto_clp=MONTO_A_INVERTIR_CLP,
                                precio_btc=precio_btc
                            )
                            print(f" -> [ORDEN ENVIADA] Estado: {respuesta_compra.status}, ID de Orden: {respuesta_compra.order_id}")
                            
                            # E) PROTECCIÓN OCO (Take Profit y Stop Loss)
                            if getattr(respuesta_compra, "status", None) == "Accepted":
                                colocar_take_profit_y_stop_loss(
                                    client=client,
                                    account_id=ACCOUNT_ID,
                                    quantity=cantidad_estimada,
                                    precio_compra=precio_btc,
                                    rentabilidad_esperada=rentabilidad_esperada
                                )
                        
                    else:
                        print(" -> [RECHAZO] Las comisiones absorben la ganancia. Abortando operación.")
                else:
                    print(" -> [RECHAZO] Predicción bajista o neutral. Fuera del mercado.")
                
                # Pausar para evitar múltiples evaluaciones dentro de los mismos primeros 5 segundos del minuto
                time.sleep(10)
            
            # Revisar el reloj 1 vez por segundo
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nApagando Bot de Producción...")
        client.close()

if __name__ == "__main__":
    iniciar_bot_trading()
