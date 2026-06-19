# Deployment Guide for AQI Comparative Analysis System

This guide provides step-by-step instructions on how to deploy the Air Quality Index (AQI) Comparative Analysis System to production. Since this project uses **TensorFlow**, **Pandas**, and **Scikit-learn**, it has a larger memory footprint than simple web apps. 

We recommend the following three deployment pathways, ordered by ease-of-use and cost-effectiveness:

1. **Hugging Face Spaces (Recommended - Free, High Resource CPU)**
2. **Render (Free Web Service - Standard Cloud Hosting)**
3. **Docker Containers (VPS, AWS, GCP, or Azure)**

---

## 📋 Table of Contents
1. [Prerequisites & Repository Setup](#1-prerequisites--repository-setup)
2. [Option A: Deploying on Hugging Face Spaces (Recommended)](#option-a-deploying-on-hugging-face-spaces-recommended)
3. [Option B: Deploying on Render (Free Python Hosting)](#option-b-deploying-on-render-free-python-hosting)
4. [Option C: Deploying using Docker (Self-Hosted/VPS/AWS)](#option-c-deploying-using-docker-self-hostedvpsaws)
5. [Production Optimization Tips](#-production-optimization-tips)

---

## 1. Prerequisites & Repository Setup

Before deploying to any platform, you need to initialize Git, create a `.gitignore` file so that your local virtual environment isn't committed, and commit the existing trained models and preprocessed data.

### Step 1: Create a `.gitignore` file
Create a file named `.gitignore` in the root of the project with the following contents:
```gitignore
# Virtual Environment
.venv/
venv/
ENV/
env/

# Python caching
__pycache__/
*.pyc
*.pyo
*.pyd

# Operating system files
.DS_Store
Thumbs.db

# Training logs
models/train.log
```

### Step 2: Initialize Git & Commit Files
Open your terminal/command prompt in the project folder and run:
```bash
# Initialize Git repository
git init

# Add all files (this will include the models/ and data/ folders)
git add .

# Create the first commit
git commit -m "Initial commit with trained models and data"
```

### Step 3: Push to GitHub
Create a new private or public repository on GitHub and link it:
```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

---

## Option A: Deploying on Hugging Face Spaces (Recommended)

**Why choose Hugging Face Spaces?**
- **100% Free** CPU basic tier with **16GB RAM** and **50GB Disk**.
- TensorFlow and Pandas require substantial memory. Render's free tier (512MB RAM) may run out of memory (OOM), whereas Hugging Face handles it easily.
- Instant deployments via Git or Docker.

### Step-by-Step Deployment:
1. Create a free account at [Hugging Face](https://huggingface.co/).
2. Click on **Spaces** in the top navigation bar, then click **Create new Space**.
3. Configure your Space:
   - **Space Name:** `aqi-analysis` (or similar)
   - **License:** `mit` (or choose any)
   - **SDK:** Select **Docker** (Blank template).
   - **Space Hardware:** CPU Basic (Free - 16GB RAM).
   - **Visibility:** Public or Private (your choice).
4. Click **Create Space**.
5. Once created, Hugging Face will show you instructions to clone the Space repository.
6. Copy your local files into the cloned repository, or add the Hugging Face Git remote directly to your local workspace:
   ```bash
   git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
   ```
7. A `Dockerfile` is required for Hugging Face to run your Flask application. Create a `Dockerfile` in your project root (see template below).
8. Commit and push to Hugging Face:
   ```bash
   git add Dockerfile
   git commit -m "Add Dockerfile for Hugging Face deployment"
   git push -f hf main
   ```
9. Hugging Face will automatically build the container and serve your application!

---

## Option B: Deploying on Render (Free Python Hosting)

**Why choose Render?**
- Popular, easy developer experience, automatically deploys from GitHub.
- *Note:* The Free tier has **512 MB RAM**. Since TensorFlow is heavy, loading the ANN and LSTM models might cause a crash. To deploy successfully on the free tier, we recommend using CPU-only version of TensorFlow or running with light workers.

### Step-by-Step Deployment:
1. Create a free account at [Render](https://render.com/).
2. Create a new **Web Service** and connect your GitHub repository.
3. Configure the service:
   - **Name:** `aqi-comparative-analysis`
   - **Environment:** `Python 3`
   - **Region:** Choose the closest region to you.
   - **Branch:** `main`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt gunicorn
     ```
   - **Start Command:**
     ```bash
     gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 app:app
     ```
     *(Note: We use 1 worker and 4 threads to minimize memory consumption on Render's free tier).*
4. Select the **Free** tier.
5. Under **Advanced Settings**, add the following environment variable:
   - `PYTHON_VERSION` = `3.9.18` (or your local Python version)
6. Click **Create Web Service**. Render will build and deploy the app.

---

## Option C: Deploying using Docker (Self-Hosted/VPS/AWS)

If you have your own VPS (DigitalOcean, Linode, AWS EC2), you can containerize the app using Docker to ensure it runs identically to your local system.

### Step 1: Write a Dockerfile
Create a `Dockerfile` in the root directory:
```dockerfile
# Use an official lightweight Python image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies (plus gunicorn for production)
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project files
COPY . .

# Expose the application port
EXPOSE 7860

# Start Flask using gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120 app:app"]
```

### Step 2: Build and Run locally with Docker
```bash
# Build the Docker image
docker build -t aqi-app .

# Run the container (binds container port 7860 to host port 5000)
docker run -p 5000:7860 -e PORT=7860 aqi-app
```
Go to `http://localhost:5000` to test it.

---

## ⚡ Production Optimization Tips

1. **Pre-trained Models (Crucial):** Make sure the `models/` directory is committed. If a user clicks "Retrain Models" on a free cloud server, the server will likely run out of CPU/RAM limits or crash due to the resource-intensive subprocess. Committing pre-trained models ensures predictions work instantly.
2. **Turn off debug mode in production:** In `app.py`, change:
   `app.run(debug=True, ...)` to `app.run(debug=False, ...)` or let Gunicorn manage execution. (Gunicorn bypasses `if __name__ == '__main__':` entirely).
3. **TensorFlow Memory Overhead:** TensorFlow can allocate all GPU/CPU memory on startup. Since this application only runs prediction (inference), you can add these environment variables on your cloud provider:
   - `TF_CPP_MIN_LOG_LEVEL` = `2` (removes noisy debug prints)
   - `OMP_NUM_THREADS` = `1` (restricts thread creation, reducing memory footprint)
