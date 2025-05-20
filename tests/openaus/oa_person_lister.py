import unittest
import requests


class TestPersonLister(unittest.TestCase):
    person2024 = {
        "constituency": "SA",
        "entered_house": "2007-05-03",
        "entered_reason": "unknown",
        "first_name": "Simon",
        "full_name": "Simon Birmingham",
        "house": "2",
        "image": "/images/mpsL/10044.jpg",
        "last_name": "Birmingham",
        "lastupdate": "2025-03-31 04:51:47",
        "left_house": "2025-01-28",
        "left_reason": "resigned",
        "member_id": "100014",
        "name": "Simon Birmingham",
        "office": [
            {
                "dept": "",
                "from_date": "2022-06-05",
                "moffice_id": "215684",
                "person": "10044",
                "position": "Shadow Minister for Foreign Affairs",
                "source": "",
                "to_date": "9999-12-31"
            },
            {
                "dept": "",
                "from_date": "2022-06-05",
                "moffice_id": "215685",
                "person": "10044",
                "position": "Leader of the Opposition in the Senate",
                "source": "",
                "to_date": "9999-12-31"
            }
        ],
        "party": "Liberal Party",
        "person_id": "10044",
        "title": ""
    }

    def test_person(self) -> None:
        """ test person lister fission function """
        url = "http://localhost:9090/openaustralia/list-people/year/2024/house/senate"
        response = requests.get(url)

        # Basic checks
        self.assertEqual(response.status_code, 200, f"Expected 200 OK, got {response.status_code}")
        data = response.json()

        # Ensure it's a dict of entity types to lists of entity texts
        self.assertEqual(self.person2024, data, "incorrect response data")


if __name__ == '__main__':
    unittest.main()
