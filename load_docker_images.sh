#!/bin/bash

set -e

INPUT_FILE="docker_images.tar"

if [ ! -f "$INPUT_FILE" ]; then
    echo "$INPUT_FILE not found."
    exit 1
fi

echo "Loading images from $INPUT_FILE..."
docker load -i "$INPUT_FILE"

echo "Images loaded successfully."
