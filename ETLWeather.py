from airflow import DAG
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.decorators import task
from airflow.utils.dates import days_ago
import requests
import json


Latitude = '51.5074'
Longitude = '-0.1278'
postgres_con_id = 'postgres_default'
Api_conn_id = 'open_meteo_api'

default_args = {
    'owner' :'airflow',
    'start_date':days_ago(1)
}
## DAG
with DAG(dag_id='weather_etl_pipline',
         default_args = default_args,
         schedule_interval = '@daily',
         catchup = False) as dag:
    @task()
    def extract_weather_data():

        httphook = HttpHook(http_conn_id=Api_conn_id,method='GET')

        endpoint = f'/v1/forecast?latitude={Latitude}&longitude={Longitude}&current_weather=true'
        response = httphook.run(endpoint)
        if response.status_code == 200:
           return response.json()
        else:
           raise Exception(f"Failed to fetch weather data: {response.status_code}")

        
    @task()
    def transfrom_weather_data(weather_data):

        current_weather = weather_data['current_weather']
        transformed_data = {
            'latitude':Latitude,
            'longitude':Longitude,
            'temperature':current_weather['temperature'],
            'windspeed':current_weather['windspeed'],
            'winddirection':current_weather['winddirection'],
            'weathercode':current_weather['weathercode']
        }
        return transformed_data
    @task()
    def load_weather_data(transformed_data):
        pg_hook = PostgresHook(Postgres_conn_id=postgres_con_id)
        conn = pg_hook.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_data(
        latitude FLOAT,
        longitude FLOAT,
        temperature FLOAT,
        windspeed FLOAT,
        winddirection FLOAT,
        weathercode INT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("""
        INSERT INTO weather_data(latitude,longitude,temperature,windspeed,winddirection,weathercode)
        VALUES(%s,%s,%s,%s,%s,%s)
        """,(
            transformed_data['latitude'],
            transformed_data['longitude'],
            transformed_data['temperature'],
            transformed_data['windspeed'],
            transformed_data['winddirection'],
            transformed_data['weathercode']
        ))
        conn.commit()
        cursor.close()
    weather_data = extract_weather_data()
    transformed_data = transfrom_weather_data(weather_data)
    load_weather_data(transformed_data)