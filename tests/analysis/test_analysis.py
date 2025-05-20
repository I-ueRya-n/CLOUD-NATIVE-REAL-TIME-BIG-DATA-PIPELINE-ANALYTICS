import requests
import unittest


class TestAnalysis(unittest.TestCase):
    # def test_sentiment(self) -> None:
    #     self.fail("test not implemented")

    def test_ner(self) -> None:
        url = "http://localhost:9090/analysis/ner/v1"
        headers = {"Content-Type": "application/json"}
        payload = {
            "text": "Barack Obama was born in Hawaii and worked in Washington."
        }

        response = requests.post(url, json=payload, headers=headers)

        # Basic checks
        self.assertEqual(response.status_code, 200, f"Expected 200 OK, got {response.status_code}")
        
        data = response.json()

        # Ensure it's a dict of entity types to lists of entity texts
        self.assertTrue(isinstance(data, dict), "Response should be a dictionary")
        for label, entities in data.items():
            self.assertTrue(isinstance(label, str), "Entity label should be a string")
            self.assertTrue(isinstance(entities, list), f"Entities for label '{label}' should be a list")

        # Check that expected entities are present
        expected_entities = {
            "PERSON": ["Barack Obama"],
            "GPE": ["Hawaii", "Washington"]
        }

        for label, expected_list in expected_entities.items():
            self.assertTrue(label in data, f"Missing expected label: {label}")
            for entity in expected_list:
                self.assertTrue(entity in data[label], f"Expected entity '{entity}' under label '{label}'")

    def test_sentiment_fission_response(self) -> None:
        url = "http://localhost:9090/analysis/sentiment/v1"
        headers = {"Content-Type": "application/json"}
        payload = {"text": "The Liberal Party is not a party that is both good and bad !"}
        response = requests.post(url, json=payload, headers=headers)

        self.assertEqual(response.status_code, 200, f"Expected 200 OK, got {response.status_code}")

        data = response.json()
        expected_values = {'neg': 0.279, 'neu': 0.462, 'pos': 0.259, 'compound': -0.1154}

        for key, expected_value in expected_values.items():
            self.assertIn(key, data, f"Missing expected key: {key}")
            self.assertIsInstance(data[key], float, f"Expected {key} to be a float")
            self.assertAlmostEqual(data[key], expected_value, places=3,
                                   msg=f"Expected {key} ≈ {expected_value}, got {data[key]}")



if __name__ == '__main__':
    unittest.main()
