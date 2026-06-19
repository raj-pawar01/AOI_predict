import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import joblib

def build_forecaster_model(lookback=24):
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    
    model = Sequential([
        LSTM(64, activation='tanh', input_shape=(lookback, 1), return_sequences=True),
        Dropout(0.1),
        LSTM(32, activation='tanh', return_sequences=False),
        Dropout(0.1),
        Dense(16, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
    return model

def train_forecaster(df, lookback=24):
    print("\nTraining LSTM Forecasting Model...")
    
    # 1. Scale AQI values
    scaler = MinMaxScaler(feature_range=(0, 1))
    
    # We will train city by city and combine sequences
    X_list, y_list = [], []
    
    for city in df['City'].unique():
        city_df = df[df['City'] == city].sort_values(by='Timestamp')
        aqi_vals = city_df['AQI'].values.reshape(-1, 1)
        
        # Fit scaler on each city's data or overall. Overall is better for consistency.
        # So let's fit scaler on the whole dataset's AQI values first
    
    aqi_all = df['AQI'].values.reshape(-1, 1)
    scaler.fit(aqi_all)
    
    for city in df['City'].unique():
        city_df = df[df['City'] == city].sort_values(by='Timestamp')
        aqi_scaled = scaler.transform(city_df['AQI'].values.reshape(-1, 1))
        
        for i in range(lookback, len(aqi_scaled)):
            X_list.append(aqi_scaled[i-lookback:i])
            y_list.append(aqi_scaled[i])
            
    X = np.array(X_list)
    y = np.array(y_list)
    
    print(f"Forecasting sequences shape: X={X.shape}, y={y.shape}")
    
    # Train test split (chronological)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    model = build_forecaster_model(lookback)
    
    # Train the forecaster
    import tensorflow as tf
    model.fit(X_train, y_train, epochs=8, batch_size=2048, validation_split=0.1, verbose=1)
    
    # Save the model and scaler
    os.makedirs("models", exist_ok=True)
    model.save("models/forecast_lstm.keras")
    joblib.dump(scaler, "models/forecast_scaler.joblib")
    
    print("LSTM Forecasting Model trained and saved successfully.")

def forecast_next_hours(city_name, df, steps=24, lookback=24):
    # Load model and scaler
    import tensorflow as tf
    if not os.path.exists("models/forecast_lstm.keras"):
        return None
        
    model = tf.keras.models.load_model("models/forecast_lstm.keras")
    scaler = joblib.load("models/forecast_scaler.joblib")
    
    # Get the last lookback hours for the specified city
    city_df = df[df['City'] == city_name].sort_values(by='Timestamp')
    if len(city_df) < lookback:
        return None
        
    last_aqis = city_df['AQI'].values[-lookback:].reshape(-1, 1)
    
    # Scale input
    scaled_seq = scaler.transform(last_aqis)
    
    predictions = []
    current_seq = scaled_seq.copy()
    
    for _ in range(steps):
        # Predict t+1
        # Input shape: (1, lookback, 1)
        pred_scaled = model.predict(current_seq.reshape(1, lookback, 1), verbose=0)[0][0]
        predictions.append(pred_scaled)
        
        # Shift sequence
        current_seq = np.vstack([current_seq[1:], [[pred_scaled]]])
        
    # Inverse scale predictions
    predictions = np.array(predictions).reshape(-1, 1)
    predictions_original = scaler.inverse_transform(predictions).flatten()
    
    # Convert predictions to integers
    predictions_original = [int(round(max(0, x))) for x in predictions_original]
    return predictions_original
