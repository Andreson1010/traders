#!/bin/bash
# Script to start the Trading Floor UI

cd "$(dirname "$0")"
python -m src.ui.app

