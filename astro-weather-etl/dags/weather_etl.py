from airflow.decorators import dag, task
import requests
import psycopg2
import datetime
import pendulum

API_URL = "https://api.open-meteo.com/v1/forecast"
LAT, LON = 28.6139, 77.2090  # New Delhi

@dag(schedule="* * * * *", start_date=pendulum.now().subtract(days=1), catchup=False, tags=["weather"])
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
            dbname="postgres",
            user="postgres",
            password="postgres",
            host="postgres",  # This is the internal Docker name for Astro’s default Postgres
            port="5432"
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