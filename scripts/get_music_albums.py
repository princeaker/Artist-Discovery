#No longer in use since the PythonOperator is preferred 
# over the python shell in Glue for the pipeline tasks
import sys
import zipfile
import os
import glob

# Find your zip manually and add to sys.path
lib_paths = glob.glob('/tmp/glue-python-libs-*/glue_deps.zip')
for lib_path in lib_paths:
    if lib_path not in sys.path:
        print(f"📌 Adding {lib_path} to sys.path")
        sys.path.insert(0, lib_path)


# Search for .zip files in sys.path and inspect contents
# for path in sys.path:
#     if path.startswith('/tmp/glue-python-libs'):
#         print(f"\n🔍 Inspecting path: {path}")
#         for files in os.listdir(path):
#             print(f"  Found file: {files}")
#             if files.endswith('.zip'):
#                 print(f"  Found zip file: {files}")
#                 zip_path = os.path.join(path, files)
#                 try:
#                     with zipfile.ZipFile(zip_path, 'r') as zip_ref:
#                         print("  Zip contents:")
#                         for f in zip_ref.namelist():
#                             print("    ", f)
#                 except Exception as e:
#                     print(f"⚠️ Could not read {zip_path}: {e}")

# Try importing jwt
try:
    import jwt
    print(f"\n✅ SUCCESS: jwt imported, version: {jwt.__version__}")
except ImportError as e:
    print(f"\n❌ FAILED: Could not import jwt: {e}")


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

    encoded_jwt = jwt.encode(claims, private_key, algorithm='ES256', headers=header)
    return encoded_jwt

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

    df = pd.DataFrame(album_list, columns=['key', 'album_name', 'album_artist', 'release_date'])
    df['ingest_ts'] = datetime.datetime.now()

    return df


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
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_fileobj(buffer, bucket_name, file_path)
    except:
        logging.error(f"Failed to upload {file_path} to {bucket_name}/{file_path}")
        return False
    return True

def process():
    #unique identifier associated with private keys used for signing and authentication in apple developer ecosystem
    # #needed for access to the authkey file obtained from apple developer account
    # #this file is used to sign the JWT token
    ssm_client = boto3.client('ssm')
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

    bucket_name = "apple_albums"

    # Upload the DataFrame to S3
    upload_df_to_s3_parquet(df, bucket_name)

process()