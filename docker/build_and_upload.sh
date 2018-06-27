#!/usr/bin/env sh

require() {
    command -v "$1" > /dev/null 2>&1 || {
        echo "Some of the required software is not installed:"
        echo "    please install $1" >&2;
        exit 4;
    }
}

get_url() {
    REPO_NAME=$1
    OUT=$(aws ecr describe-repositories --repository-name=$REPO_NAME 2> /dev/null || echo "{}")
    echo $OUT | jq -r ".repositories[0].repositoryUri"
}

create_repo() {
    REPO_NAME=$1
    echo "Creating ECR repository $REPO_NAME"
    aws ecr create-repository --repository-name $REPO_NAME
}

build_and_upload () {
    echo "Building docker image for tag $1"
    docker build --pull -t $1 $2
    docker push $1
}


set -e
require jq
require aws

REPO_NAME=${1-jsonrpc-proxy}
REPO_URL=$(get_url $REPO_NAME)
if [ $REPO_URL == "null" ]; then
    create_repo $REPO_NAME
    REPO_URL=$(get_url $REPO_NAME)
    if [ $REPO_URL == "null" ]; then
        echo "Failed to create repository $REPO_NAME"; exit 4
    fi
fi

BUILD_PATH=.
`aws ecr get-login --no-include-email`
build_and_upload $REPO_URL:latest $BUILD_PATH
