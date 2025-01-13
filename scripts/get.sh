#!/bin/sh

set -e

VERSION=v0.0.8
BASE_URL="https://raw.githubusercontent.com/mbroton/browsy/$VERSION/quickstart"
FILES=("docker-compose.yml" "seccomp_profile.json" "jobs/screenshot.py" "jobs/pdf.py")

# Check if curl is installed
if ! command -v curl >/dev/null 2>&1; then
  echo "Error: 'curl' is not installed. Please install it and try again."
  exit 1
fi

echo "=== Browsy Quickstart ==="
echo "This script will download the required files to set up Browsy."
echo "Files will be placed in the 'browsy/' directory."
echo

# Create a target directory
TARGET_DIR="browsy"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR" || exit 1

# Download each file
for FILE in "${FILES[@]}"; do
  echo "Downloading $FILE..."
  
  # Create the directory structure for the file
  DIR=$(dirname "$FILE")
  mkdir -p "$DIR"
  
  if ! curl -fsSL "${BASE_URL}/${FILE}" -o "$FILE"; then
    echo "Error: Failed to download $FILE from ${BASE_URL}/${FILE}."
    exit 1
  fi
done

echo
echo "✅ All files have been downloaded successfully!"
echo
echo "Next steps:"
echo "1. Navigate to the 'browsy/' directory:"
echo "   cd browsy"
echo "2. Start Browsy using Docker Compose:"
echo "   docker compose up --build"
echo
echo "Enjoy using Browsy!"
