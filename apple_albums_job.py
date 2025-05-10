import requests
import boto3
import os
from dotenv import load_dotenv
import base64
import json
import datetime
import jwt
import pandas as pd
import pyarrow as pa
import logging
import pyarrow.parquet as pq
from io import BytesIO

load_dotenv()



def get_jwt_token(kID, iss, key_file_path=None):
    header = {
        "alg": "ES256",
        "kid": kID
    }
    if key_file_path is None:
        key_file_path = os.path.join(os.getcwd(), 'keys')

    with open(f'{key_file_path}/AuthKey_{kID}.p8', 'rb') as f:
        private_key = f.read()

    claims = {
        "iss": iss,  # Issuer of the token
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24), # Expiration time
        "iat": datetime.datetime.now(datetime.timezone.utc), # Issued at time

    }

    encoded_jwt = jwt.encode(claims, private_key, algorithm='ES256', headers=header)
    return encoded_jwt

def get_albums(kID, iss, key_file_path=None):
    storefront = 'us'
    type = 'albums'
    album_list = []

    chart_response = requests.get(f'https://api.music.apple.com/v1/catalog/{storefront}/charts?types={type}&chart=most-played',
                                  headers={"Authorization": f"Bearer  {get_jwt_token(kID, iss, key_file_path)}"})
    
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

def main():
    #unique identifier associated with private keys used for signing and authentication in apple developer ecosystem
    # #needed for access to the authkey file obtained from apple developer account
    # #this file is used to sign the JWT token
    kID = os.getenv("KID") 
    iss = os.getenv("ISS")

    df = get_albums(kID, iss)
    bucket_name = os.getenv("BUCKET_NAME")

    # Upload the DataFrame to S3
    upload_df_to_s3_parquet(df, bucket_name)

if __name__ == "__main__":
    main()