import os
import json
import subprocess
import threading
import numpy as np
import pandas as pd
from flask import Flask, render_template, jsonify, request
import joblib

app = Flask(__name__)

# Constants
CITIES = ['Delhi', 'Mumbai', 'Bengaluru', 'Chennai', 'Kolkata', 'Hyderabad']
POLLUTANTS = ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3']

# Global thread reference for retraining
training_thread = None
training_process = None

def get_health_recommendations(category):
    recommendations = {
        "Good": {
            "text": "Air quality is satisfactory. Outdoor activities are safe for everyone.",
            "alert_class": "success",
            "icon": "bi-emoji-smile-fill"
        },
        "Satisfactory": {
            "text": "Air quality is acceptable. Only minor health concerns for extremely sensitive people.",
            "alert_class": "info",
            "icon": "bi-emoji-neutral-fill"
        },
        "Moderate": {
            "text": "May cause breathing discomfort for people with lung disease, asthma, or heart conditions. Children and elderly should limit prolonged outdoor exertion.",
            "alert_class": "warning",
            "icon": "bi-emoji-frown-fill"
        },
        "Poor": {
            "text": "May cause breathing discomfort to most people on prolonged exposure. People with heart or lung disease should avoid outdoor activity.",
            "alert_class": "warning",
            "icon": "bi-exclamation-triangle-fill"
        },
        "Very Poor": {
            "text": "May cause respiratory illness on prolonged exposure. Elderly, children, and people with respiratory conditions should remain indoors.",
            "alert_class": "danger",
            "icon": "bi-exclamation-octagon-fill"
        },
        "Severe": {
            "text": "Extremely hazardous. May cause serious respiratory impacts even in healthy individuals. Everyone should stay indoors, run air purifiers, and wear N95 masks if going out.",
            "alert_class": "danger",
            "icon": "bi-shield-fill-x"
        },
        "Unknown": {
            "text": "Data unavailable to calculate recommendations.",
            "alert_class": "secondary",
            "icon": "bi-question-circle-fill"
        }
    }
    return recommendations.get(category, recommendations["Unknown"])

