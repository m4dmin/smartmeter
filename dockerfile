FROM ubuntu:latest
MAINTAINER Mathias Lang "mathias.lang@hotmail.de"

# Install packages
RUN apt-get update \
        && apt-get -y install cron git tzdata

RUN apt-get -y install python3-pip \
        && python3 -m pip install influxdb \
        && python3 -m pip install pyserial \
        && python3 -m pip install xlsxwriter \
        && python3 -m pip install openpyxl

# Copy smartmeter git repository
RUN git clone https://github.com/m4dmin/smartmeter.git /smartmeter \
        && cd /smartmeter \
        && git checkout stable

# Add crontab
#RUN cp /smartmeter/cron/crontab /etc/cron.d/smartmeter \
#        && chmod 0644 /etc/cron.d/smartmeter \
#        && crontab /etc/cron.d/smartmeter

# Run the command on container startup
CMD ["cron", "-f"]