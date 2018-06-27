FROM nginx:alpine

RUN apk add -u --update py-pip && pip install awscli

ADD ./entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]
