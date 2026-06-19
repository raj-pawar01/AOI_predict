import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Set seed for reproducibility
np.random.seed(42)

def create_sequences(X, y, lookback=6):
    X_seq, y_seq = [], []
    # We must create sequences within each city to avoid cross-city boundaries
    # But since X and y here are pre-split or combined, we can prepare sequences from the dataframe.
    # To keep it simple and correct, we will write a helper that prepares sequences from the dataframe directly.
    return np.array(X_seq), np.array(y_seq)

def prepare_data_for_all_models(df, scaler, lookback=6):
    # Features & Targets
    pollutant_cols = ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3']
    
    X_scaled = scaler.transform(df[pollutant_cols].values)
    y = df['AQI'].values
    
    X_tabular_list, y_list = [], []
    X_lstm_list = []
    
    # Generate sequences city-wise
    for city in df['City'].unique():
        city_mask = df['City'] == city
        city_indices = np.where(city_mask)[0]
        
        for i in range(lookback, len(city_indices)):
            # indices of the sequence
            seq_idx = city_indices[i - lookback:i]
            # target index
            target_idx = city_indices[i]
            
            X_lstm_list.append(X_scaled[seq_idx])
            X_tabular_list.append(X_scaled[target_idx])
            y_list.append(y[target_idx])
            
    return np.array(X_tabular_list), np.array(X_lstm_list), np.array(y_list)

