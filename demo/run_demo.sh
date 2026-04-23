#!/bin/bash
set -e

rm -f kelp.yaml

echo ""
echo "$ pip install agentcloudkelp"
sleep 1
echo "Successfully installed agentcloudkelp-0.1.2"
sleep 0.5
echo ""
echo "$ kelp init"
sleep 0.5
kelp init
sleep 1
echo ""
echo "$ kelp run -f function"
sleep 0.5
kelp run -f function
sleep 2
