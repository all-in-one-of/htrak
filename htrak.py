import numpy as np
import hou
import thread
import math

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
'''
Creates a geometry group of all of the start points and end points for each stream
'''
def groupStartEndPoints(geo):
	starts = geo.createPointGroup('StartPoints')
	ends = geo.createPointGroup('EndPoints')

	for prim in geo.prims():
		if hou.updateProgressAndCheckForInterrupt():
			break
		starts.add(prim.vertices()[0].point())
		ends.add(prim.vertices()[len(prim.vertices())-1].point())

'''
Simple sphere intersection test
'''
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
				stream_starts[str(i)] = stream_starts[str(i)] + stream_id + ' ' + '0' + ','

			pointB = end_points[stream_id]['end'][1]
			if isInside(pointA,pointB,radius):
				stream_starts[str(i)] = stream_starts[str(i)] + stream_id + ' ' + str(end_points[stream_id]['end'][0]) + ','

		pointA = prim.vertices()[len(prim.vertices())-1].point().position()

		for stream_id in end_points:
			if stream_id == str(i):
				continue
			pointB = end_points[stream_id]['start'][1]
			if isInside(pointA,pointB,radius):
				stream_ends[str(i)] = stream_starts[str(i)] + stream_id + ' ' + '0' + ','

			pointB = end_points[stream_id]['end'][1]
			if isInside(pointA,pointB,radius):
				stream_ends[str(i)] = stream_starts[str(i)] + stream_id + ' ' + str(end_points[stream_id]['end'][0]) + ','

		prim.setAttribValue('StartNeighbors',stream_starts[str(i)])
		prim.setAttribValue('EndNeighbors',stream_ends[str(i)])

		i = i+1

	groupStartEndPoints(geo)

'''
Helper function to find the lumninance of the color
'''
def _lum(color):
	return (0.2126*color[0]+0.7152*color[1]+0.0722*color[2])
	#return (math.sqrt(color[0]*color[0] + color[1]*color[1] + color[2]*color[2]))

def _colorEqual(color1,color2):
	if color1[0] == color2[0] and color1[1] == color2[1] and color1[2] == color2[2]:
		return True
	else:
		return False
'''
Helper function to check and see if the solver reaches the end of a stream
If it does, it sends the signal color to the endpoints within the radius of that stream
'''
def _checkForEndPoint(index,rgb,prim,flow_direction,geometry):
	if index == 0:
		ends = prim.attribValue('StartNeighbors')
	else:
		ends = prim.attribValue('EndNeighbors')
	if ends is not '':
		ends_list = ends.split(',')
		for end in ends_list:
			loc = end.split()
			if len(loc) > 0:
				prim2 = geometry.prims()[int(loc[0])]
				point2 = prim2.vertices()[int(loc[1])].point()
				prim2.setAttribValue('Flow',1)
				rgb2 = point2.attribValue('Cd')
				if not _colorEqual(rgb,rgb2):
					point2.setAttribValue('Cd',(rgb2[0]+rgb[0],rgb2[1]+rgb[1],rgb2[2]+rgb[2]))
					prim.setAttribValue('Flow',0)
					if int(loc[1]) == 0:
						prim2.setAttribValue('Flow',1)
					else:
						prim2.setAttribValue('Flow',-1)

'''
Helper function to pass color to neighboring points
If a point has a color added to it, return true
'''
def _passColor(flow_direction, prim, geometry):
	total_verts = len(prim.vertices()) - 1
	if flow_direction == 1:
		i = 0
		vertices = prim.vertices()
	else:# prim.attribValue('Flow') == -1:
		i = total_verts
		vertices = reversed(prim.vertices())
	for vertex in vertices:
		
		if i > 0 and i < total_verts:
			point = vertex.point()
			point2 = prim.vertices()[i+1].point()
			point3 = prim.vertices()[i-1].point()

			rgb = point.attribValue('Cd')
			rgb_sum = _lum(rgb)
			rgb2 = point2.attribValue('Cd')
			rgb2_sum = _lum(rgb2)
			rgb3 = point3.attribValue('Cd')
			rgb3_sum = _lum(rgb3)

			found = False
			if not _colorEqual(rgb,rgb2):
				point2.setAttribValue('Cd',(rgb2[0]+rgb[0],rgb2[1]+rgb[1],rgb2[2]+rgb[2]))
				found = True
			if not _colorEqual(rgb,rgb3):
				point3.setAttribValue('Cd',(rgb3[0]+rgb[0],rgb3[1]+rgb[1],rgb3[2]+rgb[2]))
				found = True
			if found:
				return True

		elif i == 0:
			point = vertex.point()
			rgb = point.attribValue('Cd')
			
			point2 = prim.vertices()[i+1].point()
			rgb2 = point2.attribValue('Cd')
			
			rgb_sum = (rgb2[0]+rgb[0],rgb2[1]+rgb[1],rgb2[2]+rgb[2])

			if not _colorEqual(rgb,rgb2):
				point2.setAttribValue('Cd',rgb_sum)
				return True
			else:
				if flow_direction == -1:
					_checkForEndPoint(i,rgb_sum,prim,flow_direction,geometry)

		elif i == total_verts:
			point = vertex.point()
			rgb = point.attribValue('Cd')
			
			point2 = prim.vertices()[i-1].point()
			rgb2 = point2.attribValue('Cd')

			rgb_sum = (rgb2[0]+rgb[0],rgb2[1]+rgb[1],rgb2[2]+rgb[2])
			
			if not _colorEqual(rgb,rgb2):
				point2.setAttribValue('Cd',rgb_sum)
				return True
			else:
				if flow_direction == 1:
					_checkForEndPoint(i,rgb_sum,prim,flow_direction,geometry)

		i = i + flow_direction

'''
Main loop for the solver. Call this in Python SOP
'''
def solverStep(currentGeo, previousGeo):
	
	geo = hou.pwd().geometry()
	
	for prim in geo.prims():
		found = False
		if prim.attribValue('Flow') is not 0 and len(prim.vertices()) > 2:
			found = _passColor(prim.attribValue('Flow'),prim,geo)
		if found:
			continue
	return












































