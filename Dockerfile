# syntax = docker/dockerfile:1.5
FROM python:3.11

ADD . /opt/rd-usb

RUN apt-get update && apt-get install -y bluez dbus

RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    pip install -r /opt/rd-usb/requirements_headless.txt

RUN chmod +x /opt/rd-usb/docker/entrypoint.sh
ENTRYPOINT ["/opt/rd-usb/docker/entrypoint.sh"]
