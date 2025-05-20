import unittest
from unittest.mock import patch, MagicMock
from oa_debate_harvester_by_details import main 

class TestMainFunction(unittest.TestCase):

    @patch('oa_debate_harvester_by_details.requests.post')
    @patch('oa_debate_harvester_by_details.OpenAustralia')
    @patch('oa_debate_harvester_by_details.request')
    @patch('oa_debate_harvester_by_details.current_app')
    @patch('oa_debate_harvester_by_details.config', return_value='http://localhost:9090')

    def test_main_valid_date(self, mock_app, mock_request, mock_oa_cls, mock_post):
        print("Running OA test")

        #  mock request JSON
        mock_request.get_json.return_value = {
            "house": "senate",
            "date": "2023-01-01"
        }

        mock_oa = MagicMock()
        mock_oa_cls.return_value = mock_oa
        
        # mock a single debate with one gid and matching detail
        mock_oa.get_debates.side_effect = [
            [{"gid": "abc123"}],  # Initial page fetch
            [{"gid": "abc123"}],  # Fetch debate details
        ]

        # Setup response mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Run
        result, status = main()

        # Assert
        self.assertEqual(status, 200)
        self.assertEqual(result['house'], 'complete')
        mock_post.assert_called()  # Ensure it attempted to post to the Redis queue

if __name__ == "__main__":
    unittest.main()
