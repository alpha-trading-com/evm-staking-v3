import requests
import random

API_KEYS = [
    "tao-b8889cc3-5939-4172-a583-f5ab92f360e2:ab165d16",
    "tao-2a55e490-87a1-4ec6-835f-8588738a2089:3697cbf5",
    "tao-b293e92e-0436-46b8-a2e8-fab155a79cc2:4dc98b99",
    "tao-153304be-2afa-49d1-aaad-44dc05c3c849:a757860b",
    "tao-27ecfd3c-6b36-4f1a-be93-cd07f93ebc26:d8ac816a",
    "tao-696cb5af-69cc-4a96-b4e8-24090a5eef34:febe8a0a",
    "tao-745f7c12-858a-465f-a494-170cb885a055:26beb1be",
    "tao-ce470076-a904-4f71-b297-cfa9e230cd6e:b20a1eed",
    "tao-cccad295-c992-40b4-b026-ae279a3818c5:0a8532d7",
    "tao-375863cd-787a-4830-98d3-dff4b2bba920:ec80a31b",
    "tao-f42dc122-f0b6-47f4-9de3-8fc2432db960:8aa65ac6",
    "tao-f4d57aef-af83-469d-9b8e-e81acda39191:e7e7babf",
    "tao-925fc4d1-5ef9-4290-9bad-33a743938d4d:3026199b",
    "tao-011a9e61-42cc-4989-b0c7-b2570075a149:06670d32",
    "tao-ec2a4a5c-ce0b-4b80-84a3-7083f97ebe0d:3fd3aa9e",
]

def get_random_api_key():
    return random.choice(API_KEYS)

def get_subnet_history(block_number):

    url = f"https://api.taostats.io/api/dtao/pool/history/v1?frequency=by_block&block_number={block_number}&page=1&limit=200"

    headers = {
        "accept": "application/json",
        "Authorization": get_random_api_key()
    }

    response = requests.get(url, headers=headers)

    result = response.json()
    subnets = result["data"]
    return subnets
