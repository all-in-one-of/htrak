import numpy as np
import hou

from nibabel import trackvis

# HTrak File Reader for Houdini

# Get points from file

def getPointsFromTrack(filename):
	geo = hou.pwd().geometry()
	streams, hdr = trackvis.read(filename)
	print hdr
	streamlines = [s[0] for s in streams]
	for stream in streamlines:
		curve = geo.createNURBSCurve(len(stream))
		i = 0
		for vertex in curve.vertices():
		    vertex.point().setPosition((float(stream[i][0]),float(stream[i][1]),float(stream[i][2])))
		    i = i + 1



