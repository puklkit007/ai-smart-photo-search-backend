import json
import boto3
import http.client
import urllib.parse
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import base64


region = 'us-east-2'
service = 'es'
s3_client = boto3.client('s3', region_name=region)
rekognition = boto3.client('rekognition', region_name=region)

# Elasticsearch domain 
es_host = 'search-photos-o6ok35wchfkb5pu2z5se66bthm.us-east-2.es.amazonaws.com' 
# Elasticsearch credentials
es_username = 'pulkit'
es_password = 'Qwerty@007'

def get_signed_request(method, url, service, region, body=None):
    headers = {'Content-Type': 'application/json'}
    request = AWSRequest(method=method, url=url, data=body, headers=headers)
    SigV4Auth(boto3.Session().get_credentials(), service, region).add_auth(request)
    return request

def lambda_handler(event, context):
    # Extract bucket name and file key from the event
    print("Received event:", json.dumps(event))
    print("hello")
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    try:
        # Detect labels in the image
        response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=10
        )
        print("response from reko")
        print(response)

        # Get metadata from S3 object
        metadata_response = s3_client.head_object(Bucket=bucket, Key=key)
        # print("response from metadata")
        # print(metadata_response)

        custom_labels = metadata_response['Metadata'].get('customlabels', '[]')
        
        custom_labels = [label.strip() for label in custom_labels.split(',') if label.strip()]
        
        labels = [label['Name'] for label in response['Labels']]
        all_labels = labels + custom_labels
        
        print("all_labels")
        print(all_labels)

        es_json = json.dumps({
            "objectKey": key,
            "bucket": bucket,
            "createdTimestamp": metadata_response['LastModified'].strftime('%Y-%m-%dT%H:%M:%S'),
            "labels": all_labels
        })

        es_url = f'https://{es_host}/photos/_doc/'
        # Encode credentials for Basic Auth
        credentials = f'{es_username}:{es_password}'
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        # Set up headers with Basic Auth
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }

        signed_request = get_signed_request('POST', es_url, 'es', region, body=es_json)

        # Make the HTTP request to Elasticsearch
        connection = http.client.HTTPSConnection(es_host)
        connection.request(method='POST', url=es_url, body=es_json, headers=headers)
        response = connection.getresponse()
        print("response from es ")
        print(response)
        response_body = response.read().decode()
        print("Response Status Code:", response.status)
        print("Response Body:", response_body)

        return {
            'statusCode': 200,
            'headers': {"Access-Control-Allow-Origin": "*", 'Content-Type': 'application/json',
                        "Access-Control-Allow-Headers": '*', "Access-Control-Allow-Methods": '*'
                },
            'body': json.dumps(f'Successfully indexed photo. Response: {response.read().decode()}')
        }

    except Exception as e:
        print("Error: ", e)
        raise e
