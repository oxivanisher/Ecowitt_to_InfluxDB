#!/usr/bin/env python3
#
# Receive Ecowitt format payloads and write them out to InfluxDB
#

from flask import Flask, request
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS



app = Flask(__name__)

# Todo - take these from the environment
IGNORE = ["PASSKEY","stationtype","dateutc","freq"]
TAGS = ["model"]
MEASUREMENT="weather"

INFLUX_BUCKET = "testing_db"
INFLUX_ORG = ""
INFLUX_TOKEN = ""
# Store the URL of your InfluxDB instance
INFLUX_URL="http://192.168.3.84:8086"


@app.route('/')
def version():
    return "Ecowitt listener\n"


@app.route('/data/report/', methods=['POST'])
def receiveEcoWitt():

    '''
    From packet capture

    POST /data/report/ HTTP/1.1
    HOST: weatherreport.bentasker.co.uk
    Connection: Close
    Content-Type: application/x-www-form-urlencoded
    Content-Length:182 

    PASSKEY=02EB4812BE8FE29E25936DCC71B81862&stationtype=GW1100A_V2.0.4&dateutc=2022-03-23+17:47:28&tempinf=77.5&humidityin=38&baromrelin=30.428&baromabsin=30.428&freq=868M&model=GW1100AHTTP/1.1 200 OK
    Server: nginx/1.14.2
    Date: Wed, 23 Mar 2022 17:47:28 GMT
    Content-Type: application/octet-stream
    Content-Length: 0
    Connection: close
    '''        
    
    fieldset = {}
    tagset = {}
    
    # Iterate over each pair in the post body
    data = request.form
    for key in data:
        print(f"{key}: {data[key]}\n")

        if key in IGNORE:
            continue

        # The dict isn't actually a dict, but an immutable dict like object
        # copy the value into a var so we can modify it as needed
        val = data[key]
        if key in TAGS:
            tagset[key] = val
            continue
        
        if key.startswith("temp") and key.endswith("f"):
            val = convertFtoC(val)
            key = key[:-1] + 'c'

        if key.startswith("barom") and key.endswith("in"):
            # Convert inches to hPa
            val = float(val) * 33.6585
            key = key[:-2] + 'hpa'

        # Push into the fields dict
        fieldset[key] = val
        
    # turn it into LP
    lp = build_lp(tagset, fieldset)
    write_lp(lp)
    print(lp)
    return lp



def write_lp(lp):
    # Set up to send into Influx
    with influxdb_client.InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        write_api.write(INFLUX_BUCKET, lp)
        
    
    

def build_lp(tagset, fieldset):
    ''' Build some line protocol
    '''
    s = [f"{MEASUREMENT},"]

    for tag in tagset:
        s.append(f"{tag}={tagset[tag]},")
        
    s = [''.join(s)]
    s[0] = s[0].rstrip(",")
    s.append(" ")
    
    for field in fieldset:
        s += f"{field}={fieldset[field]},"
    s = ''.join(s)
    s = s.rstrip(",")
    return s


def convertFtoC(f):
    ''' Convert Farenheit to Celsius
    '''
    return (float(f) - 32) * 5 /9
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090, debug=True)

