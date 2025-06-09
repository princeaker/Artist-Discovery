from airflow import DAG
from datetime import datetime
from airflow.operators.python import PythonOperator
from utils.artist_discovery_dag.get_albums import process
# from airflow.providers.amazon.aws.operators.glue import GlueJobOperator


with DAG(
    dag_id = "artist_discovery_dag",

    default_args = {
        'owner': 'airflow',
        'depends_on_past': False,
        'retries': 1,
        'email_on_failure': False,
        'email_on_retry': False
    },
    schedule='@daily',
    start_date=datetime(2025, 6, 7),
    catchup=False
) as dag:
    
    # Task to get music albums from Apple Music
    get_albums_task = PythonOperator(
        task_id='get_music_albums',
        python_callable=process
        # Replace with the actual function to retrieve albums
    )
    

    # artist_albums_task = GlueJobOperator(
    #     task_id='get_music_albums',
    #     job_name='artist_albums_job',
    #     script_location='s3://artist-discovery-scripts/get_music_albums.py',  # Update with your script location
    #     region_name='us-east-2',  # Update with your region
    # )
    
    get_albums_task