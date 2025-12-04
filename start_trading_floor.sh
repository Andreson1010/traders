#!/bin/bash
# Script to start the Trading Floor (main loop)

cd "$(dirname "$0")"
python -m src.agents.trading_floor

