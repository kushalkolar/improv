from queue import Empty
import logging
from typing import *

import numpy as np
import tifffile
import zmq

from improv.actor import Actor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ZmqReceiver(Actor):
    """
    Receives frame from zmq and puts it in the queue
    """
    def __init__(self, address: str, *args, **kwargs):
        """
        Parameters
        ----------
        address: str
            example: ``"tcp://127.0.0.1:5555"``
        """

        super().__init__(*args, **kwargs)

        context = zmq.Context()
        # TODO: We probably also want to receive setup info from zmq
        # TODO: such as animal_id, channel info, comments, date, etc.
        self.sub = context.socket(zmq.SUB)
        self.sub.setsockopt(zmq.SUBSCRIBE, b"")

        self.sub.connect("")

    def setup(self):
        logger.info("Zmq Receiver ready")

    def _receive_buffer(self) -> bytes | None:
        """
        Gets the buffer from the publisher
        """
        try:
            b = self.sub.recv(zmq.NOBLOCK)
        except zmq.Again:
            pass
        else:
            return b

        return None

    def runStep(self):
        """
        Receives data from zmq publisher, puts it in the queue.

        We assume that actors which utilize this array will parse
        the header and frame themselves from the buffer.
        """

        buff = self._receive_buffer()

        self.q_out.put(buff)


class MesmerizeWriter(Actor):
    """
    Writes data to mesmerize database
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup(self):
        # TODO: maybe do something here where we get the UUID and other info like params?
        # TODO: Also decide how we communicate information like dtype, buffer parsing etc.
        self.writer = tifffile.TiffWriter("./test.tiff", bigtiff=True)

        logger.info("Mesmerize Writer ready")

    def _get_frame(self) -> np.ndarray:
        frame = None

        try:
            frame = self.q_in.get(timeout=0.05)
        except Empty:
            pass

        except:
            logger.error("Could not get frame!")

        return frame

    def stop(self):
        self.writer.close()
        return 0

    def runStep(self):
        """
        Writes data to a mesmerize database
        """
        frame = self._get_frame()

        self.writer.write(frame)
