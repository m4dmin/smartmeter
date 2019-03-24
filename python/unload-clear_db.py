#!/usr/bin/env python3

import time
import datetime
import configparser
import logging
from logging.handlers import RotatingFileHandler
import sys
from influxdb import InfluxDBClient
import time

import json
import xlsxwriter


############### init section ###############

##### config section
config = configparser.ConfigParser()
config.read('/smartmeter/conf/smartmeter.conf')

influxDB_ip = config['influxDB']['ipAdresse']
influxDB_port = config['influxDB']['port']
influxDB_user = config['influxDB']['user']
influxDB_passwd = config['influxDB']['password']
influxDB_db = config['influxDB']['db']
influxDB_tag_instance = config['influxDB']['tag_instance']
influxDB_tag_source = config['influxDB']['tag_source']

days = config['unload']['days']
delete = config['unload']['delete']

##### measurement section

msmntDict = {"sz_leistung_aktuell": "W",
             "pv_leistung_aktuell": "W",
             "verbrauch_aktuell": "W",
             "sz_tariflos_1.8.0": "kWh",
             "sz_hochtarif_1.8.1": "kWh",
             "sz_niedertarif_1.8.2": "kWh",
             "sz_einspeisen_tariflos_2.8.0": "kWh",
             "sz_einspeisen_hochtarif_2.8.1": "kWh",
             "sz_einspeisen_niedertarif_2.8.2": "kWh",
             "pv_ertrag_tag": "kWh",
             "einspiesen_tag": "kWh",
             "bezug_tag": "kWh",
             "pv_eigenvergrauch_tag": "kWh",
             "verbrauch_tag": "kWh"
            }   

############### logging section ###############
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a file handler
handler = RotatingFileHandler('/smartmeter/log/smartmeter.log', maxBytes=10*1024*1024, backupCount=2)
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

# logging examples
# logger.debug("Debug Log")
# logger.info("Info Log")
# logger.warning("Warning Log")
# logger.error("Error Log")
# logger.critical("Critical Log")


############### Runtime section ##################

# Excel Workbook oeffnen
try:
    logger.info("Starte Abzug DB "+influxDB_db+", Instanz "+influxDB_tag_instance+", Source "+influxDB_tag_instance)
    logger.info("Loeschen der Daten aktiv: "+str(delete))
    workbook = xlsxwriter.Workbook('/smartmeter/backup/'+str(time.strftime("%Y-%m-%d_%H-%M-%S"))+'.xlsx')
except Exception as e:
    logger.error(e)
    sys.exit(1)

for msmnt, unit in msmntDict.items():
    # Daten aus influxDB herauslesen
    try:
        clientInfluxDB = InfluxDBClient(influxDB_ip, influxDB_port, influxDB_user, influxDB_passwd, influxDB_db)
        query = 'SELECT "'+str(unit)+'" FROM "'+str(msmnt)+'" WHERE time <= now()-'+str(days)+'d ORDER BY time;'
        logger.debug(query)
        result = clientInfluxDB.query(query)
        resultList = list(result.get_points(measurement=str(msmnt)))
        logger.info("Anzahl Datensaetze "+str(msmnt)+": "+str(len(resultList)))
    except Exception as e:
        logger.error(e)
        sys.exit(1)

    # Daten aus influxDB in Excel ablegen
    if len(resultList) >= 1:
        try:
            worksheet = workbook.add_worksheet(str(msmnt))
            worksheet.write(0, 0, "Time")
            worksheet.write(0, 1, "Value")
            row = 1
            for result in resultList:
                resultJson = json.loads(str(result).replace("'",'"'))
                logger.debug(resultJson)
                for key, value in resultJson.items():
                    if key == str(unit):
                        logger.debug(str(unit)+": "+str(value))
                        worksheet.write(row, 1, str(value))
                    if key == "time":
                        logger.debug("time: "+str(value))
                        worksheet.write(row, 0, str(value))
                row += 1
        except Exception as e:
            logger.error(e)
            sys.exit(1)

    if delete == "yes":
        try:
            query = 'DELETE FROM "'+str(msmnt)+'" WHERE time <= now()-'+str(days)+'d;'
            logger.debug(query)
            logger.info("Datensaetze aus "+str(msmnt)+" geloescht")
            result = clientInfluxDB.query(query)
        except Exception as e:
            logger.error(e)
            sys.exit(1)

# Excel Workbook schießen
try:
    logger.info("Beende Abzug")
    workbook.close()
except Exception as e:
    logger.error(e)
    sys.exit(1)

