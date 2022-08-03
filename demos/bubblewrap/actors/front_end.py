import pyqtgraph
import matplotlib.pylab as plt
import matplotlib
matplotlib.use('Qt5Agg')

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QColor
from . import improv_bubble
from improv.actor import Spike

from queue import Empty
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QGridLayout

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FrontEnd(QtWidgets.QMainWindow, improv_bubble.Ui_MainWindow):
    def __init__(self, visual, comm, q_sig, parent=None):
        ''' Setup GUI
            Setup and start Nexus controls
        '''
        self.visual = visual
        self.comm = comm  # Link back to Nexus for transmitting signals
        self.q_sig = q_sig
        self.prev = 0

        pyqtgraph.setConfigOption('background', QColor(100, 100, 100))

        super(FrontEnd, self).__init__(parent)
        self.setupUi(self)
        pyqtgraph.setConfigOptions(leftButtonPan=True)
        self.setWindowTitle("Bubblewrap")

        #Setup button
        self.pushButton.clicked.connect(_call(self._setup))
        self.pushButton.clicked.connect(_call(self.started))
        #self.pushButton.clicked.connect(self.plot)
        
        #Run button
        self.pushButton_2.clicked.connect(_call(self._runProcess))
        self.pushButton_2.clicked.connect(_call(self.update)) # Tell Nexus to start

    def plot(self):
        #plot ellipses
        x_cords = np.random.randint(0, 100, 10)
        y_cords = np.random.randint(0, 100, 10)
        for i in range(10):
            self.ellipse = pyqtgraph.QtGui.QGraphicEllipseItem(x_cords[i], y_cords[i], 20, 10)
            self.ellipse.setPen(pg.mkPen((0, 0, 0, 100)))
            self.ellipse.setBrush(pg.mkBrush((50, 50, 200, 50))) #last param set transparency
            self.ellipse.setRotation(60) #set angle

    def update(self):
        self.visual.getData()
        if(len(self.visual.data) != 0):
            if(self.prev == 0):
                self.loadVisual()
                self.prev = 1
            elif(self.prev != self.visual.data[0]):
                self.updateVisual()
                self.prev += 1

        QtCore.QTimer.singleShot(10, self.update)

    def updateVisual(self):
        # if self.radioButton.isChecked():
        #     self.sc.axes.plot(self.visual.data[1][:, 0], self.visual.data[1][:, 1], color='gray', alpha=0.8)
        # if self.radioButton_2.isChecked():
        #     self.sc.axes.scatter(self.visual.data[1][:, 0], self.visual.data[1][:, 1], color='gray', alpha=0.8)
        # self.sc.fig.canvas.draw_idle()

    def loadVisual(self):
        ### 2D vdp oscillator
        # if self.radioButton.isChecked():
        #     self.sc.axes.plot(self.visual.data[1][:, 0], self.visual.data[1][:, 1], color='gray', alpha=0.8)
        # if self.radioButton_2.isChecked():
        #     self.sc.axes.scatter(self.visual.data[1][:, 0], self.visual.data[1][:, 1], color='gray', alpha=0.8)
        layout = QGridLayout()
        layout.addWidget(self.sc)
        self.frame.setLayout(layout)
        self.show()

    def started(self):
        try:
            signal = self.q_sig.get(timeout=0.000001)
            if(signal == Spike.started()):
                self.pushButton_2.setStyleSheet("background-color: rgb(255, 255, 255);")
                self.pushButton.setEnabled(False)
                self.pushButton_2.setEnabled(True)
            else:
                QtCore.QTimer.singleShot(10, self.started)
        except Empty as e:
            QtCore.QTimer.singleShot(10, self.started)
            pass
        except Exception as e:
            logger.error('Front End: Exception in get data: {}'.format(e))

    def _runProcess(self):
        self.comm.put([Spike.run()])
        logger.info('-------------------------   put run in comm')

    def _setup(self):
        self.comm.put([Spike.setup()])
        self.visual.setup()

def _call(fnc, *args, **kwargs):
    ''' Call handler for (external) events
    '''
    def _callback():
        return fnc(*args, **kwargs)
    return _callback


if __name__ == "__main__":
