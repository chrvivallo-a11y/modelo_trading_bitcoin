# Archivo: src/modelo_ensamblado.py

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Dropout

def preparar_datos(ruta_csv):
    """Carga los datos, crea los targets (desplazados al futuro) y escala las variables."""
    df = pd.read_csv(ruta_csv, index_col='timestamp_local', parse_dates=True)
    
    # 1. Crear Targets (El futuro: t+1)
    # pct_change() saca el % de cambio. shift(-1) mueve el valor de la PRÓXIMA vela a la actual.
    df['retorno_futuro'] = df['close'].pct_change().shift(-1)
    
    # Target 1: Dirección (1 si sube, 0 si baja)
    df['target_direccion'] = np.where(df['retorno_futuro'] > 0, 1, 0)
    
    # Target 2: Amplitud (Valor absoluto del movimiento)
    df['target_amplitud'] = df['retorno_futuro'].abs()
    
    # Eliminar la última fila que quedará con NaN por culpa del shift(-1)
    df.dropna(inplace=True)
    
    # 2. Definir Features (Variables de entrada)
    features = [
        'volumen', 'order_flow_delta', 'rsi_14', 
        'distancia_sma20_%', 'volatilidad_10'
    ]
    # Si logramos descargar derivados globales, los añadimos aquí:
    if 'open_interest' in df.columns:
        features.extend(['open_interest', 'funding_rate'])
        
    X = df[features]
    y_dir = df['target_direccion']
    y_amp = df['target_amplitud']
    
    # 3. Dividir en Entrenamiento (80%) y Prueba (20%) SIN mezclar temporalmente
    X_train, X_test, y_dir_train, y_dir_test, y_amp_train, y_amp_test = train_test_split(
        X, y_dir, y_amp, test_size=0.2, shuffle=False
    )
    
    # 4. Escalar los datos (Crucial para la Red Neuronal)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    return X_train_scaled, X_test_scaled, y_dir_train, y_dir_test, y_amp_train, y_amp_test, scaler

def entrenar_random_forest(X_train, y_dir_train, y_amp_train):
    """Entrena dos bosques: uno para dirección y otro para amplitud."""
    print("Entrenando Random Forest (Dirección y Amplitud)...")
    
    rf_clasificador = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf_clasificador.fit(X_train, y_dir_train)
    
    rf_regresor = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
    rf_regresor.fit(X_train, y_amp_train)
    
    return rf_clasificador, rf_regresor

def construir_dnn(input_dim):
    """Construye una Red Neuronal con Aprendizaje Multitarea (2 cabezas)."""
    # Tronco compartido
    entradas = Input(shape=(input_dim,))
    x = Dense(64, activation='relu')(entradas)
    x = Dropout(0.2)(x)
    x = Dense(32, activation='relu')(x)
    
    # Cabeza 1: Dirección (Clasificación binaria -> Sigmoid)
    salida_dir = Dense(1, activation='sigmoid', name='salida_direccion')(x)
    
    # Cabeza 2: Amplitud (Regresión -> Lineal)
    salida_amp = Dense(1, activation='linear', name='salida_amplitud')(x)
    
    modelo = Model(inputs=entradas, outputs=[salida_dir, salida_amp])
    
    # Compilamos con dos funciones de pérdida distintas
    modelo.compile(
        optimizer='adam',
        loss={'salida_direccion': 'binary_crossentropy', 'salida_amplitud': 'mse'},
        loss_weights={'salida_direccion': 1.0, 'salida_amplitud': 100.0} # Damos más peso a la amplitud por su escala pequeña
    )
    return modelo

def entrenar_meta_learner(preds_rf_dir, preds_rf_amp, preds_dnn_dir, preds_dnn_amp, y_target):
    """El Meta-Learner decide a qué modelo creerle para calcular la rentabilidad real."""
    print("Entrenando Meta-Learner (Stacking)...")
    # Apilamos las 4 predicciones como si fueran las nuevas "features"
    X_meta = np.column_stack((preds_rf_dir, preds_rf_amp, preds_dnn_dir, preds_dnn_amp))
    
    # Usamos una Regresión Ridge (lineal y penalizada) para evitar sobreajuste
    meta_modelo = Ridge(alpha=1.0)
    meta_modelo.fit(X_meta, y_target)
    
    return meta_modelo

if __name__ == "__main__":
    print("=== Iniciando Entrenamiento del Sistema Cuantitativo ===")
    
    # 1. Cargar y preparar datos
    # Asumimos que tienes el archivo generado por agregacion_15m.py
    # Para probar el código, asegúrate de tener "dataset_ml_15m.csv" en la carpeta data
    try:
        X_train, X_test, y_dir_train, y_dir_test, y_amp_train, y_amp_test, scaler = preparar_datos("../data/dataset_ml_15m.csv")
    except FileNotFoundError:
        print("Error: No se encontró el dataset. Debes ejecutar primero la recolección y agregación.")
        exit()
        
    # 2. Entrenar Capa Base 1: Random Forest
    rf_clf, rf_reg = entrenar_random_forest(X_train, y_dir_train, y_amp_train)
    
    # 3. Entrenar Capa Base 2: Red Neuronal (DNN)
    print("Entrenando Red Neuronal Profunda...")
    dnn = construir_dnn(input_dim=X_train.shape[1])
    dnn.fit(
        X_train, 
        {'salida_direccion': y_dir_train, 'salida_amplitud': y_amp_train},
        epochs=20, batch_size=32, verbose=0
    )
    
    # 4. Generar predicciones de la Capa Base para entrenar la Capa Meta
    # Obtenemos lo que opinan el RF y la DNN sobre el conjunto de prueba (Test)
    rf_preds_dir = rf_clf.predict_proba(X_test)[:, 1] # Probabilidad de que suba
    rf_preds_amp = rf_reg.predict(X_test)
    
    dnn_preds = dnn.predict(X_test, verbose=0)
    dnn_preds_dir = dnn_preds[0].flatten()
    dnn_preds_amp = dnn_preds[1].flatten()
    
    # 5. Entrenar la Capa Meta
    # El objetivo final del Meta-Learner es predecir el retorno REAL direccional (retorno_futuro original)
    # Reconstruimos el retorno original del test para que el Meta-Learner aprenda el Valor Esperado (EV)
    y_real_test = np.where(y_dir_test == 1, y_amp_test, -y_amp_test)
    
    meta_learner = entrenar_meta_learner(
        rf_preds_dir, rf_preds_amp, 
        dnn_preds_dir, dnn_preds_amp, 
        y_real_test
    )
    
    print("=== Entrenamiento Finalizado ===")
    print("Coeficientes del Meta-Learner (Importancia que le dio a cada modelo):")
    print(f" - RF Dirección: {meta_learner.coef_[0]:.4f}")
    print(f" - RF Amplitud:  {meta_learner.coef_[1]:.4f}")
    print(f" - DNN Dirección: {meta_learner.coef_[2]:.4f}")
    print(f" - DNN Amplitud:  {meta_learner.coef_[3]:.4f}")
