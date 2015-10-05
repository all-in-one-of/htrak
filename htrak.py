import numpy as np
import hou
import thread

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
		if hou.updateProgressAndCheckForInterrupt():
			break
		for vertex in curve.vertices():
		    vertex.point().setPosition((float(stream[i][0]),float(stream[i][1]),float(stream[i][2])))
		    i = i + 1
		    if hou.updateProgressAndCheckForInterrupt():
        		break

def groupStartEndPoints(geo):
	starts = geo.createPointGroup('StartPoints')
	ends = geo.createPointGroup('EndPoints')

	for prim in geo.prims():
		if hou.updateProgressAndCheckForInterrupt():
			break
		starts.add(prim.vertices()[0].point())
		ends.add(prim.vertices()[len(prim.vertices())-1].point())


def isInside(pointA,pointB,radius):
	ax = pointA[0]
	ay = pointA[1]
	az = pointA[2]

	bx = pointB[0]
	by = pointB[1]
	bz = pointB[2]

	return ((bx-ax)*(bx-ax) + (by-ay)*(by-ay) + (bz-az)*(bz-az) <= radius*radius)

'''
Read in curve data and create attributes for visualization.
Find start points and end points within a spherical radius of each start and end.
'''

def createAttributes(radius):
	geo = hou.pwd().geometry()
	prims = geo.prims()
	# Initialize Attributs
	if geo.findPointAttrib('Signal') is None:
		geo.addAttrib(hou.attribType.Point,'Signal',(0,0,0))
	if geo.findPointAttrib('Flow') is None:
		geo.addAttrib(hou.attribType.Point,'Flow',0)
	if geo.findPointAttrib('EndNeighbors') is None:
		geo.addAttrib(hou.attribType.Point,'EndNeighbors',"")
	if geo.findPointAttrib('StartNeighbors') is None:
		geo.addAttrib(hou.attribType.Point,'StartNeighbors',"")

	# Iterate through the streamlines and create a dict from id to Start and End Points
	starts = {}
	ends = {}
	i = 0
	for prim in geo.prims():
		starts[str(i)] = prim.vertices()[0].point().position()
		ends[str(i)] = prim.vertices()[len(prim.vertices())-1].point().position()
		if hou.updateProgressAndCheckForInterrupt():
			break
		i = i + 1

	# Using start and end dicts, create a new dict of stream # to start points and end
	# points within the radius of a sphere
	stream_starts = {}
	stream_ends = {}
	i=0
	for i in range(0,len(geo.prims())):
		if hou.updateProgressAndCheckForInterrupt():
			break
		
		pointA = prim.vertices()[0].point().position()

		for stream_id in starts:
			pointB = starts[stream_id]
			if hou.updateProgressAndCheckForInterrupt():
				break
			if isInside(pointA,pointB,radius):
				if stream_starts[str(i)] is None:
					stream_starts[str(i)] = stream_id
				else:
					stream_starts[str(i)] = stream_starts[str(i)] + stream_id
			
		for stream_id in ends:
			pointB = ends[stream_id]
			if hou.updateProgressAndCheckForInterrupt():
				break
			if isInside(pointA,pointB,radius):
				if stream_ends[str(i)] is None:
					stream_ends[str(i)] = stream_id
				else:
					stream_ends[str(i)] = stream_ends[str(i)] + stream_id
			

		for vert in prim.vertices():
			if hou.updateProgressAndCheckForInterrupt():
				break
			try:
				vert.point().setAttribValue('StartNeighbors',stream_starts[str(i)])
			except:
				continue

		for vert in prim.vertices():
			if hou.updateProgressAndCheckForInterrupt():
				break
			try:
				vert.point().setAttribValue('EndNeighbors',stream_ends[str(i)])
			except:
				continue
		i = i+1

	groupStartEndPoints(geo)



