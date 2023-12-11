import json
import boto3
from datetime import datetime
import requests
from requests_aws4auth import AWS4Auth

ES_HOST = 'https://search-photos-o6ok35wchfkb5pu2z5se66bthm.aos.us-east-2.on.aws'

def get_url(index):
    return f'{ES_HOST}/{index}/_doc'

def lambda_handler(event, context):
    print(f"EVENT --- {json.dumps(event)}")

    rek = boto3.client('rekognition')

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        print(bucket)
        print(key)
        
        labels = rek.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=10
        )
    
    print(f"IMAGE LABELS --- {labels['Labels']}")

    obj = {
        'objectKey': key,
        'bucket': bucket,
        'createdTimestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'labels': [label['Name'] for label in labels['Labels']]
    }
    
    print(f"JSON OBJECT --- {obj}")
    
    host = 'https://search-photos-o6ok35wchfkb5pu2z5se66bthm.us-east-2.es.amazonaws.com'
    url = host + '/photos/' + '_doc/' + obj['objectKey']
    headers = {'Content-Type': 'application/json'}
    session = boto3.Session()
    credentials = session.get_credentials()
    current_credentials = credentials.get_frozen_credentials()

    # Prepare the AWS authentication
    awsauth = AWS4Auth(current_credentials.access_key,
                       current_credentials.secret_key,
                       session.region_name, 'es',
                       session_token=current_credentials.token)
    
    response = requests.post(
        url, auth=awsauth, headers=headers, json=obj)
    # return response

    # url = get_url('photos')
    # response = requests.post(url, json=obj, headers={"Content-Type": "application/json"})
    
    # print(f"Success: {response}")
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(f"Response Text: {response.text}")  # Print out the response text for debugging
    else:
        print(f"Success: {response}")
    
    return {
        'statusCode': 200,
        'headers': {"Access-Control-Allow-Origin": "*", 'Content-Type': 'application/json'},
        'body': json.dumps("Image labels have been successfully detected!")
    }
