"""
OpenGB configuration.
"""

from tornado.options import define


# TODO: deploy a default config file via package manager and/or on startup.
CONFIG_FILE = "/etc/opengb/opengb.conf"


define('http_port', default=80, help='Webserver http listen port')
define('debug', default=False, help='Run in debug mode')
define('db_file', default='/var/opengb/opengb.db', help='SQLite database')
define('printer', default='Dummy', help='Printer type')
define('baud_rate', default=115200, help='Printer baud rate')
define('serial_port', default='/dev/ttyACM0', help='Printer serial port')
