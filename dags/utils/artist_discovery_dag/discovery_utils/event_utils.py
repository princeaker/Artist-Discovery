import requests
import boto3
import json
import pyarrow as pa
import pandas as pd
import logging
import pyarrow.parquet as pq
import datetime
from io import BytesIO
from utils.artist_discovery_dag.discovery_utils.aws_helpers.aws_utils import get_s3_object, upload_df_to_s3_parquet



def clean_artist_names(df):
    """Clean artist names by removing leading/trailing whitespace and splitting on '&'."""
    df['album_artist_clean'] = df['album_artist'].str.split('&', expand=True)[0]
    df['album_artist_clean'] = df['album_artist_clean'].str.strip()
    return df

def remove_nan_from_list(input_list):
       return [x for x in input_list if pd.notna(x)]

def get_artist_id(name, session):
    """Get the artist ID from SeatGeek"""
    if name is None:
        return None 
    
    response = session.get('https://api.seatgeek.com/2/performers', params={'q': name, 'per_page': 5, 'page': 1})

    return response.json()['performers'][0]['id'] if len(response.json()['performers']) != 0 else None


def get_upcoming_events(artist_id, session=None):
    """Get upcoming events for a given artist ID."""
    if session is None:
        return None
    
    response = session.get('https://api.seatgeek.com/2/events', params={'performers.id': artist_id, 'per_page': 5, 'page': 1})
    events = response.json()['events']
    
    upcoming_events = []
    for event in events:
        event_date_time = datetime.datetime.fromisoformat(event['datetime_local'])
        if event_date_time > datetime.datetime.now() and (event_date_time - datetime.datetime.now()) < datetime.timedelta(days=30):
            upcoming_events.append({
                'event_id': event['id'],
                'artist_id': artist_id,
                'event_name': event['title'],
                'event_date_time': event_date_time,
                'venue_name': event['venue']['name'],
                'venue_city': event['venue']['city'],
                'venue_state': event['venue']['state'],
                'venue_type': event['type']
            })

    try:
        if upcoming_events:
            logging.info(f"Found {len(upcoming_events)} upcoming events for artist ID {artist_id}.")
            df = pd.DataFrame(upcoming_events)
            df['event_date'] = df['event_date_time'].dt.date
            return df
        else:
            logging.warning("No upcoming events found for the artist in the next 30 days.")

    except Exception as e:
        logging.error("Failed to create DataFrame from upcoming events.")
        raise e
        

def transform_create_sg_data(df: pd.DataFrame):
    """This function transforms the input DataFrame by cleaning artist names 
    and fetching artist IDs and creates a new dataset with upcoming events from SeatGeek."""

    ssm_client = boto3.client('ssm', region_name='us-east-2')
    sg_key = ssm_client.get_parameter(
        Name='/seatgeek/client_key',
        WithDecryption=True
    )['Parameter']['Value']

    sg_secret = ssm_client.get_parameter(
        Name='/seatgeek/client_secret',
        WithDecryption=True
    )['Parameter']['Value']


    artist_df = clean_artist_names(df)

    with requests.Session() as session:
        session.auth = (sg_key, sg_secret)
        df['artist_sg_index'] = df[['album_artist_clean']].apply(lambda x: get_artist_id(name=x, session=session), axis=1)
        df['artist_sg_index'] = df['artist_sg_index'].astype('Int64')
        df['ingest_ts'] = datetime.datetime.now()

        artist_id_list = remove_nan_from_list(df['artist_sg_index'].unique().tolist())

        artist_events_list = []
        for i in artist_id_list:
            artist_events_list.append(get_upcoming_events(artist_id=i, session=session))


    artist_events_df = pd.concat(artist_events_list, ignore_index=True)
    artist_events_df['ingest_ts'] = datetime.datetime.now()
    return [artist_df, artist_events_df]

def event_process():
    """Main function to process events and upload to S3."""
    # Retrieve the DataFrame from S3

    bucket_name = 'artist-discovery-data'
    key = 'silver/apple-albums/albums_' + str(pd.to_datetime('today').date()) + '.parquet' 
    file = get_s3_object(bucket_name, key)
    
    if file is None:
        logging.error("Failed to retrieve DataFrame from S3.")
        raise Exception("Failed to retrieve DataFrame from S3.")
    
    df = pd.read_parquet(BytesIO(file))
    
    # Transform and create SeatGeek data
    artist_df, artist_events_df = transform_create_sg_data(df)
    artist_df_file_path = 'silver/apple-albums-enriched/albums_enriched_' + str(pd.to_datetime('today').date()) + '.parquet'
    events_df_file_path = 'silver/artist-events/events_' + str(pd.to_datetime('today').date()) + '.parquet'
    
    # Upload the transformed DataFrames to S3
    upload_df_to_s3_parquet(artist_df, bucket_name, artist_df_file_path)
    upload_df_to_s3_parquet(artist_events_df, bucket_name, events_df_file_path)
    
        