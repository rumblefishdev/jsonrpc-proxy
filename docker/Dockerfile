FROM nginx:alpine

RUN apk add -u --update py-pip && pip install awscli

ADD ./default.conf /etc/nginx/conf.d/default.conf
ADD ./entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]
