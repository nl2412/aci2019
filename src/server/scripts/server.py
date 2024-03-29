import socket
import asyncio
import pyaudio
import sys
import struct
import math
import datetime
import logging

class SoundDetector():
    def __init__(self, threshold):
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.dev_index = 2
        self.rate = 44100
        self.record_seconds = 10
        self.swidth = 2
        self.threshold = threshold
        self.short_normalize = (1.0/32768.0)
        self.pyrecord = pyaudio.PyAudio()

    def convert_data(self, input):
        count = len(input) / self.swidth
        format = "%dh" % (count)
        shorts = struct.unpack(format, input)
        sum_square = 0.0
        for sample in shorts:
            n = sample * self.short_normalize
            sum_square += n*n
        rms = math.pow(sum_square/count, 0.5)
        return rms * 1000

    def start_recording(self, connection):
        stream = self.pyrecord.open(format=self.format, channels=self.channels,
                                    rate=self.rate, input=True,
                                    input_device_index=self.dev_index,
                                    frames_per_buffer=self.chunk)
        logging.info("start recording")
        for i in range(0, int(44100 / self.chunk * self.record_seconds)):
            data = stream.read(self.chunk)
            rms_value = self.convert_data(data)
            if rms_value > self.threshold:
                timestamp = datetime.datetime.now()
                message = "{}:{}:{}.{} Sound detected".format(timestamp.hour, timestamp.minute, 
                                                            timestamp.second, timestamp.microsecond)
                # send data to client
                connection.sendall(message.encode())

        # done recording
        logging.info("recording done")
        message = "done"
        connection.sendall(message.encode())

        stream.stop_stream()
        stream.close()
        self.pyrecord.terminate()


class TcpServer():
    def __init__(self, host, port):
        self.server_host = host
        self.server_port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # bind listener to specified port
        self.server_socket.bind((self.server_host, self.server_port))

        logging.info("Server setup successfully.")

    def start(self):
        # start listening for incoming connection
        self.server_socket.listen(1)
        logging.info("Listening for connection from client...")

        while True:
            # accept connection from client
            conn, client_address = self.server_socket.accept()
            try:
                logging.info("Received connection from {}".format(client_address))
                while True:
                    # read request from client(s)
                    data = conn.recv(1024)
                    logging.info("Received {!r}".format(data.decode()))

                    if data:
                        detector = SoundDetector(10)
                        detector.start_recording(conn)
                    else:
                        break

            finally:
                conn.close()


async def main():
    # initialize logging
    logging.basicConfig(level = logging.INFO)

    # setup server: TcpServer(host, port)
    tcp_server = TcpServer("", 9999)

    # start a task that will listen for connection from clients asynchronously
    task = loop.create_task(tcp_server.start())
    await asyncio.wait(task)


if __name__ == "__main__":
    try:
        # create an event loop for asyncio
        loop = asyncio.get_event_loop()
        # start the loop until main function completed its job
        loop.run_until_complete(main())
    except Exception as err:
        raise err
    finally:
        # close loop on finish
        loop.close()
