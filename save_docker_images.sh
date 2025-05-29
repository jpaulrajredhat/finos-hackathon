#!/bin/bash

set -e

OUTPUT_FILE="docker_images.tar"

echo "Extracting image names from docker-compose.yml..."

# Extract all image names from docker-compose
IMAGES=$(docker-compose config | awk '/image:/ { print $2 }')

if [ -z "$IMAGES" ]; then
    echo " No images found in docker-compose.yml."
    exit 1
fi

echo "Found images:"
echo "$IMAGES"

echo "Pulling all images to ensure they are present locally..."
for IMAGE in $IMAGES; do
    docker pull "$IMAGE"
done

echo "Saving all images to $OUTPUT_FILE..."
docker save -o "$OUTPUT_FILE" $IMAGES

echo "All images saved to $OUTPUT_FILE"
