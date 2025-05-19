import unittest
import json
from flask import Flask, request
from comp90024_team_57.src.tests.test_ner import main  # Replace with the actual file/module name

app = Flask(__name__)

@app.route("/test", methods=["POST"])
def test_route():
    return main()

class NamedEntityTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_named_entities(self):
        test_payload = {
            "text": "Barack Obama was born in Hawaii and worked in Washington."
        }
        response = self.client.post("/test", data=json.dumps(test_payload),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertIn("PERSON", data)
        self.assertIn("Barack Obama", data["PERSON"])
        self.assertIn("GPE", data)
        self.assertIn("Hawaii", data["GPE"])

if __name__ == "__main__":
    unittest.main()
