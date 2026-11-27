import requests
from unittest.mock import patch
from app.services.http import get_json


def response(status, data=b'{}', headers=None):
    r=requests.Response();r.status_code=status;r._content=data
    r.url='https://api.openf1.org/v1/laps';r.headers.update(headers or {})
    return r


def test_short_429_bounded_retry():
    replies=[response(429,headers={'Retry-After':'0'}),response(200,b'{"laps":2}')]
    with patch('app.services.http.requests.get',side_effect=replies) as client,patch('app.services.http.time.sleep'):
        assert get_json('https://api.openf1.org/v1/laps')=={'laps':2}
    assert client.call_count==2


def test_long_429_no_retry():
    with patch('app.services.http.requests.get',return_value=response(429,headers={'Retry-After':'60'})) as client,patch('app.services.http.time.sleep') as sleeper:
        try: get_json('https://api.openf1.org/v1/car_data');assert False
        except requests.HTTPError as exc: assert exc.response.status_code==429
    client.assert_called_once();sleeper.assert_not_called()


def test_401_no_retry():
    with patch('app.services.http.requests.get',return_value=response(401)) as client:
        try: get_json('https://api.openf1.org/v1/sessions');assert False
        except requests.HTTPError: pass
    client.assert_called_once()
