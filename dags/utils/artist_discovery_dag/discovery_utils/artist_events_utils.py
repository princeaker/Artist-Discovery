import boto3
import pyarrow as pa
import pandas as pd
import logging
import pyarrow.parquet as pq
import datetime
import uuid
import hashlib
from io import BytesIO
from utils.artist_discovery_dag.discovery_utils.aws_helpers.aws_utils import get_s3_object, upload_df_to_s3_parquet


def merge_album_events(album_df, events_df):
    """Merge album DataFrame with events DataFrame on artist_id."""
    merged_df = album_df.merge(
        events_df,
        how='left',
        left_on='artist_sg_index',
        right_on='artist_id'
    )
    return merged_df

def generate_unique_id(field1, field2):
    combined_string = str(field1) + str(field2)
    hashed_string = hashlib.sha256(combined_string.encode()).hexdigest()
    return uuid.UUID(hashed_string[:32])


def artist_events_process():
    bucket_name = 'artist-discovery-data'
    album_key = 'silver/apple-albums-enriched/albums_enriched_' + str(pd.to_datetime('today').date())+ '.parquet'
    album_file = get_s3_object(bucket_name, album_key)
    events_key = 'silver/artist-events/events_' + str(pd.to_datetime('today').date())+ '.parquet'
    events_file = get_s3_object(bucket_name, events_key)

    album_df = pd.read_parquet(BytesIO(album_file), engine='pyarrow')
    events_df = pd.read_parquet(BytesIO(events_file), engine='pyarrow')

    album_set = album_df[['album_artist','album_name', 'release_date', 'artist_sg_index']]
    event_set = events_df[['artist_id', 'event_id', 'event_name', 'event_date_time', 'venue_name', 'venue_city', 'venue_state', 'venue_type']]

    merged_df = merge_album_events(album_set, event_set)

    merged_df['id'] = merged_df[['artist_sg_index','event_id']].apply(lambda x: generate_unique_id(x.iloc[0], x.iloc[1]), axis=1)
    merged_df['id'] = merged_df['id'].astype(str)
    merged_df = merged_df.filter(items=['id','album_artist','album_name','release_date','event_name','event_date_time','venue_name','venue_type','venue_city','venue_state'])

    upcoming_events_df_file_path = 'analytics/upcoming-events/date=' + str(pd.to_datetime('today').date()) + '/upcoming_events.parquet'
    
    # Upload the transformed DataFrames to S3
    upload_df_to_s3_parquet(merged_df, bucket_name, upcoming_events_df_file_path)
