import serial
import time
import threading
import random
import logging
import re

from opengb.printer import IPrinter
from opengb.printer import State 


# Map Marlin message patterns to callbacks.
MSG_PATTERNS = [
    # Standard 'echo' message.
    (re.compile(r'echo:\s*(?P<msg>.*)$'),
     lambda g, c: (getattr(c, 'log')(logging.INFO, g['msg']))),
    # Temperature update.
    (re.compile(r'ok T:(?P<n1temp>\d*\.?\d+)\s/(?P<n1target>\d*\.?\d+)\s'
                'B:(?P<btemp>\d*\.?\d+)\s/(?P<btarget>\d*\.?\d+)\s'
                'T0:(?P<n2temp>\d*\.?\d+)\s/(?P<n2target>\d*\.?\d+)\s.*$'),
     lambda g, c: (getattr(c, 'temp_update')(g['btemp'], g['btarget'],
                                             g['n1temp'], g['n1target'],
                                             g['n2temp'], g['n2target']))),
]


class Marlin(IPrinter):
    """
    A printer controlled by `Marlin <http://www.marlinfirmware.org>`_ firmware.
    """

    def __init__(self, *args, **kwargs):
        self._serial = serial.Serial()
        self._serial_lock = threading.Lock()
        super().__init__(*args, **kwargs)

    def _connect(self):
        try:
            self._serial.setBaudrate(self._baud_rate)
            self._serial.setPort(self._port)
            self._serial.setTimeout(self._timeout)
            self._serial.open()
            # Allow time for serial open to complete before reading/writing.
            time.sleep(1)
        except serial.SerialException as e:
            raise ConnectionError(e)

    def _send_command(self, command):
        """
        Send a command to the serial port, attempting to re-connect if
        necessary.
        
        :param command: Command to send to the serial port.
        :type command: :class:`bytes`
        :returns: True if successful, otherwise False.
        :rtype: :class:`bool`
        """

        self._callbacks.log(logging.DEBUG, 'Sending command: ' + str(command))
        try:
            with self._serial_lock:
                try:
                    self._serial.write(command + b'\n')
                except serial.SerialException:
                    self._callbacks.log, (logging.WARN, 'Error writing to '
                                          'serial port - reconnecting')
                    try:
                        self._connect()
                        self._serial.write(command)
                    except ConnectionError as e:
                        self._callbacks.log, (logging.ERROR, 'unable to connect '
                                          'to serial port: ' + str(e))
                        return False
        except IOError:
            # Unable to lock the serial port.
            return False
        return True

    def _request_printer_metrics(self):
        self._callbacks.log(logging.DEBUG, 'Requesting printer metrics')
        self._send_command(b'M105')

    def _print_line(self, line):
        # TODO: implement
        pass

    def _get_message_from_printer(self):
        """
        Read a message from the serial port, attempting to re-connect if
        neccessary.
        """
        try:
            with self._serial_lock:
                try:
                    message = self._serial.readline()
                except serial.SerialException:
                    self._callbacks.log, (logging.WARN, 'Error reading from '
                                          'serial port - reconnecting')
                    try:
                        self._connect()
                    except ConnectionError as e:
                        self._callbacks.log, (logging.ERROR, 'unable to '
                                          'connect to serial port: ' + e)
                    finally:
                        return None
        except IOError:
            # Unable to lock the serial port.
            return False
        return message

    def _process_message_from_printer(self, message):
        """
        Process Marlin messages and fire appropriate callbacks.
        """
        message = message.decode().rstrip()
        for each in MSG_PATTERNS:
            m = each[0].match(message)
            if m:
                self._callbacks.log(logging.DEBUG, 'Parsed: ' + message)
                each[1](m.groupdict(), self._callbacks)
                break
            time.sleep(1)
        else:
            self._callbacks.log(logging.DEBUG, 'Unparsed: ' + message)

    def set_temp(self, bed=None, nozzle1=None, nozzle2=None):
        if bed:
            self._send_command(b'M140 S' + str(bed).encode())
        if nozzle1:
            self._send_command(b'M104 T0 S' + str(nozzle1).encode())
        if nozzle2:
            self._send_command(b'M104 T1 S' + str(nozzle2).encode())

    def move_head(self, x=0, y=0, z=0):
        # Switch to relative coordinates before sending.
        # TODO: does it matter to send G91 every time?
        self._send_command(b'G91')
        # TODO: confirm that it's ok to send 0 for no movement.
        self._send_command('G0 X{0} Y{1} Z{2}'.format(x, y, z).encode())
