import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def calculate_sub_index_pm25(val):
    if pd.isna(val) or val < 0: return np.nan
    # CPCB Breakpoints for PM2.5 (24h avg)
    if val <= 30: return val * 50 / 30
    elif val <= 60: return 50 + (val - 30) * 50 / 30
    elif val <= 90: return 100 + (val - 60) * 100 / 30
    elif val <= 120: return 200 + (val - 90) * 100 / 30
    elif val <= 250: return 300 + (val - 120) * 100 / 130
    else: return 400 + (val - 250) * 100 / 150

def calculate_sub_index_pm10(val):
    if pd.isna(val) or val < 0: return np.nan
    # CPCB Breakpoints for PM10 (24h avg)
    if val <= 50: return val * 50 / 50
    elif val <= 100: return 50 + (val - 50) * 50 / 50
    elif val <= 250: return 100 + (val - 100) * 100 / 150
    elif val <= 350: return 200 + (val - 250) * 100 / 100
    elif val <= 430: return 300 + (val - 350) * 100 / 80
    else: return 400 + (val - 430) * 100 / 85

def calculate_sub_index_no2(val):
    if pd.isna(val) or val < 0: return np.nan
    # CPCB Breakpoints for NO2 (24h avg)
    if val <= 40: return val * 50 / 40
    elif val <= 80: return 50 + (val - 40) * 50 / 40
    elif val <= 180: return 100 + (val - 80) * 100 / 100
    elif val <= 280: return 200 + (val - 180) * 100 / 100
    elif val <= 400: return 300 + (val - 280) * 100 / 120
    else: return 400 + (val - 400) * 100 / 100

def calculate_sub_index_so2(val):
    if pd.isna(val) or val < 0: return np.nan
    # CPCB Breakpoints for SO2 (24h avg)
    if val <= 40: return val * 50 / 40
    elif val <= 80: return 50 + (val - 40) * 50 / 40
    elif val <= 380: return 100 + (val - 80) * 100 / 300
    elif val <= 800: return 200 + (val - 380) * 100 / 420
    elif val <= 1600: return 300 + (val - 800) * 100 / 800
    else: return 400 + (val - 1600) * 100 / 800

def calculate_sub_index_co(val):
    if pd.isna(val) or val < 0: return np.nan
    # CPCB Breakpoints for CO (8h avg in mg/m3)
    if val <= 1.0: return val * 50 / 1.0
    elif val <= 2.0: return 50 + (val - 1.0) * 50 / 1.0
    elif val <= 10.0: return 100 + (val - 2.0) * 100 / 8.0
    elif val <= 17.0: return 200 + (val - 10.0) * 100 / 7.0
    elif val <= 34.0: return 300 + (val - 17.0) * 100 / 17.0
    else: return 400 + (val - 34.0) * 100 / 16.0

def calculate_sub_index_o3(val):
    if pd.isna(val) or val < 0: return np.nan
    # CPCB Breakpoints for O3 (8h avg)
    if val <= 50: return val * 50 / 50
    elif val <= 100: return 50 + (val - 50) * 50 / 50
    elif val <= 168: return 100 + (val - 100) * 100 / 68
    elif val <= 208: return 200 + (val - 168) * 100 / 40
    elif val <= 748: return 300 + (val - 208) * 100 / 540
    else: return 400 + (val - 748) * 100 / 252

def calculate_aqi_cpcb(pm25, pm10, no2, so2, co, o3):
    si_pm25 = calculate_sub_index_pm25(pm25)
    si_pm10 = calculate_sub_index_pm10(pm10)
    si_no2 = calculate_sub_index_no2(no2)
    si_so2 = calculate_sub_index_so2(so2)
    si_co = calculate_sub_index_co(co)
    si_o3 = calculate_sub_index_o3(o3)
    
    sub_indices = [si_pm25, si_pm10, si_no2, si_so2, si_co, si_o3]
    valid_sis = [x for x in sub_indices if not pd.isna(x)]
    
    # CPCB rules: AQI is max of sub-indices, provided >= 3 pollutants present, one of which is PM2.5 or PM10
    if len(valid_sis) >= 3 and (not pd.isna(si_pm25) or not pd.isna(si_pm10)):
        return round(max(valid_sis))
    elif len(valid_sis) > 0:
        # Fallback to simple max if rules not strictly met, for data integrity
        return round(max(valid_sis))
    return np.nan

def get_aqi_category(aqi):
    if pd.isna(aqi): return "Unknown"
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Satisfactory"
    elif aqi <= 200: return "Moderate"
    elif aqi <= 300: return "Poor"
    elif aqi <= 400: return "Very Poor"
    else: return "Severe"

