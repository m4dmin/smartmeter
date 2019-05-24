#!/usr/bin/env python3

import time
import datetime
import configparser
import logging
from logging.handlers import RotatingFileHandler
import serial
import requests
import sys
import json
from influxdb import InfluxDBClient


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

serial_port = config['serial']['port']
serial_baud = "300"

piko_ipAdresse = config['kostal_piko']['ipAdresse']

##### Array with JSON data for influxDB write
points = []

##### Stromzaehler section
# Zaehler Werte
sz_geraetenummer = "C.1.0"
sz_tarif_program = "C.1.1"
sz_zaehlernummer = "0.0"
sz_firmware_version = "0.2.0"
sz_firmware_checksumme = "0.2.8"
# Status
sz_fehler = "F.F"
sz_statuscode = "C.5.0"
# Leistungswerte
sz_zaehler_tariflos = "1.8.0"               # in kWh
sz_zaehler_hochtarif = "1.8.1"              # in kWh
sz_zaehler_niedertarif = "1.8.2"            # in kWh
sz_zaehler_einspeisen_tariflos = "2.8.0"    # in kWh
sz_zaehler_einspeisen_hochtarif = "2.8.1"   # in kWh
sz_zaehler_einspeisen_niedertarif = "2.8.2" # in kWh
sz_zaehler_gesamt = "15.8.0"                # in kWh (1.8.0 + 2.8.0 - immer positiv)
sz_spannung_l1 = "32.7"                     # in V
sz_spannung_l2 = "52.7"                     # in V
sz_spannung_l3 = "72.7"                     # in V
sz_stromfluss_l1 = "31.7"                   # in A
sz_stromfluss_l2 = "51.7"                   # in A
sz_stromfluss_l3 = "71.7"                   # in A
sz_leistung_aktuell = "16.7"                # in kW
sz_zaehler_spannungsausfall = "C.7.0"

##### Kostal Piko PV Wechselrichter section

# Leistungswerte
piko_id_DCEingangGesamt = 33556736          # in W
piko_id_Ausgangsleistung = 67109120         # in W
piko_id_Eigenverbrauch = 83888128           # in W
# Status
piko_id_Status = 16780032                   # 0 = Off
                                            # 1 = Leerlauf
                                            # 2 = Anfahren
                                            # 3 = Einspeisen MPP
                                            # 4 = abgeregelt
                                            # 5 = Einspeisen
                                            # 6 = ??
                                            # 7 = ??
                                            # 8 = ??
# Statistik - Tag
piko_id_Ertrag_d = 251658754                # in Wh
piko_id_Hausverbrauch_d = 251659010         # in Wh
piko_id_Eigenverbrauch_d = 251659266        # in Wh
piko_id_Eigenverbrauchsquote_d = 251659278  # in %
piko_id_Autarkiegrad_d = 251659279          # in %
# Statistik - Gesamt
piko_id_Ertrag_G = 251658753                # in kWh
piko_id_Hausverbrauch_G = 251659009         # in kWh
piko_id_Eigenverbrauch_G = 251659265        # in kWh
piko_id_Eigenverbrauchsquote_G = 251659280  # in %
piko_id_Autarkiegrad_G = 251659281          # in %
piko_id_Betriebszeit = 251658496            # in h
# Momentanwerte - PV Genertor
piko_id_DC1Spannung = 33555202              # in V
piko_id_DC1Strom = 33555201                 # in A
piko_id_DC1Leistung = 33555203              # in W
piko_id_DC2Spannung = 33555458              # in V
piko_id_DC2Strom = 33555457                 # in A
piko_id_DC2Leistung = 33555459              # in W
# Momentanwerte Haus
piko_id_HausverbrauchSolar = 83886336       # in W
piko_id_HausverbrauchBatterie = 83886592    # in W
piko_id_HausverbrauchNetz = 83886848        # in W
piko_id_HausverbrauchPhase1 = 83887106      # in W
piko_id_HausverbrauchPhase2 = 83887362      # in W
piko_id_HausverbrauchPhase3 = 83887618      # in W
# Netz Netzparameter
piko_id_NetzAusgangLeistung = 67109120      # in W
piko_id_NetzFrequenz = 67110400             # in Hz
piko_id_NetzCosPhi = 67110656
# Netz Phase 1
piko_id_P1Spannung = 67109378               # in V
piko_id_P1Strom = 67109377                  # in A
piko_id_P1Leistung = 67109379               # in W
# Netz Phase 2
piko_id_P2Spannung = 67109634               # in V
piko_id_P2Strom = 67109633                  # in A
piko_id_P2Leistung = 67109635               # in W
# Netz Phase 3
piko_id_P3Spannung = 67109890               # in V
piko_id_P3Strom = 67109889                  # in A
piko_id_P3Leistung = 67109891               # in W


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

