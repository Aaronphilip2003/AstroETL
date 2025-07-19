Awesome! Let's walk through everything **from scratch** — installing Docker and Astro CLI, and then setting up your **Airflow ETL pipeline on your external SSD** without using internal disk space.

We’ll **store all code and persistent data on `/Volumes/New Volume`**, and run everything via **Docker containers**.

----------

## 🧱 PART 1: Install Prerequisites

### ✅ Step 1: Install Docker Desktop for macOS

1.  Download: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
    
2.  Install the `.dmg` file and follow the prompts
    
3.  Start Docker Desktop
    
4.  Verify in terminal:
    

```bash
docker --version

```

Expected output (something like):

```bash
Docker version 24.x.x, build abcdef

```

----------

### ✅ Step 2: Install Astro CLI

```bash
brew install astronomer/tap/astro

```

Verify:

```bash
astro --version

```

----------

## 📦 PART 2: Build Your ETL Project on External SSD

Let’s assume your external SSD is mounted as:

```
/Volumes/New Volume

```

----------

## 🏗️ Step-by-Step from Scratch

### 📁 Step 1: Create Your Project Folder on SSD

```bash
cd "/Volumes/New Volume"
mkdir astro-weather-etl && cd astro-weather-etl

```

### 🚀 Step 2: Initialize Astro Airflow Project

```bash
astro dev init

```

This will generate an Airflow project in **this folder on your SSD**.

----------

### 📦 Step 3: Install Python Dependencies

Edit the `requirements.txt` file in the project root:

```txt
requests
psycopg2-binary

```

----------

### 🐘 Step 4: Add PostgreSQL with Volume Bound to SSD

Create `docker-compose.override.yml` in the root of your project:

```yaml
version: '3'
services:
  data-postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: weather_db
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /Volumes/New Volume/astro-weather-etl/pgdata

```

Then create that directory:

```bash
mkdir -p "/Volumes/New Volume/astro-weather-etl/pgdata"

```

> ✅ This ensures Postgres **only uses disk space on the SSD**

----------

### 📜 Step 5: Write the ETL DAG using Open-Meteo API

Create the file: `dags/weather_etl.py`

```python
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
import requests
import psycopg2
import datetime

API_URL = "https://api.open-meteo.com/v1/forecast"
LAT, LON = 28.6139, 77.2090  # New Delhi

@dag(schedule_interval="* * * * *", start_date=days_ago(1), catchup=False, tags=["weather"])
def weather_etl():

    @task
    def extract():
        params = {
            "latitude": LAT,
            "longitude": LON,
            "current": "temperature_2m,relative_humidity_2m,precipitation"
        }
        res = requests.get(API_URL, params=params)
        data = res.json().get("current", {})
        data["timestamp"] = datetime.datetime.utcnow().isoformat()
        return data

    @task
    def load(data):
        conn = psycopg2.connect(
            dbname="weather_db",
            user="airflow",
            password="airflow",
            host="data-postgres",
            port=5432
        )
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                timestamp TIMESTAMP,
                temperature FLOAT,
                humidity FLOAT,
                precipitation FLOAT
            )
        """)
        cur.execute("""
            INSERT INTO weather (timestamp, temperature, humidity, precipitation)
            VALUES (%s, %s, %s, %s)
        """, (
            data.get("timestamp"),
            data.get("temperature_2m"),
            data.get("relative_humidity_2m"),
            data.get("precipitation")
        ))
        conn.commit()
        cur.close()
        conn.close()

    load(extract())

weather_etl()

```

----------

### 🏃 Step 6: Start Everything from External SSD

```bash
astro dev start

```

Docker will build and run:

-   Airflow Webserver, Scheduler
    
-   Triggerer
    
-   Metadata DB (internal)
    
-   External Postgres service (our sink)
    

✅ All files and Docker volumes used in `docker-compose.override.yml` will be bound to your **external SSD only**

----------

### 🌐 Step 7: Access Airflow UI

-   Go to: [http://localhost:8080](http://localhost:8080/)
    
-   Username: `admin`, Password: `admin` (default)
    
-   Find and trigger `weather_etl` DAG
    

----------

### 🧪 Step 8: Verify Postgres Data

Connect using any Postgres GUI or CLI:

```bash
psql -h localhost -p 5433 -U airflow -d weather_db
# password: airflow
# then:
SELECT * FROM weather;

```

----------

## ✅ Summary

Component

Location

Code & DAGs

`/Volumes/New Volume/astro-weather-etl/`

Postgres volume

`/Volumes/New Volume/astro-weather-etl/pgdata`

Airflow container

Docker (no internal disk use)

Postgres sink

Docker, bound to SSD only

ETL Schedule

Every minute

API Source

Open-Meteo (free, no auth)

----------

Do you want me to give you the full file dump (`.zip` or `.tar.gz`) you can directly unzip into your SSD?