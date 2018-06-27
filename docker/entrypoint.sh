#!/bin/sh
set -ex

if [ -n "$S3_CONFIG_PATH" ]
then
    echo "Using $S3_CONFIG_PATH as proxy config"
    aws s3 cp $S3_CONFIG_PATH /etc/nginx/conf.d/default.conf
else
    echo "\$S3_CONFIG_PATH not set, using default config"
fi

nginx -g "daemon off;"