#### SZ section
ser = serial.Serial(serial_port, serial_baud, parity=serial.PARITY_ODD)
ser.bytesize = serial.SEVENBITS             # number of bits per bytes
ser.parity = serial.PARITY_EVEN             # set parity check: no parity
ser.stopbits = serial.STOPBITS_ONE          # number of stop bits
#ser.timeout = None                         # block read
#ser.timeout = 0                            # non-block read
ser.timeout = 5                             # timeout block read
ser.xonxoff = False                         # disable software flow control
ser.rtscts = False                          # disable hardware (RTS/CTS) flow control
ser.dsrdtr = False                          # disable hardware (DSR/DTR) flow control
ser.writeTimeout = 0                        # timeout for write


try:
    ser.open()
except Exception as e:
    logger.debug(e)

try:
    logger.debug("Sende Initiaslisierungssequenz")
    ser.write(b'\x2F\x3F\x21\x0D\x0A')
    time.sleep(0.5)
    responseByte = ser.readline()
    logger.debug(responseByte)
    logger.debug("Sende Acksequenz")
    ser.write(b'\x06\x30\x30\x30\x0D\x0A')

    numberOfLine = 0
    while True:
        numberOfLine = numberOfLine + 1
        logger.debug("Zeile "+str(numberOfLine)+" einlesen")
        sz_responseByte = ser.readline()
        logger.debug(sz_responseByte)
        sz_responseString = sz_responseByte.decode("utf-8").rstrip('\r\n')

        # sz_zaehler_tariflos (1.8.0)
        if sz_responseString[0:len(sz_zaehler_tariflos)] == sz_zaehler_tariflos:
            sz_responseStripped = sz_responseString.replace(sz_zaehler_tariflos,"")
            sz_responseStripped = sz_responseStripped.replace("(","")
            sz_responseStripped = sz_responseStripped.replace("*kWh)","")
            sz_zaehler_tariflos_kWh = float(sz_responseStripped)
            logger.info("SZ Zaehler tariflos 1.8.0: "+sz_responseStripped)
            point = {
                "measurement": 'sz_tariflos_1.8.0',
                "tags": {
                    "instance": influxDB_tag_instance,
                    "source": influxDB_tag_source
                },
                #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
                "fields": {
                    "kWh": str(float(sz_responseStripped))
                    }
                }
            points.append(point)

        # sz_zaehler_hochtarif (1.8.1)
        if sz_responseString[0:len(sz_zaehler_hochtarif)] == sz_zaehler_hochtarif:
            sz_responseStripped = sz_responseString.replace(sz_zaehler_hochtarif,"")
            sz_responseStripped = sz_responseStripped.replace("(","")
            sz_responseStripped = sz_responseStripped.replace("*kWh)","")
            logger.info("SZ Zaehler hochtarif 1.8.1: "+sz_responseStripped)
            point = {
                "measurement": 'sz_hochtarif_1.8.1',
                "tags": {
                    "instance": influxDB_tag_instance,
                    "source": influxDB_tag_source
                },
                #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
                "fields": {
                    "kWh": str(float(sz_responseStripped))
                    }
                }
            points.append(point)

        # sz_zaehler_niedertarif (1.8.2)
        if sz_responseString[0:len(sz_zaehler_niedertarif)] == sz_zaehler_niedertarif:
            sz_responseStripped = sz_responseString.replace(sz_zaehler_niedertarif,"")
            sz_responseStripped = sz_responseStripped.replace("(","")
            sz_responseStripped = sz_responseStripped.replace("*kWh)","")
            logger.info("SZ Zaehler niedertarif 1.8.2: "+sz_responseStripped)
            point = {
                "measurement": 'sz_niedertarif_1.8.2',
                "tags": {
                    "instance": influxDB_tag_instance,
                    "source": influxDB_tag_source
                },
                #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
                "fields": {
                    "kWh": str(float(sz_responseStripped))
                    }
                }
            points.append(point)

        # sz_zaehler_einspeisen_tariflos (2.8.0)
        if sz_responseString[0:len(sz_zaehler_einspeisen_tariflos)] == sz_zaehler_einspeisen_tariflos:
            sz_responseStripped = sz_responseString.replace(sz_zaehler_einspeisen_tariflos,"")
            sz_responseStripped = sz_responseStripped.replace("(","")
            sz_responseStripped = sz_responseStripped.replace("*kWh)","")
            sz_zaehler_einspeisen_tariflos_kWh = float(sz_responseStripped)
            logger.info("SZ Zaehler einspeisen tariflos 2.8.0: "+sz_responseStripped)
            point = {
                "measurement": 'sz_einspeisen_tariflos_2.8.0',
                "tags": {
                    "instance": influxDB_tag_instance,
                    "source": influxDB_tag_source
                },
                #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
                "fields": {
                    "kWh": str(float(sz_responseStripped))
                    }
                }
            points.append(point)

        # sz_zaehler_einspeisen_hochtarif (2.8.1)
        if sz_responseString[0:len(sz_zaehler_einspeisen_hochtarif)] == sz_zaehler_einspeisen_hochtarif:
            sz_responseStripped = sz_responseString.replace(sz_zaehler_einspeisen_hochtarif,"")
            sz_responseStripped = sz_responseStripped.replace("(","")
            sz_responseStripped = sz_responseStripped.replace("*kWh)","")
            logger.info("SZ Zaehler einspeisen hochtarif 2.8.1: "+sz_responseStripped)
            point = {
                "measurement": 'sz_einspeisen_hochtarif_2.8.1',
                "tags": {
                    "instance": influxDB_tag_instance,
                    "source": influxDB_tag_source
                },
                #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
                "fields": {
                    "kWh": str(float(sz_responseStripped))
                    }
                }
            points.append(point)

        # sz_zaehler_einspeisen_niedertarif (2.8.2)
        if sz_responseString[0:len(sz_zaehler_einspeisen_niedertarif)] == sz_zaehler_einspeisen_niedertarif:
            sz_responseStripped = sz_responseString.replace(sz_zaehler_einspeisen_niedertarif,"")
            sz_responseStripped = sz_responseStripped.replace("(","")
            sz_responseStripped = sz_responseStripped.replace("*kWh)","")
            logger.info("SZ Zaehler einspeisen niedertarif 2.8.2: "+sz_responseStripped)
            point = {
                "measurement": 'sz_einspeisen_niedertarif_2.8.2',
                "tags": {
                    "instance": influxDB_tag_instance,
                    "source": influxDB_tag_source
                },
                #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
                "fields": {
                    "kWh": str(float(sz_responseStripped))
                    }
                }
            points.append(point)

        if (numberOfLine >= 24):
            break