def run_train_process():
    global training_process
    os.makedirs("models", exist_ok=True)
    log_file_path = "models/train.log"
    
    with open(log_file_path, "w") as log_file:
        log_file.write("Starting model training pipeline...\n")
        log_file.flush()
        
        # Determine the python executable path
        python_bin = os.path.join(".venv", "Scripts", "python.exe")
        if not os.path.exists(python_bin):
            # Fallback for unix-like venv structure if someone deploys there
            python_bin = os.path.join(".venv", "bin", "python")
            if not os.path.exists(python_bin):
                python_bin = "python" # fallback
            
        try:
            training_process = subprocess.Popen(
                [python_bin, "-m", "ml.train"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in training_process.stdout:
                log_file.write(line)
                log_file.flush()
                
            training_process.wait()
            if training_process.returncode == 0:
                log_file.write("\nSUCCESS: All models trained and saved successfully.\n")
            else:
                log_file.write(f"\nERROR: Training process exited with code {training_process.returncode}\n")
        except Exception as e:
            log_file.write(f"\nEXCEPTION: {str(e)}\n")
        finally:
            log_file.flush()

# Page Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/comparison')
def comparison():
    return render_template('comparison.html')

@app.route('/predict')
def predict_page():
    return render_template('predict.html')

@app.route('/forecast')
def forecast_page():
    return render_template('forecast.html')

@app.route('/city-comparison')
def city_comparison_page():
    return render_template('city_comparison.html')

# API Endpoints
@app.route('/api/metrics')
def api_metrics():
    metrics_path = "models/metrics.json"
    if not os.path.exists(metrics_path):
        return jsonify({"status": "not_trained", "message": "Models are not trained yet."})
    
    with open(metrics_path, "r") as f:
        data = json.load(f)
    return jsonify({"status": "ready", "data": data})

@app.route('/api/eda')
def api_eda():
    clean_data_path = "data/processed/city_hour_clean.csv"
    if not os.path.exists(clean_data_path):
        return jsonify({"status": "error", "message": "Preprocessed data not ready. Train models first."}), 400
        
    try:
        df = pd.read_csv(clean_data_path)
        
        # 1. AQI Distribution (Categories)
        aqi_dist = df['AQI_Category'].value_counts().to_dict()
        
        # 2. Pollutant Average Concentrations
        pollutants = ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3']
        pollutant_avgs = df[pollutants].mean().to_dict()
        
        # 3. Monthly Trends of PM2.5 & PM10 (using Delhi as representative)
        delhi_df = df[df['City'] == 'Delhi'].copy()
        delhi_df['ParsedDate'] = pd.to_datetime(delhi_df['Timestamp'])
        # Group by Month-Year for trends
        delhi_df['Month'] = delhi_df['ParsedDate'].dt.strftime('%b %Y')
        # Sort values first to maintain timeline order
        delhi_df = delhi_df.sort_values(by='ParsedDate')
        monthly_trends = delhi_df.groupby('Month', sort=False)[['PM2.5', 'PM10', 'AQI']].mean().tail(12)
        
        trends_data = {
            "months": list(monthly_trends.index),
            "pm25": [round(x, 1) for x in monthly_trends['PM2.5']],
            "pm10": [round(x, 1) for x in monthly_trends['PM10']],
            "aqi": [round(x, 1) for x in monthly_trends['AQI']]
        }
        
        # 4. Correlation with AQI
        corr_with_aqi = df[pollutants + ['AQI']].corr()['AQI'].drop('AQI').to_dict()
        
        # Full correlation matrix for heatmap
        corr_matrix = df[pollutants].corr().values.tolist()
        
        # 5. AQI Time Series (Delhi last 120 hours)
        time_series_df = delhi_df.tail(120)
        ts_data = {
            "timestamps": time_series_df['Timestamp'].tolist(),
            "aqi": time_series_df['AQI'].tolist(),
            "pm25": time_series_df['PM2.5'].tolist()
        }
        
        # 6. Feature Importance (from trained Random Forest)
        importance_vals = [0.45, 0.35, 0.08, 0.03, 0.06, 0.03]
        rf_path = "models/random_forest.joblib"
        if os.path.exists(rf_path):
            try:
                rf = joblib.load(rf_path)
                importance_vals = list(rf.feature_importances_)
            except:
                pass
                
        feature_importance = {pollutants[i]: float(importance_vals[i]) for i in range(len(pollutants))}
        
        return jsonify({
            "status": "success",
            "aqi_distribution": aqi_dist,
            "pollutant_averages": pollutant_avgs,
            "trends": trends_data,
            "correlations": corr_with_aqi,
            "correlation_matrix": {
                "columns": pollutants,
                "matrix": corr_matrix
            },
            "time_series": ts_data,
            "feature_importance": feature_importance
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"EDA data calculation error: {str(e)}"}), 500

@app.route('/api/train', methods=['POST'])
def api_train():
    global training_thread, training_process
    
    # Check if already running
    if training_process and training_process.poll() is None:
        return jsonify({"status": "running", "message": "Training is already in progress."})
        
    # Start background training thread
    training_thread = threading.Thread(target=run_train_process)
    training_thread.daemon = True
    training_thread.start()
    
    return jsonify({"status": "started", "message": "Training pipeline started in background."})

@app.route('/api/train-status')
def api_train_status():
    global training_process
    
    status = "idle"
    if training_process and training_process.poll() is None:
        status = "training"
        
    logs = ""
    log_file_path = "models/train.log"
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r") as f:
                logs = f.read()
        except Exception as e:
            logs = f"Error reading log: {str(e)}"
            
    return jsonify({"status": status, "logs": logs})

@app.route('/api/predict', methods=['POST'])
def api_predict():
    data = request.get_json() or {}
    model_name = data.get('model', 'Random Forest Regression')
    
    # Extract inputs and parse to floats
    try:
        inputs = {
            'PM2.5': float(data.get('pm25', 50)),
            'PM10': float(data.get('pm10', 100)),
            'NO2': float(data.get('no2', 40)),
            'SO2': float(data.get('so2', 20)),
            'CO': float(data.get('co', 1.0)),
            'O3': float(data.get('o3', 50))
        }
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid input values. Please provide numbers."}), 400
        
    # Check if model files exist
    scaler_path = "models/scaler.joblib"
    if not os.path.exists(scaler_path):
        return jsonify({"status": "error", "message": "Models have not been trained yet. Please train them first."}), 400
        
    try:
        # Load scaler
        scaler = joblib.load(scaler_path)
        
        # Prepare inputs vector [PM2.5, PM10, NO2, SO2, CO, O3]
        input_vec = [inputs['PM2.5'], inputs['PM10'], inputs['NO2'], inputs['SO2'], inputs['CO'], inputs['O3']]
        scaled_vec = scaler.transform([input_vec])
        
        # Model predictions
        predicted_aqi = 0.0
        
        # Import TensorFlow only if deep learning model is chosen
        if model_name == "Artificial Neural Network":
            import tensorflow as tf
            model = tf.keras.models.load_model("models/ann.keras")
            predicted_aqi = float(model.predict(scaled_vec, verbose=0)[0][0])
        elif model_name == "LSTM Network":
            import tensorflow as tf
            model = tf.keras.models.load_model("models/lstm.keras")
            # LSTM expects sequence shape (batch_size, sequence_length, features)
            # We pad input by replicating it to match sequence length of 6
            seq_vec = np.repeat(scaled_vec, 6, axis=0).reshape(1, 6, 6)
            predicted_aqi = float(model.predict(seq_vec, verbose=0)[0][0])
        else:
            # Scikit-learn models
            model_file_map = {
                "Linear Regression": "linear_regression.joblib",
                "Polynomial Regression": "polynomial_regression.joblib",
                "Ridge Regression": "ridge_regression.joblib",
                "Lasso Regression": "lasso_regression.joblib",
                "Support Vector Regression": "svr.joblib",
                "Decision Tree Regression": "decision_tree.joblib",
                "Random Forest Regression": "random_forest.joblib"
            }
            
            m_file = model_file_map.get(model_name, "random_forest.joblib")
            model = joblib.load(f"models/{m_file}")
            predicted_aqi = float(model.predict(scaled_vec)[0])
            
        predicted_aqi = max(0.0, round(predicted_aqi, 1))
        
        # Determine category and health recommendations
        from ml.data_generator import get_aqi_category
        category = get_aqi_category(predicted_aqi)
        rec = get_health_recommendations(category)
        
        # Calculate Confidence Level
        # Load R2 of model as a baseline
        with open("models/metrics.json", "r") as f:
            metrics_data = json.load(f)
        r2 = metrics_data["metrics"].get(model_name, {}).get("R2", 0.85)
        
        # Distance penalty: how far inputs are from standard standard deviation
        # If values are extreme, confidence goes down slightly
        z_scores = np.abs(scaled_vec[0])
        max_z = np.max(z_scores)
        penalty = max(0.0, (max_z - 1.5) * 5) # Penalty of 5% per standard dev past 1.5
        
        confidence = round(max(45, min(99, r2 * 100 - penalty)), 1)
        
        return jsonify({
            "status": "success",
            "model": model_name,
            "aqi": predicted_aqi,
            "category": category,
            "confidence": confidence,
            "recommendation": rec["text"],
            "alert_class": rec["alert_class"],
            "icon": rec["icon"]
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Prediction error: {str(e)}"}), 500

@app.route('/api/forecast-data')
def api_forecast_data():
    city = request.args.get('city', 'Delhi')
    if city not in CITIES:
        return jsonify({"status": "error", "message": "Invalid city name."}), 400
        
    clean_data_path = "data/processed/city_hour_clean.csv"
    if not os.path.exists(clean_data_path):
        return jsonify({"status": "error", "message": "Preprocessed dataset is missing. Please train the models first."}), 400
        
    try:
        df = pd.read_csv(clean_data_path)
        
        # Call the forecaster
        from ml.forecaster import forecast_next_hours
        forecast_vals = forecast_next_hours(city, df, steps=24)
        
        if forecast_vals is None:
            return jsonify({"status": "error", "message": "Forecasting model or scaler not found. Please train models first."}), 400
            
        # Get historical data for the last 24 hours of that city
        city_df = df[df['City'] == city].sort_values(by='Timestamp').tail(24)
        history_aqi = city_df['AQI'].tolist()
        history_time = city_df['Timestamp'].tolist()
        
        # Build forecast timestamps (hourly)
        last_time = pd.to_datetime(history_time[-1])
        forecast_time = [(last_time + pd.Timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(1, 25)]
        
        return jsonify({
            "status": "success",
            "city": city,
            "history": {
                "timestamps": history_time,
                "values": history_aqi
            },
            "forecast": {
                "timestamps": forecast_time,
                "values": forecast_vals,
                "h6": forecast_vals[:6],
                "h12": forecast_vals[:12],
                "h24": forecast_vals[:24]
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Forecasting error: {str(e)}"}), 500

@app.route('/api/city-data')
def api_city_data():
    clean_data_path = "data/processed/city_hour_clean.csv"
    if not os.path.exists(clean_data_path):
        # Fallback to loading raw if cleaned isn't ready, otherwise error
        if os.path.exists("data/raw/city_hour.csv"):
            clean_data_path = "data/raw/city_hour.csv"
        else:
            return jsonify({"status": "error", "message": "No data available. Train models to generate data."}), 400
            
    try:
        df = pd.read_csv(clean_data_path)
        city_summaries = {}
        
        for city in CITIES:
            city_df = df[df['City'] == city].sort_values(by='Timestamp')
            last_record = city_df.iloc[-1]
            
            # Historical trends (last 7 days of daily averages)
            # Grouping by date
            city_df['Date'] = pd.to_datetime(city_df['Timestamp']).dt.date
            daily_df = city_df.groupby('Date')[['AQI', 'PM2.5', 'PM10']].mean().tail(7)
            
            city_summaries[city] = {
                "current": {
                    "aqi": int(last_record['AQI']),
                    "category": last_record['AQI_Category'],
                    "pm25": float(last_record['PM2.5']),
                    "pm10": float(last_record['PM10']),
                    "no2": float(last_record['NO2']),
                    "so2": float(last_record['SO2']),
                    "co": float(last_record['CO']),
                    "o3": float(last_record['O3']),
                    "time": last_record['Timestamp']
                },
                "historical": {
                    "dates": [str(d) for d in daily_df.index],
                    "aqi": [round(a, 1) for a in daily_df['AQI']],
                    "pm25": [round(p, 1) for p in daily_df['PM2.5']],
                    "pm10": [round(p, 1) for p in daily_df['PM10']]
                }
            }
            
        return jsonify({
            "status": "success",
            "cities": city_summaries
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"City data loading error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
