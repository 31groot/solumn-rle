#!/bin/bash
# Grader: functional (export CSV), regression (existing endpoints) and security -> /logs/verifier/{reward.txt,result.json}
mkdir -p /logs/verifier
python3 /tests/grade.py
[ -s /logs/verifier/reward.txt ] || echo 0 > /logs/verifier/reward.txt
