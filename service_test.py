
import requests

BASE_URL = 'http://localhost:80'


def check_health():
    response = requests.get(f'{BASE_URL}/health')
    return response.json()


def get_token(username, password):
    response = requests.post(f'{BASE_URL}/token', data={
        'username': username,
        'password': password
    })
    return response.json()['access_token']


def generate_id(token):
    # use the token to generate id by hitting /generate-id
    response = requests.get(f'{BASE_URL}/generate-id', headers={
        'Authorization': f'Bearer {token}'
    })

    return response.json()['uuid']


def generate_integer_id(token):

    # use the token to generate id by hitting /generate-id
    response = requests.get(f'{BASE_URL}/generate-id-integer', headers={
        'Authorization': f'Bearer {token}'
    })

    return response.json()['id']

if __name__ == '__main__':
    print(check_health())
    token = get_token('admin', 'admin')
    print(generate_id(token))
    print(generate_integer_id(token))