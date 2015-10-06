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
	j = 0
	for stream in streamlines:		
		i = 0
		curve = geo.createNURBSCurve(len(stream))
		if hou.updateProgressAndCheckForInterrupt(int(float(j)/float(len(streamlines))*100)):
			break
		for vertex in curve.vertices():
		    vertex.point().setPosition((float(stream[i][0]),float(stream[i][1]),float(stream[i][2])))
		    i = i + 1
		    if hou.updateProgressAndCheckForInterrupt():
        		break
        j = j+1

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
	if geo.findPrimAttrib('Flow') is None:
		geo.addAttrib(hou.attribType.Prim,'Flow',0)
	if geo.findPrimAttrib('EndNeighbors') is None:
		geo.addAttrib(hou.attribType.Prim,'EndNeighbors',"")
	if geo.findPrimAttrib('StartNeighbors') is None:
		geo.addAttrib(hou.attribType.Prim,'StartNeighbors',"")

	# Iterate through the streamlines and create a dict from id to Start and End Points
	end_points = {}
	i = 0
	for prim in geo.prims():
		end_points[str(i)] = {'start':(0,prim.vertices()[0].point().position()), 'end':(len(prim.vertices())-1,prim.vertices()[len(prim.vertices())-1].point().position())}
		if hou.updateProgressAndCheckForInterrupt():
			break
		i = i + 1

	# Using start and end dicts, create a new dict of stream # to start points and end
	# points within the radius of a sphere
	stream_starts = {}
	stream_ends = {}
	
	i = 0
	for prim in geo.prims():
		stream_starts[str(i)] = ''
		stream_ends[str(i)] = ''
		i = i+1
	
	i = 0
	for prim in geo.prims():
		if hou.updateProgressAndCheckForInterrupt(int(float(i)/float(len(geo.prims()))*100)):
			break

		# Check prim start and end against all other prim start and ends.
		# Group near ends and near starts.

		pointA = prim.vertices()[0].point().position()

		for stream_id in end_points:
			if stream_id == str(i):
				continue
			pointB = end_points[stream_id]['start'][1]
			if isInside(pointA,pointB,radius):
				stream_starts[str(i)] = stream_starts[str(i)] + stream_id + ':' + '0' + ','

			pointB = end_points[stream_id]['end'][1]
			if isInside(pointA,pointB,radius):
				stream_starts[str(i)] = stream_starts[str(i)] + stream_id + ':' + str(end_points[stream_id]['end'][0]) + ','

		pointA = prim.vertices()[len(prim.vertices())-1].point().position()

		for stream_id in end_points:
			if stream_id == str(i):
				continue
			pointB = end_points[stream_id]['start'][1]
			if isInside(pointA,pointB,radius):
				stream_ends[str(i)] = stream_starts[str(i)] + stream_id + ':' + '0' + ','

			pointB = end_points[stream_id]['end'][1]
			if isInside(pointA,pointB,radius):
				stream_ends[str(i)] = stream_starts[str(i)] + stream_id + ':' + str(end_points[stream_id]['end'][0]) + ','

		prim.setAttribValue('StartNeighbors',stream_starts[str(i)])
		prim.setAttribValue('EndNeighbors',stream_ends[str(i)])

		i = i+1

	groupStartEndPoints(geo)

def solverStep(currentGeo, previousGeo):
	geo = hou.pwd().geometry()
	for prim in geo.prims():
		i = 0
		found = False
		if len(prim.vertices()) > 2:
			for vertex in prim.vertices():
				if i < len(prim.vertices()) - 1:

					point = vertex.point()
					rgb = point.attribValue('Cd')
					
					point2 = prim.vertices()[i+1].point()
					rgb2 = point2.attribValue('Cd')
					
					if rgb[0] > rgb2[0]:

						point2.setAttribValue('Cd',(rgb2[0]+rgb[0],rgb2[1]+rgb[1],rgb2[2]+rgb[2]))
						found = True
						break

				'''
				# If it is the first point
				if i == 0:
					point2 = prim.vertices()[i+1].point()
					rgb2 = point2.attribValue('Cd')
					if rgb[0] > 0 and rgb2[0] < 1:
						point2.setAttribValue('Cd',(rgb2[0]+rgb[0],rgb2[1]+rgb[1],rgb2[2]+rgb[2]))
						break
				'''
				'''
				# If it is a middle point
				elif i < len(prim.vertices()) - 1:
					point2 = prim.vertices()[i+1].point()
					rgb2 = point2.attribValue('Cd')

					point3 = prim.vertices()[i-1].point()
					rgb3 = point3.attribValue('Cd')

					if rgb[0] > rgb2[0]:
						point2.setAttribValue('Cd',(rgb2[0]+rgb[0],rgb2[1]+rgb[1],rgb2[2]+rgb[2]))
						break
					if rgb[0] > rgb3[0]:
						point3.setAttribValue('Cd',(rgb3[0]+rgb[0],rgb3[1]+rgb[1],rgb3[2]+rgb[2])) 
						break
				'''
				# If it is the last point
				i = i+1
		if found:
			continue
	return












































