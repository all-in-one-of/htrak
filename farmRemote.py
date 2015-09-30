
from PySide import QtCore
from PySide import QtGui
from PySide import QtWebKit

import os
import sys

class QuickStartBrowser(QtWebKit.QWebView):
    def __init__(self):
        QtWebKit.QWebView.__init__(self)
        
    def contextMenuEvent(self, event):
        menu = QtGui.QMenu()
        menu.addAction(self.pageAction(QtWebKit.QWebPage.Copy))
        menu.exec_(QtGui.QCursor.pos())

def createInterface():

    web_view = QuickStartBrowser()
    web_view.load('http://25.125.36.248:5000')

    return web_view
