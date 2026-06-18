# SOC Security Analytics Platform - Execution & Running Guide

This guide provides step-by-step instructions to spin up the local infrastructure, configure the environment, and run the FastAPI backend for the ISRO SOC Security Analytics Platform.

---

## Prerequisites
Before you start, make sure you have the following installed on your machine:
* **Docker & Docker Compose** (Ensure the daemon is running)
* **Python 3.10+** (Preferably with `uv` installed for faster dependency installation)
* **cURL** or a REST client (like Postman or VS Code Thunder Client) for hitting endpoints (optional, as Swagger UI is available)

---

## Step-by-step Execution Instructions

### Step 1: Start the Infrastructure Stack
The platform uses **Elasticsearch** (port `9200`) and **Kibana** (port `5601`) for data ingestion, querying, and visual exploration.

1. Navigate to the project root directory in your terminal:
   ```bash
   cd /Users/bhaveshpatil/Developer/Project-SOC/Project-SOC
   ```
2. Start the services in detached mode:
   ```bash
   docker-compose up -d
   ```
3. Verify that the containers are healthy and running:
   ```bash
   docker-compose ps
   ```

---

### Step 2: Configure the Environment Variables (`.env`)
The environment configuration has been generated for you. If you need to review or customize settings (such as logging levels, host/port settings, or the models directory):

* For running from the **root directory**: Review [`.env`](file:///Users/bhaveshpatil/Developer/Project-SOC/Project-SOC/.env)
* For running from the **backend directory**: Review [`backend/.env`](file:///Users/bhaveshpatil/Developer/Project-SOC/Project-SOC/backend/.env)

Both files are pre-configured to authenticate with Elasticsearch using the password `elasticpassword` as defined in [`docker-compose.yml`](file:///Users/bhaveshpatil/Developer/Project-SOC/Project-SOC/docker-compose.yml).

---

### Step 3: Setup Virtual Environment & Install Dependencies
Navigate to the `backend` directory and set up your Python environment using either `uv` (recommended) or standard `venv`.

#### Option A: Using `uv` (Fastest)
```bash
# Navigate to the backend directory
cd backend

# Create the virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Install all dependencies
uv pip install -r requirements.txt
```

#### Option B: Using standard Python `venv`
```bash
# Navigate to the backend directory
cd backend

# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

---

### Step 4: Run the FastAPI Application Server
Start the Uvicorn ASGI server. You have two options for where you run it:

#### Option 1: Running from the `backend/` directory (Recommended)
Make sure your virtual environment is activated and run:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Running from the project root directory
Ensure the virtual environment is activated and run:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### Step 5: Verify the Startup
* **Health Check API:** Open your browser or run a cURL command to check if the server is healthy:
  ```bash
  curl http://localhost:8000/health
  ```
  Expected response: `{"status": "ok", "version": "1.0.0"}`

* **Swagger Interactive API Documentation:** Visit:
  `http://localhost:8000/docs`
  Here you can test all endpoints directly.

---

### Step 6: Initial Ingestion, Training, & Threat Scoring

#### 1. Ingestion Warning on First Run
On the first run, the FastAPI server lifespan handler checks for pre-trained model files (like `isolation_forest.pkl` and `autoencoder.pt`) in `models/saved`. Since it is a fresh setup, it will trigger an initial training job. If Elasticsearch doesn't contain any security logs yet, it will log a warning that no baseline data is available, and gracefully degrade.

#### 2. Mock Log Ingestion
Inject security logs (syslog, endpoint process events, or PowerShell operational logs) into Elasticsearch.

#### 3. Trigger Initial Model Training
Once some logs are present in Elasticsearch, manually trigger model training by executing a POST request:
```bash
curl -X POST http://localhost:8000/api/training/initial
```
This trains the Isolation Forest, Autoencoder, and LSTM models and registers runs to MLflow.

#### 4. Trigger Threat Scoring Engine Cycle
To force the scoring engine to query recent logs, generate features, evaluate rules, score them with ML models, and output processed alerts to `soc-processed-alerts`:
```bash
curl -X POST http://localhost:8000/api/alerts/trigger-scoring
```

#### 5. MLflow UI (Optional)
To view metrics, parameter logs, and model versions, start the MLflow server:
```bash
mlflow ui --port 5000
```
Open `http://localhost:5000` in your browser.
