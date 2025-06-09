import requests
import boto3
import base64
import json
import datetime
import jwt
import pandas as pd
import pyarrow as pa
import logging
import pyarrow.parquet as pq
from io import BytesIO

def get_jwt_token(kID, private_key, iss):
    header = {
        "alg": "ES256", #algorithm used for signing the JWT token
        "kid": kID # Key ID. This is a 10-character identifer obtained from the developer account
    }

    claims = {
        "iss": iss,  # Issuer claim key. This is a 10-character Team ID obtained from the apple developer account.
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24), # Expiration time
        "iat": datetime.datetime.now(datetime.timezone.utc), # Issued at time

    }

    try:
        encoded_jwt = jwt.encode(claims, private_key, algorithm='ES256', headers=header)
        return encoded_jwt
    except:
        logging.error("Failed to encode JWT token")
        return False

def get_albums(kID, private_key, iss):
    storefront = 'us'
    type = 'albums'
    album_list = []

    chart_response = requests.get(f'https://api.music.apple.com/v1/catalog/{storefront}/charts?types={type}&chart=most-played',
                                  headers={"Authorization": f"Bearer  {get_jwt_token(kID, private_key, iss)}"})
    
    for i in range(len(chart_response.json()['results']['albums'][0]['data'])):
        album_name = chart_response.json()['results']['albums'][0]['data'][i]['attributes']['name']
        album_artist = chart_response.json()['results']['albums'][0]['data'][i]['attributes']['artistName']
        release_date = chart_response.json()['results']['albums'][0]['data'][i]['attributes']['releaseDate']
        key = i
        album_list.append([key, album_name, album_artist, release_date])

    
    try:
        df = pd.DataFrame(album_list, columns=['key', 'album_name', 'album_artist', 'release_date'])
        df['ingest_ts'] = datetime.datetime.now()
        return df
    except:
        logging.error("Failed to create DataFrame from album list")
        return False


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
        file_path = str(pd.to_datetime('today').date()) + '/albums_' + str(pd.to_datetime('today').date()) + '.parquet' 

    # Upload the file
    s3_client = boto3.client('s3', region_name='us-east-2')
    try:
        response = s3_client.upload_fileobj(buffer, bucket_name, file_path)
    except:
        logging.error(f"Failed to upload {file_path} to {bucket_name}/{file_path}")
        return False

def process():
    #unique identifier associated with private keys used for signing and authentication in apple developer ecosystem
    # #needed for access to the authkey file obtained from apple developer account
    # #this file is used to sign the JWT token
    ssm_client = boto3.client('ssm', region_name='us-east-2')
    private_key = ssm_client.get_parameter(
        Name='/apple/private_key',
        WithDecryption=True
    )['Parameter']['Value']

    iss = ssm_client.get_parameter(
        Name='/apple/iss',
        WithDecryption=True
    )['Parameter']['Value']

    kID = ssm_client.get_parameter(
        Name='/apple/kid',
    )['Parameter']['Value']

    df = get_albums(kID, private_key, iss)

    bucket_name = "apple-albums"

    # Upload the DataFrame to S3
    upload_df_to_s3_parquet(df, bucket_name)