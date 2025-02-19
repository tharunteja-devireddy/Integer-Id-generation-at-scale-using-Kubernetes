
# Functions used to test whether the services are up and running

import requests


ID_SERVICE_URL = 'http://localhost:8000' # on local
# ID_SERVICE_URL = 'http://localhost:80'   # on kubernetes


def id_service_health():
    response = requests.get(f'{ID_SERVICE_URL}/health')
    return response.json()


def generate_id():
    # use the token to generate id by hitting /generate-id
    response = requests.get(f'{ID_SERVICE_URL}/generate-id')
    return response.json()['id']



if __name__ == '__main__':
    print('ID Service Health           :', id_service_health())
    print('Generated ID                :', generate_id())