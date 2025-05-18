import json
from typing import Optional

import requests


def config(k: str) -> str:
  """Reads configuration from file."""
  with open(f'/configs/default/shared-data/{k}', 'r') as f:
      return f.read().strip()


def enqueue_data(queue_name: str, data: str) -> None:
    """Enqueues data into a Redis queue."""
    response: Optional[requests.Response] = requests.post(
      url=config("FISSION_HOSTNAME") + f'/enqueue/{queue_name}',
      headers={'Content-Type': 'application/json'},
      data=data
    )
    if response.status_code != 200:
      print(f"Failed to add {data} to redis queue: {response.text}")
      return json.dumps({"error": "Failed to add date to redis queue"}), 500
    else:
      print(f"Added {data} to redis queue {queue_name}, yay!")
