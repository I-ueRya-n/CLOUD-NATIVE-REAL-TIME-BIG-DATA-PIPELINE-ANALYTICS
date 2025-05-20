import unittest
import requests
from unittest.mock import patch, MagicMock
from flask import Flask

import sys
sys.path.append('./src/open_australia/oa_debates')
from oa_date_lister import main


class TestDateListerFunction(unittest.TestCase):
    debates2024 = {
        "dates": [
            "2024-02-06", "2024-02-07", "2024-02-08", "2024-02-12",
            "2024-02-13", "2024-02-15", "2024-02-26", "2024-02-27",
            "2024-02-28", "2024-02-29", "2024-03-18", "2024-03-19",
            "2024-03-20", "2024-03-21", "2024-03-25", "2024-03-26",
            "2024-03-27", "2024-05-14", "2024-05-15", "2024-05-16",
            "2024-05-28", "2024-05-29", "2024-05-30", "2024-06-03",
            "2024-06-04", "2024-06-05", "2024-06-06", "2024-06-24",
            "2024-06-25", "2024-06-26", "2024-06-27", "2024-07-02",
            "2024-07-03", "2024-07-04", "2024-08-12", "2024-08-13",
            "2024-08-14", "2024-08-15", "2024-08-19", "2024-08-20",
            "2024-08-21", "2024-08-22", "2024-09-09", "2024-09-10",
            "2024-09-11", "2024-09-12", "2024-10-08", "2024-10-09",
            "2024-10-10", "2024-11-04", "2024-11-05", "2024-11-06",
            "2024-11-07", "2024-11-18", "2024-11-19", "2024-11-20",
            "2024-11-21", "2024-11-25", "2024-11-26", "2024-11-27"
        ],
        "url": "/debates/"
    }

    def test_date_lister(self) -> None:
        """ test date lister fission function """
        url = "http://localhost:9090/openaustralia/year/2024"
        response = requests.get(url)

        # Basic checks
        self.assertEqual(response.status_code, 200, f"Expected 200 OK, got {response.status_code}")
        data = response.json()

        # Ensure it's a dict of entity types to lists of entity texts
        self.assertEqual(self.debates2024, data, "incorrect response data")

    @patch('oa_date_lister.config', return_value='http://localhost:9090')
    @patch('oa_date_lister.requests.post')
    @patch('oa_date_lister.OpenAustralia')
    def test_add_years_to_queue(self, mock_oa_cls, mock_post, mock_config):
        """ mock fission function to check for redis queue calls """
        # for getting keys and routes from the configmap
        def config_side_effect(key):
            if key == "OA_API_KEY":
                return ""
            elif key == "FISSION_HOSTNAME":
                return "http://localhost:9090"
            else:
                return None

        mock_config.side_effect = config_side_effect

        app = Flask(__name__)
        with app.app_context():
            with app.test_request_context(headers={
                "X-Fission-Params-year": "2023"
            }):
                with patch('oa_date_lister.current_app') as mock_current_app:
                    mock_current_app.logger = MagicMock()

                    mock_oa = MagicMock()
                    mock_oa_cls.return_value = mock_oa
                    # mock the OpenAustralia API response 
                    # so that it returns just this  date
                    mock_oa.get_debates.return_value = {'dates': ['2023-01-01']}

                    # make it so the redis post request returns a success
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.text = "OK"
                    mock_post.return_value = mock_response

                    result, status = main()
                    print("RESULT:", result)
                    print("STATUS:", status)

                    # response should be a dict with the dates found
                    # like {"dates": ["2023-01-01"]}
                    self.assertIsInstance(result, dict)
                    self.assertEqual(status, 200)
                    self.assertIn('dates', result)
                    self.assertEqual(result['dates'], ['2023-01-01'])

                    # check that both the senate and house of reps were added
                    # to the redis queue
                    expected_calls = [
                        unittest.mock.call(
                            url='http://localhost:9090/enqueue/oa_debate_keys',
                            headers={'Content-Type': 'application/json'},
                            json={'date': '2023-01-01', 'house': 'senate'}
                        ),
                        unittest.mock.call(
                            url='http://localhost:9090/enqueue/oa_debate_keys',
                            headers={'Content-Type': 'application/json'},
                            json={'date': '2023-01-01', 'house': 'representatives'}
                        )
                    ]
                    self.assertTrue(all(call in mock_post.call_args_list for call in expected_calls))


if __name__ == "__main__":
    unittest.main()
