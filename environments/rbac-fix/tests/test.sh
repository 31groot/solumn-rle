#!/bin/bash
# Grader: functional (held-out cases), regression and security checks -> /logs/verifier/{reward.txt,result.json}
mkdir -p /logs/verifier
python3 /tests/grade.py
[ -s /logs/verifier/reward.txt ] || echo 0 > /logs/verifier/reward.txt
