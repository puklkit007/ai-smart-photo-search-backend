import json
import boto3
import os
import sys
import uuid
import time
import requests
from requests_aws4auth import AWS4Auth


ES_HOST = 'https://search-photos-o6ok35wchfkb5pu2z5se66bthm.aos.us-east-2.on.aws'
REGION = 'us-east-1'
index = 'photos'

url = ES_HOST + '/' + index + '/_search'

def lambda_handler(event, context):
    # receive from API Gateway
    print("EVENT --- {}".format(json.dumps(event)))
    
    headers = { "Content-Type": "application/json" }
    lex = boto3.client('lexv2-runtime', region_name=REGION)

    query_text = event["queryStringParameters"]["q"]
    print("query text: ", query_text)
    
    lexresponse = lex.recognize_text(
                    botId='NGDMKDTYVL',
                    botAliasId='TSTALIASID',
        			localeId='en_US',
                    sessionId="test_session",
                    text=query_text)
        
    print('lexresponse: ', lexresponse)

    if lexresponse['sessionState']['intent']['slots'] == {}:
        res_ = query_text
    else:
        slots = lexresponse['sessionState']['intent']['slots']
        tag_a_value = slots['tag_a']['value']['originalValue'] if slots['tag_a'] is not None else None
        tag_b_value = slots['tag_b']['value']['originalValue'] if slots['tag_b'] is not None else None

    key_word_list = []
    if tag_a_value:
        key_word_list.append(tag_a_value)
    if tag_b_value:
        key_word_list.append(tag_b_value)
    print('lexresponse slot key word', key_word_list)


    headers = {"Content-Type": "application/json"}

    # Create the response and add some extra content to support CORS
    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": '*',
            "Access-Control-Allow-Headers": '*',
            "Access-Control-Allow-Methods": '*'
        },
    }
    
    session = boto3.Session()
    credentials = session.get_credentials()
    current_credentials = credentials.get_frozen_credentials()

    # Prepare the AWS authentication
    awsauth = AWS4Auth(current_credentials.access_key,
                       current_credentials.secret_key,
                       session.region_name, 'es',
                       session_token=current_credentials.token)
    
    final_url_list = []

    for term in key_word_list:
        url_list = []
        query = {"query": {
            "bool": {
                "must": [
                    {"fuzzy": {
                        "labels": {
                            "value": term}
                    }
                    }
                ]
            }
        },
            "size": 10}
            
        

        # Make the signed HTTP request
        r = requests.get(url, auth=awsauth,
                         headers=headers, data=json.dumps(query))

        print("es response", r.text)
        posts_list = json.loads(r.text)['hits']['hits']
        

        url_list = ['https://' + str(x["_source"]["bucket"]) + '.s3.us-east-2.amazonaws.com/' + str(x["_source"]["objectKey"]) for x in posts_list]

        final_url_list += url_list
    
    final_url_list = list(set(final_url_list))
    print("final url list:", final_url_list)
    response['body'] = json.dumps(final_url_list)

    return response
