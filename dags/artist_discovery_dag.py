from airflow import DAG
from datetime import datetime
from airflow.operators.python import PythonOperator
from utils.artist_discovery_dag.discovery_utils.album_utils import album_process
from utils.artist_discovery_dag.discovery_utils.event_utils import event_process
from utils.artist_discovery_dag.discovery_utils.artist_events_utils import artist_events_process
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
        python_callable=album_process
    )

    get_events_task = PythonOperator(
        task_id='get_events',
        python_callable=event_process
   
    )

    get_artist_upcoming_events_task = PythonOperator(
        task_id='get_artist_upcoming_events',
        python_callable=artist_events_process  # Replace with your analytics processing function
    )
    

    # artist_albums_task = GlueJobOperator(
    #     task_id='get_music_albums',
    #     job_name='artist_albums_job',
    #     script_location='s3://artist-discovery-scripts/get_music_albums.py',  # Update with your script location
    #     region_name='us-east-2',  # Update with your region
    # )
    
    get_albums_task >> get_events_task >> get_artist_upcoming_events_task