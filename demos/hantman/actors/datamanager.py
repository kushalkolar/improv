from queue import Empty
import logging
from typing import *

import numpy as np
import tifffile
import zmq

from improv.actor import Actor

from .metadata import AcquisitionMetadata, TwoPhotonFrame

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ScanImageReceiver(Actor):
    """
    Receives frames and header from zmq and puts it in the queue as raw bytes.
    """
    def __init__(
            self,
            addr_acq: str,
            addr_frames: str,
            *args,
            **kwargs
    ):
        """
        Parameters
        ----------
        addr_acq: str
            zmq address for receiving acquisition metadata, example: ``"tcp://127.0.0.1:5555"``

        addr_frames: str
            zmq address for receiving frames with their headers
        """

        super().__init__(*args, **kwargs)

        # for receiving acquisition metadata
        self.context_acq = zmq.Context()
        self.sub_acq = self.context_acq.socket(zmq.SUB)
        self.sub_acq.setsockopt(zmq.SUBSCRIBE, b"")
        self.sub_acq.connect(addr_acq)

        # TODO: Better to use a store for keep acquisition metadata
        # self.context_pub_acq = zmq.Context()
        # self.pub_acq = self.context_pub_acq.socket(zmq.PUB)
        # self.pub_acq.bind(addr_pub_acq)

        # for reader frames along with their headers
        self.context_frames = zmq.Context()
        self.sub_frames = self.context_frames.socket(zmq.SUB)
        self.sub_frames.setsockopt(zmq.SUBSCRIBE, b"")
        self.sub_frames.connect(addr_frames)

    def setup(self):
        logger.info("ScanImageReceiver receiver starting")

        # TODO: Need to figure out how to properly format this as a dict or something
        acq_metadata = self.sub_acq.recv()

        # TODO: put acquisition metadata in store

        logger.info("ScanImageReceiver receiver ready!")

    def _receive_bytes(self) -> bytes | None:
        """
        Gets the buffer from the publisher
        """
        try:
            b = self.sub_frames.recv(zmq.NOBLOCK)
        except zmq.Again:
            pass
        else:
            return b

    def runStep(self):
        """
        Receives data from zmq publisher, puts it in the queue.

        We assume that actors which utilize this array will parse
        the header and frame themselves from the buffer.
        """

        buff = self._receive_bytes()

        if buff is None:
            return

        self.q_out.put(buff)


class MesmerizeWriter(Actor):
    """
    Writes data to mesmerize database
    """

    def __init__(
            self,
            *args,
            **kwargs
    ):
        """

        Parameters
        ----------
        addr_acq_meta: str
            zmq address to receive acquisition metadata
        """
        super().__init__(*args, **kwargs)
        self.acq_meta: AcquisitionMetadata = None
        self.writers: List[tifffile.TiffWriter] = list()

    def setup(self):
        # TODO: maybe do something here where we get the UUID and other info like params?
        # TODO: Also decide how we communicate information like dtype, buffer parsing etc.
        self.acq_meta: AcquisitionMetadata

        for channel in self.acq_meta.channels:
            color = channel.color
            self.writers.append(tifffile.TiffWriter(f"./{color}.tiff", bigtiff=True))

        # TODO: Get acquisition params etc. from store


        logger.info("Mesmerize Writer ready")

    def _get_frame(self) -> TwoPhotonFrame:
        try:
            buff = self.q_in.get(timeout=0.05)
        except Empty:
            pass
        except:
            logger.error("Could not get frame!")
        else:
            return TwoPhotonFrame.from_bytes(buff, self.acq_meta)

    def stop(self):
        self.writer.close()
        return 0

    def runStep(self):
        """
        Writes data to a mesmerize database
        """
        frame = self._get_frame()

        if frame is None:
            return

        for writer, channel_data in zip(self.writers, frame.channels):
            writer.write(channel_data)
