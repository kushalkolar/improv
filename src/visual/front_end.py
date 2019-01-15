import sys
from PyQt5 import QtGui,QtCore
from PyQt5.QtGui import QColor
from visual import rasp_ui
from nexus.nexus import Nexus
import numpy as np
import pylab
import time
import pyqtgraph
from pyqtgraph import EllipseROI, PolyLineROI
from threading import Thread
from multiprocessing import Process
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from process.process import CaimanProcessor as cp

import logging; logger = logging.getLogger(__name__)


class FrontEnd(QtGui.QMainWindow, rasp_ui.Ui_MainWindow):

    def __init__(self, parent=None):
        ''' Setup GUI
            Setup and start Nexus
        '''
        pyqtgraph.setConfigOption('background', QColor(229, 229, 229)) #before loading widget
        super(FrontEnd, self).__init__(parent)
        
        self.setupUi(self)
        self.setStyleSheet("QMainWindow {background: 'white';}")
                
        self.rawplot.ui.histogram.hide()
        self.rawplot.ui.roiBtn.hide()
        self.rawplot.ui.menuBtn.hide()
        self.checkBox.setChecked(True)

        #init line plot
        self.c1 = self.grplot.plot()
        self.c2 = self.grplot_2.plot()
        self.c3 = self.grplot_3.plot()
        grplot = [self.grplot, self.grplot_2, self.grplot_3]
        for plt in grplot:
            plt.getAxis('bottom').setTickSpacing(major=50, minor=50)
            plt.setLabel('bottom', "Frames")
            plt.setLabel('left', "Temporal traces")
        self.updateLines()
        
        self.nexus = Nexus('NeuralNexus')
        self.nexus.createNexus()

        #Currently running initialize here        
        self.nexus.setupProcessor()

        self.pushButton_3.clicked.connect(_call(self._runProcess))
        self.pushButton_3.clicked.connect(_call(self.update))
        self.pushButton.clicked.connect(_call(self._loadParams))
        self.checkBox.stateChanged.connect(self.update) #TODO: call outside process or restric to checkbox update
        self.rawplot.getImageItem().mouseClickEvent = self.mouseClick

    def _loadParams(self):
        ''' Button event to load parameters from file
            File location determined from user input
            Throws FileNotFound error
        '''
        fname = QFileDialog.getOpenFileName(self, 'Open file', '/home')
            #TODO: make default home folder system-independent
        try:
            self.nexus.loadTweak(fname[0])
        except FileNotFoundError as e:
            logger.error('File not found {}'.format(e))
            #raise FileNotFoundError
    
    def _runProcess(self):
        '''Run ImageProcessor in separate thread
        '''
        self.t = Thread(target=self.nexus.runProcessor)
        self.t.daemon = True
        self.t.start()

        #TODO: grey out button until self.t is done, but allow other buttons to be active


    def update(self):
        ''' Update visualization while running
        '''
        #plot lines
        self.updateLines()

        #plot video
        self.updateVideo()

        #re-update
        if self.checkBox.isChecked():
            QtCore.QTimer.singleShot(100, self.update)
    
    def updateVideo(self):
        image = None
        try:
            image = self.nexus.getPlotRaw()
        except Exception as e:
            logger.error('Oh no {0}'.format(e))
        if image is not None:
            self.rawplot.setImage(image.T)
        
        #try:
            #neurCom = self.nexus.getPlotCoM()
            #penCont=pyqtgraph.mkPen(width=1, color='b')
            #for c in neurCom:
                #TODO: offload this to visual class
                #TODO: and only add item if it doesn't yet exist
                #shp = shp[~np.isnan(shp).any(axis=-1)]
                #positions = tuple(map(tuple,shp))
                #self.rawplot.getView().addItem(CircleROI(positions, closed=True, pos=self.selected[0].T-5, pen=penCont))
            #    self.rawplot.getView().addItem(CircleROI(pos = np.array([c[1], c[0]])-5, size=10, movable=False, pen=penCont))
        #except Exception as e:
        #    logger.error('Something {0}'.format(e))

    def updateLines(self):
        ''' Helper function to plot the line traces
            of the activity of the selected neurons.
            TODO: separate updates for each plot?
        '''
        #plot traces
        pen=pyqtgraph.mkPen(width=2, color='r')
        pen2=pyqtgraph.mkPen(width=2, color='b')
        pen3=pyqtgraph.mkPen(width=2, color='g')
        Y = None
        try:
            #self.ests = self.nexus.getEstimates()
            (X, Y) = self.nexus.getPlotEst()
        except Exception as e:
            logger.error('output does not yet exist. error: {}'.format(e))

        if(Y is not None):
            self.c1.setData(X, Y[0], pen=pen)
            self.c2.setData(X, Y[1], pen=pen2)
            self.c3.setData(X, Y[2], pen=pen3)

    def mouseClick(self, event):
        '''Clicked on raw image to select neurons
        '''
        #TODO: make this unclickable until finished updated plot (?)
        event.accept()
        mousePoint = event.pos()
        self.selected = self.nexus.selectNeurons(int(mousePoint.x()), int(mousePoint.y()))
        selectedraw = np.zeros(2)
        selectedraw[0] = int(mousePoint.x())
        selectedraw[1] = int(mousePoint.y())
        print('selectedRaw is ', selectedraw, ' but found selected is ', self.selected)
        ROIpen1=pyqtgraph.mkPen(width=1, color='r')
        if np.count_nonzero(self.selected[0]) > 0:
            self.rawplot.getView().addItem(CircleROI(pos = self.selected[0]-5, size=10, movable=False, pen=ROIpen1))

    def closeEvent(self, event):
        '''Clicked x/close on window
            Add confirmation for closing without saving
        '''
        confirm = QMessageBox.question(self, 'Message', 'Quit without saving?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.nexus.destroyNexus()
            event.accept()
        else: event.ignore()


def _call(fnc, *args, **kwargs):
    ''' Call handler for (external) events
    '''
    def _callback():
        return fnc(*args, **kwargs)
    return _callback

class CircleROI(EllipseROI):
    def __init__(self, pos, size, **args):
        pyqtgraph.ROI.__init__(self, pos, size, **args)
        self.aspectLocked = True

class PolyROI(PolyLineROI):
    def __init__(self, positions, pos, **args):
        closed = True
        print('got positions ', positions)
        pyqtgraph.ROI.__init__(self, positions, closed, pos, **args)
        #self.aspectLocked = True

if __name__=="__main__":
    app = QtGui.QApplication(sys.argv)
    rasp = FrontEnd()
    rasp.show()
    app.exec_()