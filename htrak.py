import numpy as np
import hou

from nibabel import trackvis

'''

Read in .trk file and return separate Nurbs curves with start and end neighbor 
attributes. Optional radius input for neightbor search boundary.

'''
def getPointsFromTrack(filename):
	geo = hou.pwd().geometry()
	# Read in stream data 
	streams, hdr = trackvis.read(filename)

	streamlines = [s[0] for s in streams]

	# For each streamline add a curve to the geometry
	for stream in streamlines:		
		i = 0
		curve = geo.createNURBSCurve(len(stream))
		for vertex in curve.vertices():
		    vertex.point().setPosition((float(stream[i][0]),float(stream[i][1]),float(stream[i][2])))
		    i = i + 1

def isInside(pointA,pointB,radius=0.1):
	return

'''
Read in curve data and create attributes for visualization.
Find start points and end points within a spherical radius of each start and end.
'''

def createAttributes():
	geo = hou.pwd().geometry()
	prims = geo.prims()
	# Initialize Attributs
	if geo.findPointAttrib('Signal') is None:
		geo.addAttrib(hou.attribType.Point,'Signal',(0,0,0))
	if geo.findPointAttrib('Flow') is None:
		geo.addAttrib(hou.attribType.Point,'Flow',0)
	if geo.findPointAttrib('EndNeighbors') is None:
		geo.addAttrib(hou.attribType.Point,'EndNeighbors',"A")
	if geo.findPointAttrib('StartNeighbors') is None:
		geo.addAttrib(hou.attribType.Point,'StartNeighbors',"B")

	# Iterate through the streamlines and create a dict from id to Start and End Points
	starts = {}
	ends = {}
	i = 0
	for prim in geo.prims():
		starts[str(i)] = prim.vertices()[0].point().position()
		ends[str(i)] = prim.vertices()[len(prim.vertices())-1].point().position()
		i = i + 1

	print starts
	# Using start and end dicts, create a new dict of stream # to start points and end
	# points within the radius of a sphere
	stream_starts = {}
	stream_ends = {}


