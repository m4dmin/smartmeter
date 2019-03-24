# smartmeter

Smartmeter
=========


Introduction
----
This project aims to query data from electric and photovoltaics meter frequently and push it to an influxDB database. 
Aditionally a docker image was created for ease of use.

Install
----
Install is easy as all docker images

```sh
docker pull m4dmin/smartmeter:latest
```

Docker-Compose
----

```sh
version: '3'
services:
  smartmeter:
    container_name: smartmeter
    image: smartmeter
    devices:
     - /dev/ttyUSB0:/dev/ttyUSB0
    volumes:
     - /etc/localtime:/etc/localtime:ro
     - /etc/timezone:/etc/timezone:ro
     - <host log directory>:/smartmeter/log
     - <host config directory>:/smartmeter/conf
    restart: unless-stopped
    network_mode: host
```

Configuration
=========

smartmeter.conf
----

```sh
[influxDB]
ipAdresse = 1.2.3.4
port = 8086
user = smartmeter-user
password = password
db = smartmeter-db
tag_instance = tag
tag_source = tag

[kostal_piko]
ipAdresse = 1.2.3.5

[serial]
port = /dev/ttyUSB0

[unload]
days = 712
delete = no
```

Notice:
Tested with Kostal Piko 7.0 Firmware 05.43

load-backup.conf
----

```sh
[influxDB]
ipAdresse = 1.2.3.4
port = 8086
user = smartmeter-user
password = password
db = smartmeter-db
tag_instance = tag
tag_source = tag

[backup]
dsn = /abc/backup/backupfile.xlsx
```