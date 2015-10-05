
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
    
    hbox = QtGui.QHBoxLayout()
    vbox = QtGui.QVBoxLayout()
    
    render_button = QtGui.QPushButton("Render Current Hip")
    sync_button = QtGui.QPushButton("Sync Disk")
    
    hbox.addWidget(render_button)
    hbox.addWidget(sync_button)
    
    vbox.addLayout(hbox)
    vbox.addWidget(web_view)
    
    root_widget = QtGui.QWidget()
    
    root_widget.setLayout(vbox)
    
    return root_widget
