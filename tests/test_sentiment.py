import requests
from config import URL

def test_sentiment_fission_response():
    url = f"{URL}/analysis/ner/v1"
    headers = {"Content-Type": "application/json"}
    payload = {"text": "The Liberal Party is not a party that is both good and bad !"}
    response = requests.post(url, json=payload, headers=headers)

    # Basic checks
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    data = response.json()

    # Check that expected entities are present
    expected_values = {'neg': 0.279, 'neu': 0.462, 'pos': 0.259, 'compound': -0.1154}

    for key, expected_value in expected_values.items():
        assert key in data, f"Missing expected key: {key}"
        assert isinstance(data[key], float), f"Expected {key} to be a float"
        assert abs(data[key] - expected_value) < 0.001, f"Expected {key} to be close to {expected_value}, got {data[key]}"