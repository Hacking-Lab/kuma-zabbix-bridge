FROM hackinglab/alpine-base-hl:3.2
LABEL maintainer="Ivan Buetler <ivan.buetler@hacking-lab.com>"

# Add the files
ADD root /

WORKDIR /opt/app

RUN apk add --no-cache ca-certificates openssl && \
    update-ca-certificates

RUN adduser -D flask && \
    chown -R flask:flask /opt/app && \
    \
    echo "**** install python ****" && \
    apk add --no-cache python3 py3-virtualenv && \
    \
    echo "**** create venv ****" && \
    python3 -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r /opt/app/requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8080
