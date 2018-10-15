import inspect
import os
import sys
import math
import threading
from http.server import HTTPServer
import socket
import time
import obd

from prometheus.collectors import Gauge
from prometheus.registry import Registry
from prometheus.exporter import PrometheusMetricHandler

print("Connecting to obd...")
connection = obd.OBD("/dev/ttyUSB0", 115200)
print("Connected...")
PORT_NUMBER = 8081
def gather_data(registry):
    """Gathers the metrics"""

    host = socket.gethostname()
    tags = {'host': host}

    # Create our collectors
    engine_rpm = Gauge("obd_engine_rpm", "OBD Engine RPM", tags)
    engine_load = Gauge("obd_engine_load", "OBD Engine Load", tags)
    vehicle_speed = Gauge("obd_vehicle_speed", "OBD Vehicle Speed", tags)
    coolant_temp = Gauge("obd_coolant_temperature", "OBD Coolant temp", tags)
    throttle_pos = Gauge("obd_throttle_position", "OBD throttle pos", tags)
    timing_advance = Gauge("obd_timing_advance", "OBD timing advance", tags)

    # register the metric collectors
    metrics = [engine_rpm, engine_load, vehicle_speed, coolant_temp, throttle_pos, timing_advance]
    commands = ["RPM", "ENGINE_LOAD", "SPEED", "COOLANT_TEMP", "THROTTLE_POS", "TIMING_ADVANCE"]
    for metric in metrics:
        registry.register(metric)

    # Start gathering metrics every half second
    while True:
        time.sleep(0.5)

        for idx, metric in enumerate(metrics):
            command = commands[idx]
            response = connection.query(obd.commands[command])
            if response != None and not response.is_null():
                value = response.value
                metric.set({}, value.magnitude)

if __name__ == "__main__":
    # Create the registry
    registry = Registry()

    # Create the thread that gathers the data while we serve it
    thread = threading.Thread(target=gather_data, args=(registry, ))
    thread.start()

    # Set a server to export (expose to prometheus) the data (in a thread)
    try:
        # We make this to set the registry in the handler
        def handler(*args, **kwargs):
            PrometheusMetricHandler(registry, *args, **kwargs)

        server = HTTPServer(('', PORT_NUMBER), handler)
        server.serve_forever()

    except KeyboardInterrupt:
        server.socket.close()
        thread.join()