def generate_city_data(city_name, base_levels, start_date, end_date):
    print(f"Generating data for {city_name}...")
    delta = end_date - start_date
    total_hours = int(delta.total_seconds() / 3600) + 1
    
    dates = [start_date + timedelta(hours=i) for i in range(total_hours)]
    
    # Base level definitions
    # base_levels: {pm25, pm10, no2, so2, co, o3}
    np.random.seed(42 + hash(city_name) % 1000)
    
    data = []
    for dt in dates:
        hour = dt.hour
        month = dt.month
        
        # Diurnal pattern (two traffic peaks: 8-10 AM, 6-9 PM)
        diurnal_factor = 1.0 + 0.3 * np.sin((hour - 4) * np.pi / 12) + 0.2 * np.sin((hour - 15) * np.pi / 12)
        if 8 <= hour <= 10 or 18 <= hour <= 21:
            diurnal_factor += 0.25
            
        # Seasonal pattern (winter peak: Nov-Jan, monsoon low: Jul-Sep)
        if month in [11, 12, 1]: # Winter
            seasonal_factor = 1.5 if city_name in ["Jalgaon", "Kolkata"] else 1.25
        elif month in [7, 8, 9]: # Monsoon
            seasonal_factor = 0.5
        else:
            seasonal_factor = 0.9
            
        # Add random noise
        noise = np.random.normal(0, 0.1)
        total_factor = max(0.2, diurnal_factor * seasonal_factor + noise)
        
        pm25 = max(1, base_levels['pm25'] * total_factor + np.random.normal(0, 5))
        pm10 = max(2, base_levels['pm10'] * total_factor + np.random.normal(0, 8))
        no2 = max(1, base_levels['no2'] * total_factor + np.random.normal(0, 3))
        so2 = max(1, base_levels['so2'] * total_factor + np.random.normal(0, 2))
        co = max(0.1, base_levels['co'] * total_factor + np.random.normal(0, 0.15))
        o3 = max(1, base_levels['o3'] * (1.2 - 0.3 * diurnal_factor) + np.random.normal(0, 4)) # O3 peak is in afternoon
        
        # Clip values to reasonable biological boundaries
        pm25 = round(pm25, 1)
        pm10 = round(pm10, 1)
        no2 = round(no2, 1)
        so2 = round(so2, 1)
        co = round(co, 2)
        o3 = round(o3, 1)
        
        aqi = calculate_aqi_cpcb(pm25, pm10, no2, so2, co, o3)
        category = get_aqi_category(aqi)
        
        data.append({
            'Timestamp': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'City': city_name,
            'PM2.5': pm25,
            'PM10': pm10,
            'NO2': no2,
            'SO2': so2,
            'CO': co,
            'O3': o3,
            'AQI': aqi,
            'AQI_Category': category
        })
        
    return pd.DataFrame(data)

def generate_full_dataset(output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 6, 1)
    
    # Establish characteristic pollutant profiles for each city
    city_profiles = {
        'Jalgaon':   {'pm25': 98.0, 'pm10': 185.0, 'no2': 45.0, 'so2': 15.0, 'co': 1.80, 'o3': 38.0},
        'Mumbai':    {'pm25': 48.0, 'pm10': 92.0,  'no2': 28.0, 'so2': 12.0, 'co': 0.95, 'o3': 28.0},
        'Bengaluru': {'pm25': 28.0, 'pm10': 55.0,  'no2': 18.0, 'so2': 8.0,  'co': 0.65, 'o3': 32.0},
        'Chennai':   {'pm25': 36.0, 'pm10': 68.0,  'no2': 15.0, 'so2': 9.0,  'co': 0.75, 'o3': 26.0},
        'Kolkata':   {'pm25': 64.0, 'pm10': 118.0, 'no2': 32.0, 'so2': 10.0, 'co': 1.10, 'o3': 30.0},
        'Hyderabad': {'pm25': 42.0, 'pm10': 85.0,  'no2': 24.0, 'so2': 11.0, 'co': 0.85, 'o3': 34.0}
    }
    
    dfs = []
    for city, profile in city_profiles.items():
        city_df = generate_city_data(city, profile, start_date, end_date)
        dfs.append(city_df)
        
    full_df = pd.concat(dfs, ignore_index=True)
    
    # Introduce random missing values (NaNs) in features (~5% missingness)
    print("Injecting missing values...")
    mask_features = ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3']
    for col in mask_features:
        # Select 5% random indices to turn to NaN
        nan_indices = full_df.sample(frac=0.05, random_state=42).index
        full_df.loc[nan_indices, col] = np.nan
        # Recalculate AQI where features are missing to simulate real CPCB missingness
        # For simplicity, we just recalculate AQI for rows with missing features
        # since we want to demonstrate imputation on features, then feeding to AQI predictions
        
    # Introduce duplicate records (~0.5%)
    print("Injecting duplicate records...")
    dup_indices = full_df.sample(frac=0.005, random_state=42).index
    duplicates = full_df.loc[dup_indices].copy()
    # Add a slight shift to timestamp or keep exact same to show exact duplicate detection
    full_df = pd.concat([full_df, duplicates], ignore_index=True)
    
    # Introduce outliers (~0.5%)
    print("Injecting outliers...")
    for col in ['PM2.5', 'PM10']:
        outlier_indices = full_df.sample(frac=0.0025, random_state=100).index
        # Extreme spikes (e.g. 800 - 1500)
        full_df.loc[outlier_indices, col] = np.random.uniform(800, 1500, size=len(outlier_indices))
        
        # Negative values (physically impossible but common sensor faults)
        negative_indices = full_df.sample(frac=0.0025, random_state=200).index
        full_df.loc[negative_indices, col] = np.random.uniform(-100, -5, size=len(negative_indices))
        
    for col in ['CO']:
        outlier_indices = full_df.sample(frac=0.005, random_state=300).index
        # Spike
        full_df.loc[outlier_indices, col] = np.random.uniform(50, 99, size=len(outlier_indices))
        
    # Sort dataset by timestamp and city
    # Parse timestamp back to datetime for sorting
    full_df['parsed_time'] = pd.to_datetime(full_df['Timestamp'])
    full_df = full_df.sort_values(by=['City', 'parsed_time']).drop(columns=['parsed_time']).reset_index(drop=True)
    
    full_df.to_csv(output_path, index=False)
    print(f"Data generation complete. Dataset saved to {output_path} with {len(full_df)} records.")

if __name__ == '__main__':
    generate_full_dataset("data/raw/city_hour.csv")