except Exception as e:
    logger.error(e)
    ser.close()
    sys.exit(1)

try:
    ser.close()
except Exception as e:
    logger.error(e)
    sys.exit(1)

#### PV section

# JSON params for PV API request
params = (
    ('dxsEntries', [piko_id_Ertrag_d]),
    ('sessionId', '3378188426'),
)

# get data from PV API
try:
    logger.debug('http://'+piko_ipAdresse+'/api/dxs.json')
    pv_responseRequest = requests.get('http://'+piko_ipAdresse+'/api/dxs.json', params=params)
except requests.exceptions.RequestException as e:
    logger.error(e)
    sys.exit(1)
logger.debug(pv_responseRequest.content)

pv_responseByte = pv_responseRequest.content
pv_responseString = pv_responseByte.decode("utf-8")
pv_responseJson = json.loads(pv_responseString)
logger.debug(pv_responseJson)

# exploit data values from PV API response
for dxsId in pv_responseJson["dxsEntries"]:
    logger.debug(dxsId)
    pv_ertrag_tag_kWh = float(dxsId["value"])/1000

    if dxsId["dxsId"] == piko_id_Ertrag_d:
        logger.info("PV Ertrag Tag: "+str(dxsId["value"]))
        point = {
            "measurement": 'pv_ertrag_tag',
            "tags": {
                "instance": influxDB_tag_instance,
                "source": influxDB_tag_source
            },
            #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
            "fields": {
                "kWh": pv_ertrag_tag_kWh
                }
            }
        points.append(point)

