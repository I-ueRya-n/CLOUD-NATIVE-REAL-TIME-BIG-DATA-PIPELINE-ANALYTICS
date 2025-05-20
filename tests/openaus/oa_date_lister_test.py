import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask

# couldnt import this directly idk how to fix it other than this sorry
import sys
sys.path.append('../comp90024_team_57/src/open_australia/oa_debates')

from oa_date_lister import main
class TestDateListerFunction(unittest.TestCase):

    @patch('oa_date_lister.config', return_value='http://localhost:9090')
    @patch('oa_date_lister.requests.post')
    @patch('oa_date_lister.OpenAustralia')
    def test_add_years_to_queue(self, mock_oa_cls, mock_post, mock_config):
        
        # for getting keys and routes from the configmap
        def config_side_effect(key):
          if key == "OA_API_KEY":
              return "literally anything we r faking it anyways"
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
