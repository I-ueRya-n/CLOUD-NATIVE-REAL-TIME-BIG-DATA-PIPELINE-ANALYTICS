#!/bin/bash

set -e

# run all tests
(
    echo 'Testing Bluesky'
    cd tests/bluesky
    go test
)

(
    echo 'Testing Analysis'
    cd tests/analysis
    python test_analysis.py
)

(
    echo 'Testing Open Australia'
    python tests/openaus/oa_date_lister_test.py
    python tests/openaus/oa_person_lister.py
    python tests/openaus/oa_debate_adder_test.py
)

echo 'all tests passed'
