import httpx

endpoint = 'https://api.bitbucket.org/2.0'


def test_token(username: str, token: str):
    response = httpx.get(f'{endpoint}/user', auth=(username, token))

    if response.status_code != 200:
        return False

    return True
