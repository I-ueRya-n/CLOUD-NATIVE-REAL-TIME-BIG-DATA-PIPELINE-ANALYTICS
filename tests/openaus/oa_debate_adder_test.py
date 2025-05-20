import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
import sys

# couldnt import this directly idk how to fix it other than this sorry
sys.path.append('../comp90024_team_57/src/open_australia/oa_debates')
from oa_debate_adder import main

class TestDebateAdderFunction(unittest.TestCase):
    
    @patch('oa_debate_adder.config')
    @patch('oa_debate_adder.Elasticsearch')
    def test_add_debate(self, mock_es_cls, mock_config):


        # for getting keys and routes from the configmap
        def config_side_effect(key):
            if key == "ES_HOSTNAME":
              return "literally anything we r faking it anyways"
            elif key == "ES_USERNAME":
              return "woo hoo"
            elif key == "ES_PASSWORD":
                return "pass"
            else:
                return None
            
        mock_config.side_effect = config_side_effect

        app = Flask(__name__)
        with app.app_context():
            with app.test_request_context():
                with patch('oa_debate_adder.current_app') as mock_current_app, \
                    patch('oa_debate_adder.request.get_json', return_value=[{
                        "epobject_id": "2025-01-01.1.1",
                        "gid": "gid1",
                        "hdate": "2023-01-01",
                        "body": "democoracy sausages should be outlawed.",
                        "section_id": "1",  
                        "subsection_id": "1",
                        "speaker": {
                            "first_name": "Jane",
                            "last_name": "Doe",
                            "party": "Test Party",
                            "house": 1,
                            "constituency": "Victoria",
                            "person_id": "123",
                            "title": "Sir"
                        }
                    }]):

                    mock_current_app.logger = MagicMock()


                    mock_es = MagicMock()
                    # mock the es client so it says its added
                    mock_es_cls.return_value = mock_es
                    mock_es.exists.return_value = False
                    mock_es.index.return_value = {"_version": 1}

                    result, status = main()
                    print("RESULT:", result)
                    print("STATUS:", status)

                    self.assertEqual(status, 200)
                    
                    self.assertEqual(result, "added 1 debates to the index, yay!")
                    self.assertIn("added", result)

                    mock_es.index.assert_called()  

                    # check that the debate was correctly mapped into the right format
                    # and "added" to the ES index
                    mock_es.index.assert_called_once_with(
                        index="oa-debates",
                        id="2025-01-01.1.1",
                        body={
                            "id": "2025-01-01.1.1",
                            "gid": "gid1",
                            "date": "2023-01-01",
                            "parent_topic": "",
                            "transcript": "democoracy sausages should be outlawed.",
                            "speaker": {
                                "first_name": "Jane",
                                "last_name": "Doe",
                                "party": "Test Party",
                                "house": 1,
                                "state": "Victoria",
                                "person_id": "123",
                                "position": "Sir"
                            }
                        }
                    )
