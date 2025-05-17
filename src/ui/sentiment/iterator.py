from typing import Dict
import requests
from elasticsearch8 import Elasticsearch


def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()


def array_to_dict(array: [Dict], key: str) -> Dict[str, Dict]:
    d = {}
    for item in array:
        d[item[key]] = item.get("_source")

    return d


class AnalysisIterator:
    def __init__(self, client: Elasticsearch, route: str, query: str):
        self.client = client
        self.route = route
        self.query = query
        self.search_after = None
        self.results = []
        self.i = 0

    def elastic_fields(self, index: str, idField: str, textField: str, dateField: str):
        self.index = index
        self.id = idField
        self.text = textField
        self.date = dateField

    def __iter__(self):
        return self

    def addr(self):
        fission = config("FISSION_HOSTNAME")
        return f"{fission}{self.route}/index/{self.index}/field/{self.text}"

    def __next__(self):
        if self.i == len(self.results):
            response = self.client.search(
                index=self.index,
                query=self.query,
                search_after=self.search_after,
                sort=[{self.date: "asc"}, {self.id: "asc"}],
                size=1000
            )
            posts = response.get("hits").get("hits")

            if len(posts) == 0:
                raise StopIteration

            # get sentiment for posts
            analysis_query = [p.get("_id") for p in posts]
            print(f"[{self.index}] requesting {len(analysis_query)} posts")
            print(f"[{self.index}] addr {self.addr()}")
            response = requests.post(self.addr(), json=analysis_query)

            if response.status_code >= 400:
                print("error making request:", response.text)
                raise StopIteration

            # aggregate sentiment across time
            self.posts = array_to_dict(posts, "_id")
            self.results = response.json()
            self.search_after = posts[-1].get("sort")
            self.i = 0

        post_id = self.results[self.i].get("id")
        item = self.results[self.i], self.posts.get(post_id, None)
        self.i += 1
        return item
