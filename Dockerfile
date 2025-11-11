FROM debian:trixie

EXPOSE 9000

ENV RELEASE=stretch \
    LANGUAGE=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    WEBHOOK_VERSION=2.6.8

RUN apt-get update \
  && apt-get install -y make python3 python3-requests python3-yaml python3-pip \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY snow-hook.json /etc/webhook/snow-hook.json
COPY snow-hook.py /snow-hook.py

# Install webhook
RUN apt-get update \
    && apt-get install -y wget \
    && wget https://github.com/adnanh/webhook/releases/download/${WEBHOOK_VERSION}/webhook-linux-amd64.tar.gz \
    && tar xzf webhook-linux-amd64.tar.gz \
    && mv webhook-linux-amd64/webhook /usr/local/bin/webhook \
    && rm -f webhook-linux-amd64.tar.gz \
    && apt-get remove -y --purge wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY /docker-entrypoint.d/* /docker-entrypoint.d/

ENTRYPOINT ["/docker-entrypoint.sh"]