def build_ann_model():
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    
    model = Sequential([
        Dense(64, activation='relu', input_shape=(6,)),
        Dropout(0.1),
        Dense(32, activation='relu'),
        Dense(16, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
    return model

def build_lstm_model(lookback=6):
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    
    model = Sequential([
        LSTM(50, activation='tanh', input_shape=(lookback, 6), return_sequences=False),
        Dropout(0.1),
        Dense(25, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
    return model

def main():
    print("Starting Machine Learning Training Pipeline...")
    
    # 1. Generate dataset if not present
    raw_data_path = "data/raw/city_hour.csv"
    if not os.path.exists(raw_data_path):
        from ml.data_generator import generate_full_dataset
        generate_full_dataset(raw_data_path)
        
    # 2. Run Preprocessing
    from ml.preprocessing import AQIPreprocessingPipeline
    pipeline = AQIPreprocessingPipeline(raw_data_path)
    
    scaler_path = "models/scaler.joblib"
    X_train_raw, X_test_raw, y_train_raw, y_test_raw, clean_df = pipeline.fit_transform(save_scaler_path=scaler_path)
    
    # 3. Prepare sequences for LSTM & Tabular models matching the sequence indexes
    lookback = 6
    print(f"Preparing sequence data with lookback = {lookback} hours...")
    
    # We split clean_df chronologically per city: 80% train, 20% test
    train_dfs = []
    test_dfs = []
    for city in clean_df['City'].unique():
        city_df = clean_df[clean_df['City'] == city]
        split_idx = int(len(city_df) * 0.8)
        train_dfs.append(city_df.iloc[:split_idx])
        test_dfs.append(city_df.iloc[split_idx:])
        
    train_df = pd.concat(train_dfs, ignore_index=True)
    test_df = pd.concat(test_dfs, ignore_index=True)
    
    X_train_tab, X_train_lstm, y_train = prepare_data_for_all_models(train_df, pipeline.scaler, lookback)
    X_test_tab, X_test_lstm, y_test = prepare_data_for_all_models(test_df, pipeline.scaler, lookback)
    
    print(f"Tabular Train Shape: {X_train_tab.shape}, LSTM Train Shape: {X_train_lstm.shape}")
    print(f"Tabular Test Shape: {X_test_tab.shape}, LSTM Test Shape: {X_test_lstm.shape}")
    
    # 4. Train & Evaluate Models
    metrics = {}
    os.makedirs("models", exist_ok=True)
    
    # 1. Linear Regression
    print("\nTraining Model 1/9: Linear Regression...")
    lr = LinearRegression()
    lr.fit(X_train_tab, y_train)
    joblib.dump(lr, "models/linear_regression.joblib")
    y_pred = lr.predict(X_test_tab)
    metrics["Linear Regression"] = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "MSE": float(mean_squared_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred))
    }
    
    # 2. Polynomial Regression
    print("Training Model 2/9: Polynomial Regression...")
    poly = make_pipeline(PolynomialFeatures(degree=2), LinearRegression())
    poly.fit(X_train_tab, y_train)
    joblib.dump(poly, "models/polynomial_regression.joblib")
    y_pred = poly.predict(X_test_tab)
    metrics["Polynomial Regression"] = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "MSE": float(mean_squared_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred))
    }
    
    # 3. Ridge Regression
    print("Training Model 3/9: Ridge Regression...")
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_tab, y_train)
    joblib.dump(ridge, "models/ridge_regression.joblib")
    y_pred = ridge.predict(X_test_tab)
    metrics["Ridge Regression"] = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "MSE": float(mean_squared_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred))
    }
    
    # 4. Lasso Regression
    print("Training Model 4/9: Lasso Regression...")
    lasso = Lasso(alpha=0.1)
    lasso.fit(X_train_tab, y_train)
    joblib.dump(lasso, "models/lasso_regression.joblib")
    y_pred = lasso.predict(X_test_tab)
    metrics["Lasso Regression"] = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "MSE": float(mean_squared_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred))
    }
    
    # 5. Support Vector Regression (SVR)
    print("Training Model 5/9: Support Vector Regression (SVR)...")
    # Using a subset of training data if too large, to keep it quick on user machine
    svr_train_size = min(15000, len(X_train_tab))
    svr = SVR(kernel='rbf', C=10.0, epsilon=0.1)
    svr.fit(X_train_tab[:svr_train_size], y_train[:svr_train_size])
    joblib.dump(svr, "models/svr.joblib")
    y_pred = svr.predict(X_test_tab)
    metrics["Support Vector Regression"] = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "MSE": float(mean_squared_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred))
    }
    
    # 6. Decision Tree Regression
    print("Training Model 6/9: Decision Tree Regression...")
    dt = DecisionTreeRegressor(max_depth=10, random_state=42)
    dt.fit(X_train_tab, y_train)
    joblib.dump(dt, "models/decision_tree.joblib")
    y_pred = dt.predict(X_test_tab)
    metrics["Decision Tree Regression"] = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "MSE": float(mean_squared_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred))
    }
    
    # 7. Random Forest Regression
    print("Training Model 7/9: Random Forest Regression...")
    # Limit estimators and depth for performance
    rf = RandomForestRegressor(n_estimators=30, max_depth=12, random_state=42, n_jobs=-1)
    rf.fit(X_train_tab, y_train)
    joblib.dump(rf, "models/random_forest.joblib")
    y_pred = rf.predict(X_test_tab)
    metrics["Random Forest Regression"] = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "MSE": float(mean_squared_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred))
    }
    
    # Import TensorFlow for deep learning
    print("\nImporting TensorFlow...")
    import tensorflow as tf
    
    # 8. Artificial Neural Network (ANN)
    print("Training Model 8/9: Artificial Neural Network (ANN)...")
    ann = build_ann_model()
    # Train quickly
    ann.fit(X_train_tab, y_train, epochs=15, batch_size=2048, validation_split=0.1, verbose=1)
    ann.save("models/ann.keras")
    y_pred = ann.predict(X_test_tab).flatten()
    metrics["Artificial Neural Network"] = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "MSE": float(mean_squared_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred))
    }
    
    # 9. LSTM Network
    print("Training Model 9/9: LSTM Network...")
    lstm = build_lstm_model(lookback)
    # Train quickly
    lstm.fit(X_train_lstm, y_train, epochs=10, batch_size=2048, validation_split=0.1, verbose=1)
    lstm.save("models/lstm.keras")
    y_pred = lstm.predict(X_test_lstm).flatten()
    metrics["LSTM Network"] = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "MSE": float(mean_squared_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred))
    }
    
    # 5. Train LSTM Forecasting Model
    from ml.forecaster import train_forecaster
    train_forecaster(clean_df)
    
    # 6. Save Preprocessing Summary and Model Metrics
    summary_data = {
        "preprocessing_summary": pipeline.summary,
        "metrics": metrics
    }
    
    with open("models/metrics.json", "w") as f:
        json.dump(summary_data, f, indent=4)
        
    print("\nTraining Pipeline Completed Successfully!")
    print("Saved all models and metrics to models/ directory.")

if __name__ == '__main__':
    main()
