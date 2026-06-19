---
title: AQI Comparative Analysis System
emoji: 🌬️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# AQI Comparative Analysis System

An interactive web application analyzing and predicting Air Quality Index (AQI) using Machine Learning and Deep Learning models (Random Forest, ANN, LSTM).

## Features
- **Dashboard:** Exploratory Data Analysis (EDA) charts including pollutant distributions, correlations, monthly trends, and feature importance.
- **Model Comparison:** Compare R² scores, Mean Absolute Error (MAE), and training logs across various regressors.
- **Single Prediction:** Interactive form to input pollutant levels (PM2.5, PM10, NO2, etc.) and predict AQI using standard regression or deep learning models.
- **Hourly Forecast:** Visualizes 24-hour future forecasting for major cities (Delhi, Mumbai, Bengaluru, etc.) using LSTM.
- **City Comparison:** Compare current AQI metrics and 7-day historical trends across multiple cities side-by-side.

## Tech Stack
- **Backend:** Flask, Python 3.9
- **Libraries:** TensorFlow, Scikit-learn, Pandas, NumPy, Joblib
- **Frontend:** HTML, Bootstrap 5, Chart.js
- **Deployment:** Docker
