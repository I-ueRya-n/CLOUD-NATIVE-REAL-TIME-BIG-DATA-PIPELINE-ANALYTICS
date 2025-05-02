from flask import request, current_app
from typing import Dict, Any, Tuple
import requests
import logging
from datetime import datetime


def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/shared-data/{k}', 'r') as f:
        return f.read()


def main() -> Tuple[Dict[str, Any], int]:
    """Checks Elasticsearch cluster status.

    Performs:
    - Elasticsearch cluster health check

    Returns:
        tuple: (status_dict, http_code)
    """

    status = {'elasticsearch': {}}
    all_ok = True

    # Elasticsearch health check
    es_start = datetime.now()
    try:
        es_res = requests.get(
            'https://elasticsearch-master.elastic.svc.cluster.local:9200/_cluster/health',
            verify=False,
            auth=(config('ES_USERNAME'), config('ES_PASSWORD')),
            timeout=2
        )
        status['elasticsearch']['status'] = es_res.json()['status']
        status['elasticsearch']['status_code'] = es_res.status_code
        status['elasticsearch']['latency_ms'] = (datetime.now() - es_start).total_seconds() * 1000
    except Exception as e:
        current_app.logger.error(f'Elasticsearch check failed: {str(e)}')
        status['elasticsearch']['status'] = 'DOWN'
        all_ok = False

    return status, 200 if all_ok else 503
