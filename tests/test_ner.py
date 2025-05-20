import requests
from config import URL

def test_ner_fission_response():
    url = f"{URL}/analysis/ner/v1"
    headers = {"Content-Type": "application/json"}
    payload = {
        "text": "Barack Obama was born in Hawaii and worked in Washington."
    }

    response = requests.post(url, json=payload, headers=headers)

    # Basic checks
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    data = response.json()

    # Ensure it's a dict of entity types to lists of entity texts
    assert isinstance(data, dict), "Response should be a dictionary"
    for label, entities in data.items():
        assert isinstance(label, str), "Entity label should be a string"
        assert isinstance(entities, list), f"Entities for label '{label}' should be a list"

    # Check that expected entities are present
    expected_entities = {
        "PERSON": ["Barack Obama"],
        "GPE": ["Hawaii", "Washington"]
    }

    for label, expected_list in expected_entities.items():
        assert label in data, f"Missing expected label: {label}"
        for entity in expected_list:
            assert entity in data[label], f"Expected entity '{entity}' under label '{label}'"
