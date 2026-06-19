import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os

class AQIPreprocessingPipeline:
    def __init__(self, data_path):
        self.data_path = data_path
        self.scaler = StandardScaler()
        self.medians = {}
        self.summary = {}
        
    def fit_transform(self, save_scaler_path=None):
        # 1. Load Data
        df = pd.read_csv(self.data_path)
        raw_rows = len(df)
        
        # 2. Duplicate Removal
        initial_duplicates = df.duplicated().sum()
        df = df.drop_duplicates().reset_index(drop=True)
        post_dup_rows = len(df)
        self.summary['duplicates_removed'] = int(initial_duplicates)
        
        # 3. Outlier Handling
        # Identify numeric columns for imputation and outlier handling
        pollutant_cols = ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3']
        outliers_detected = {}
        
        for col in pollutant_cols:
            # We calculate IQR on non-null values
            valid_vals = df[col].dropna()
            if len(valid_vals) > 0:
                q1 = valid_vals.quantile(0.25)
                q3 = valid_vals.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                
                # Detect outliers (either below lower bound or above upper bound)
                # Note: negative values are also caught by lower_bound (since lower bound for PM2.5 is usually > 0)
                outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
                outliers_detected[col] = int(outlier_mask.sum())
                
                # Outlier Removal: Replace outliers with NaN, so they are imputed in the next step
                df.loc[outlier_mask, col] = np.nan
                
        self.summary['outliers_handled'] = outliers_detected
        
        # 4. Missing Value Handling & Median Imputation
        # We calculate median for each pollutant, grouped by City, for better accuracy
        missing_before = df[pollutant_cols].isna().sum().to_dict()
        self.summary['missing_before_imputation'] = {col: int(val) for col, val in missing_before.items()}
        
        # Store group-wise medians for future inference
        for col in pollutant_cols:
            self.medians[col] = df.groupby('City')[col].median().to_dict()
            # Overall median fallback in case of new city in prediction
            self.medians[f"{col}_global"] = df[col].median()
            
            # Perform imputation
            df[col] = df.groupby('City')[col].transform(lambda x: x.fillna(x.median()))
            # If any remaining NaNs (e.g. if a city has all NaNs for a pollutant, which shouldn't happen), fill with global median
            df[col] = df[col].fillna(self.medians[f"{col}_global"])
            
        # Re-calculate AQI if any of the features were imputed to ensure data integrity
        # In this project, to keep training target (AQI) matching the features:
        # We recalculate the actual CPCB AQI using the clean imputed pollutants
        from ml.data_generator import calculate_aqi_cpcb, get_aqi_category
        
        print("Recalculating AQI on cleaned features...")
        clean_aqis = []
        for idx, row in df.iterrows():
            aqi = calculate_aqi_cpcb(row['PM2.5'], row['PM10'], row['NO2'], row['SO2'], row['CO'], row['O3'])
            clean_aqis.append(aqi)
            
        df['AQI'] = clean_aqis
        # Impute any final missing AQI values (should be none since features are imputed)
        df['AQI'] = df['AQI'].fillna(df['AQI'].median())
        df['AQI_Category'] = df['AQI'].apply(get_aqi_category)
        
        missing_after = df[pollutant_cols].isna().sum().to_dict()
        self.summary['missing_after_imputation'] = {col: int(val) for col, val in missing_after.items()}
        self.summary['preprocessed_rows'] = len(df)
        self.summary['raw_rows'] = raw_rows
        
        # 5. Scaling and Train/Test Split
        # Features: PM2.5, PM10, NO2, SO2, CO, O3
        # Target: AQI
        X = df[pollutant_cols].values
        y = df['AQI'].values
        
        # Fit scaler on features
        X_scaled = self.scaler.fit_transform(X)
        
        if save_scaler_path:
            os.makedirs(os.path.dirname(save_scaler_path), exist_ok=True)
            joblib.dump(self.scaler, save_scaler_path)
            # Also save medians for predictions
            joblib.dump(self.medians, save_scaler_path.replace("scaler.joblib", "medians.joblib"))
            
        # Chronological Split (Train 80%, Test 20%)
        # Since it is a city-by-city time series, we split each city's data chronologically
        # to ensure no leakage across time or cities.
        X_train_list, X_test_list = [], []
        y_train_list, y_test_list = [], []
        
        for city in df['City'].unique():
            city_mask = df['City'] == city
            city_X = X_scaled[city_mask]
            city_y = y[city_mask]
            
            split_idx = int(len(city_X) * 0.8)
            
            X_train_list.append(city_X[:split_idx])
            X_test_list.append(city_X[split_idx:])
            y_train_list.append(city_y[:split_idx])
            y_test_list.append(city_y[split_idx:])
            
        X_train = np.concatenate(X_train_list, axis=0)
        X_test = np.concatenate(X_test_list, axis=0)
        y_train = np.concatenate(y_train_list, axis=0)
        y_test = np.concatenate(y_test_list, axis=0)
        
        self.summary['train_shape'] = X_train.shape
        self.summary['test_shape'] = X_test.shape
        
        # Save preprocessed clean data for visualization
        os.makedirs("data/processed", exist_ok=True)
        df.to_csv("data/processed/city_hour_clean.csv", index=False)
        
        return X_train, X_test, y_train, y_test, df

    def transform_input(self, input_dict, city=None):
        # Used for real-time user predictions
        # input_dict has PM2.5, PM10, NO2, SO2, CO, O3
        pollutant_cols = ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3']
        processed_input = []
        
        for col in pollutant_cols:
            val = input_dict.get(col, np.nan)
            
            # Handle missing input values using medians
            if pd.isna(val):
                if city and city in self.medians.get(col, {}):
                    val = self.medians[col][city]
                else:
                    val = self.medians.get(f"{col}_global", 0.0)
            processed_input.append(val)
            
        # Scale input
        scaled_input = self.scaler.transform([processed_input])
        return scaled_input