# Daten von gestern aus influxdb herauslesen
try:
    clientInfluxDB = InfluxDBClient(influxDB_ip, influxDB_port, influxDB_user, influxDB_passwd, influxDB_db)
    query = 'SELECT "kWh" FROM "sz_tariflos_1.8.0" ORDER BY time DESC LIMIT 1;'
    sz_result = clientInfluxDB.query(query)
    logger.debug(sz_result)
    sz_resultList = list(sz_result.get_points(measurement='sz_tariflos_1.8.0'))
    sz_resultDict = sz_resultList[0]
    sz_zaehler_tariflos_kWh_gestern = float(sz_resultDict['kWh'])
    logger.info("SZ Zaehler tariflos 1.8.0 gestern: "+str(sz_zaehler_tariflos_kWh_gestern))
        
    query = 'SELECT "kWh" FROM "sz_einspeisen_tariflos_2.8.0" ORDER BY time DESC LIMIT 1;'
    sz_result = clientInfluxDB.query(query)
    logger.debug(sz_result)
    sz_resultList = list(sz_result.get_points(measurement='sz_einspeisen_tariflos_2.8.0'))
    sz_resultDict = sz_resultList[0]
    sz_zaehler_einspeisen_tariflos_kWh_gestern = float(sz_resultDict['kWh'])
    logger.info("SZ Zaehler einspeisen tariflos 2.8.0 gestern: "+str(sz_zaehler_einspeisen_tariflos_kWh_gestern))
except Exception as e:
    logger.error(e)
    try:
        logger.error("Keine Daten vom Vortag in der Datenbank! Die aktullen Daten werden eingespielt, der Tagesverbrauch kann nicht errechnet werden!")
        clientInfluxDB.write_points(points)
    except Exception as e:
        logger.error(e)
        sys.exit(1)
    sys.exit(1)


# Verbrauch und Einspeisung eines Tages berechnen
einspiesen_tag = sz_zaehler_einspeisen_tariflos_kWh - sz_zaehler_einspeisen_tariflos_kWh_gestern
logger.info("Einspeisen Tag: "+str(einspiesen_tag))
point = {
    "measurement": 'einspiesen_tag',
    "tags": {
        "instance": influxDB_tag_instance,
        "source": influxDB_tag_source
    },
    #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
    "fields": {
        "kWh": einspiesen_tag
        }
    }
points.append(point)

bezug_tag = sz_zaehler_tariflos_kWh - sz_zaehler_tariflos_kWh_gestern
logger.info("Bezug Tag: "+str(bezug_tag))
point = {
    "measurement": 'bezug_tag',
    "tags": {
        "instance": influxDB_tag_instance,
        "source": influxDB_tag_source
    },
    #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
    "fields": {
        "kWh": bezug_tag
        }
    }
points.append(point)

pv_eigenvergrauch_tag = pv_ertrag_tag_kWh - einspiesen_tag
logger.info("Eigenverbrauch Tag: "+str(pv_eigenvergrauch_tag))
point = {
    "measurement": 'pv_eigenvergrauch_tag',
    "tags": {
        "instance": influxDB_tag_instance,
        "source": influxDB_tag_source
    },
    #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
    "fields": {
        "kWh": pv_eigenvergrauch_tag
        }
    }
points.append(point)

verbrauch_tag = pv_eigenvergrauch_tag + bezug_tag
logger.info("Verbrauch Tag: "+str(verbrauch_tag))
point = {
    "measurement": 'verbrauch_tag',
    "tags": {
        "instance": influxDB_tag_instance,
        "source": influxDB_tag_source
    },
    #   "time": timestamp,   # Wenn nicht genutzt, wird der aktuelle Timestamp aus influxDB genutzt
    "fields": {
        "kWh": verbrauch_tag
        }
    }
points.append(point)
logger.debug(points)

##### influxDB section
try:
    clientInfluxDB.write_points(points)
except Exception as e:
    logger.error(e)
    sys.exit(1)

