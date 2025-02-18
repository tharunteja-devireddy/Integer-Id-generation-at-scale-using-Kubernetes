
# Functions used to test whether the services are up and running

import requests


COORDINATOR_SERVICE_URL = 'http://localhost:5000'
ID_SERVICE_URL = 'http://localhost:8000'


def coordinator_service_health():
    response = requests.get(f'{COORDINATOR_SERVICE_URL}/health')
    return response.json()


def coordinator_service_status():
    response = requests.get(f'{COORDINATOR_SERVICE_URL}/status')
    return response.json()


def id_service_health():
    response = requests.get(f'{ID_SERVICE_URL}/health')
    return response.json()


def generate_id():
    # use the token to generate id by hitting /generate-id
    response = requests.get(f'{ID_SERVICE_URL}/generate-id')
    return response.json()['id']



if __name__ == '__main__':
    print('Coordinator Service Health  :', coordinator_service_health())
    print('Coordinator Service Status  :', coordinator_service_status())
    print('ID Service Health           :', id_service_health())
    print('Generated ID                :', generate_id())