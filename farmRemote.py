
from PySide import QtCore
from PySide import QtGui
from PySide import QtWebKit

import os
import sys
import hou

class QuickStartBrowser(QtWebKit.QWebView):
    def __init__(self):
        QtWebKit.QWebView.__init__(self)
        
        
    def contextMenuEvent(self, event):
        menu = QtGui.QMenu()
        menu.addAction(self.pageAction(QtWebKit.QWebPage.Copy))
        menu.exec_(QtGui.QCursor.pos())

def sendJob():
    project_name = hou.hscriptExpression('$HIP').split('/')[len(hou.hscriptExpression('$HIP').split('/'))-1]
    copy_file = "cp " + hou.hscriptExpression('$HIP') + "/*" + " ~/Documents/houdini_render_farm/" + project_name + "; "
    main_string1 = '''ssh james@25.125.36.248 -t "cd /opt/hfs14.0.444/; source houdini_setup; cp -n /mnt/dtop/''' + project_name + ''' /mnt/hq/; cd /mnt/hq/Projects/'''
    main_string2 = project_name + '''; echo 'render hq_render1' | hbatch ''' + hou.hscriptExpression('$HIPNAME') + ''';"'''
    execute = copy_file+main_string1+main_string2
    print execute
    #os.system(execute)


def createInterface():
    web_view = QuickStartBrowser()
    
    web_view.load('http://25.125.36.248:5000')
    
    hbox = QtGui.QHBoxLayout()
    vbox = QtGui.QVBoxLayout()

    #os.system("")
    
    render_button = QtGui.QPushButton("Render Current Hip")
    render_button.clicked[bool].connect(sendJob)
    sync_button = QtGui.QPushButton("Sync Disk")
    
    hbox.addWidget(render_button)
    hbox.addWidget(sync_button)
    
    vbox.addLayout(hbox)
    vbox.addWidget(web_view)
    
    root_widget = QtGui.QWidget()
    
    root_widget.setLayout(vbox)
    
    return root_widget
