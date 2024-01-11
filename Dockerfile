FROM python:3.7

ADD . /opt/rd-usb

RUN apt-get update && apt-get install -y bluez dbus

RUN pip install -r /opt/rd-usb/requirements_headless.txt

RUN chmod +x /opt/rd-usb/docker/entrypoint.sh
ENTRYPOINT ["/opt/rd-usb/docker/entrypoint.sh"]
