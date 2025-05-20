#!/bin/bash

set -e

# run all tests
(
    cd tests/bluesky
    go test
)

(
    cd tests/analysis
    python test_analysis.py
)

(
    cd tests/openaus
    python test_oa.py
)

echo 'all tests passed'
