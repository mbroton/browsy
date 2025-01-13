#!/bin/bash

set -e

cd ../../

echo "==> Building browsy package..."
rm -rf dist
uv build --all

echo "==> Copying browsy package to local env..."
for dir in server worker; do
    cp dist/browsy-*.whl tests/local_env/images/$dir/
    mv tests/local_env/images/$dir/browsy-*.whl tests/local_env/images/$dir/browsy.whl
done

echo "==> Building server image..."
cd tests/local_env/images/server
docker build -t browsy-server-local .

echo "==> Building worker image..."
cd ../worker
docker build -t browsy-worker-local .
