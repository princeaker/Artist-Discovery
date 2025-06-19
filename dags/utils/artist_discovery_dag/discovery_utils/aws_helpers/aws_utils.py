import boto3
import pyarrow as pa
import pandas as pd
import logging
import pyarrow.parquet as pq
import datetime
from io import BytesIO

def upload_df_to_s3_parquet(df, bucket_name, file_path=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    buffer = BytesIO()

    table = pa.Table.from_pandas(df)
    pq.write_table(table, buffer)
    buffer.seek(0)

    if file_path is None:
        file_path = 'silver/apple-albums/albums_' + str(pd.to_datetime('today').date()) + '.parquet' 

    # Upload the file
    s3_client = boto3.client('s3', region_name='us-east-2')
    try:
        response = s3_client.upload_fileobj(buffer, bucket_name, file_path)
    except Exception as e:
        logging.error(f"Failed to upload {file_path} to {bucket_name}/{file_path}")
        raise e
    
    
def get_s3_object(bucket_name, key):
    """Retrieve an object from S3 bucket."""
    s3_client = boto3.client('s3', region_name='us-east-2')
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response['Body'].read()
    except Exception as e:
        logging.error(f"Failed to retrieve {key} from {bucket_name}: {e}")
        raise e