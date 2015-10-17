import numpy as np
import hou
import threading
import math
import random

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
Divide list into n sized chunks
Can be accessed using .next() call on generator object
'''
def chunks(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

'''
Multithreaded create attributes.
Operates on 1/4 of the set per thread.
'''
def _threadCreateAttribute(primitives,geo,end_points,radius):
	stream_starts = {}
	stream_ends = {}
	i = 0
	for prim in primitives:
		stream_starts[str(i)] = ''
		stream_ends[str(i)] = ''
		i = i+1
	
	i = 0
	for prim in primitives:
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
				stream_ends[str(i)] = stream_ends[str(i)] + stream_id + ' ' + '0' + ','

			pointB = end_points[stream_id]['end'][1]
			if isInside(pointA,pointB,radius):
				stream_ends[str(i)] = stream_ends[str(i)] + stream_id + ' ' + str(end_points[stream_id]['end'][0]) + ','

		prim.setAttribValue('StartNeighbors',stream_starts[str(i)])
		prim.setAttribValue('EndNeighbors',stream_ends[str(i)])

		i = i+1

'''
Read in curve data and create attributes for visualization.
Find start points and end points within a spherical radius of each start and end.
'''
def createAttributes(radius,singleThreaded=False):
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
	if geo.findPrimAttrib('CurrentPoint') is None:
		geo.addAttrib(hou.attribType.Prim,'CurrentPoint',-1)
	if geo.findGlobalAttrib('ActivePrims') is None:
		geo.addAttrib(hou.attribType.Global,'ActivePrims', (0) )
	
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
	if singleThreaded:
		_threadCreateAttribute(geo.prims(),geo,end_points,radius)

	else:
		primitives = chunks(geo.prims(),len(geo.prims())/3)
		threads = []
		for i in range(3):
			t = threading.Thread(target =_threadCreateAttribute, args=(primitives.next(),geo,end_points,radius, ))
			threads.append(t)
			t.start()
		#t.join()

	#for t in threads:
	#	t.join()

	groupStartEndPoints(geo)

def mergePrimTuples(current, add, remove):
	output = ()
	for val in current:
		if val != remove:
			output = output + (val,)
	for val in add:
		output = output + (val,)
	return output

def sumColors(color1, color2):
	r = color1[0] + color2[0]
	r = 1 if r > 1 else r
	g = color1[1] + color2[1]
	g = 1 if g > 1 else g
	b = color1[2] + color2[1]
	b = 1 if b > 1 else b

	return ((r,g,b))
	

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
		primAddList = ()
		primRemoveList = ()
		for end in ends_list:
			loc = end.split()
			if len(loc) > 0:
				prim2 = geometry.prims()[int(loc[0])]
				point2 = prim2.vertices()[int(loc[1])].point()
				prim2.setAttribValue('Flow',1)
				rgb2 = point2.attribValue('Cd')
				
				rgbSum = sumColors(rgb,rgb2)

				point2.setAttribValue('Cd',rgbSum)

				if int(loc[1]) == 0:
					prim2.setAttribValue('Flow',1)
					prim2.setAttribValue('CurrentPoint',0)
					
				else:
					prim2.setAttribValue('Flow',-1)
					prim2.setAttribValue('CurrentPoint',len(prim2.vertices())-1)

				primAddList = primAddList + (int(loc[0]),)

		primTuple = geometry.intListAttribValue('ActivePrims')
		newActiveTuple = mergePrimTuples(primTuple, primAddList, prim.number())
		geometry.findGlobalAttrib('ActivePrims').setSize(len(newActiveTuple))
		geometry.setGlobalAttribValue('ActivePrims',newActiveTuple)
		prim.setAttribValue('Flow',0)



def listToString(theList):
	string = ""
	for item in theList:
		string = string + str(item)

def stringToList(string,delimiter=" "):
	splitString = string.split(delimiter)
	newList = []
	for string in splitString:
		newList.append(int(string))
	return newList

'''
Main loop for solver function. Updates all points.
'''
def solverStep():
	geo = hou.pwd().geometry()

	activePrims = geo.intListAttribValue('ActivePrims')


	# For each prim, look up current point and set next point based on flow direction.
	i = 0
	for index in activePrims:
		prim = geo.prims()[index]
		if hou.updateProgressAndCheckForInterrupt(int(float(i)/float(len(geo.prims()))*100)):
			break
		flowDir = prim.attribValue('Flow')
		if flowDir == 0:
			continue
		
		sizeOfPrim = len(prim.vertices())

		currentPoint = prim.attribValue('CurrentPoint')
		rgb1 = prim.vertices()[currentPoint].point().attribValue('Cd')

		nextPoint = currentPoint + flowDir

		# For all valid points that are not the end points of a stream
		if (currentPoint > 0 and currentPoint < sizeOfPrim - 1) or (currentPoint == 0 and flowDir == 1) or (currentPoint == sizeOfPrim-1 and flowDir == -1):
			rgb2 = prim.vertices()[nextPoint].point().attribValue('Cd')
			rgbSum = (sumColors(rgb1,rgb2))
			prim.vertices()[nextPoint].point().setAttribValue('Cd',rgbSum)
			prim.setAttribValue('CurrentPoint',nextPoint)
		# Jump to all the start points
		elif currentPoint == 0 and flowDir == -1:
			_checkForEndPoint(0,rgb1,prim,flowDir,geo)
		# Jump to all the end points
		elif currentPoint == sizeOfPrim-1 and flowDir == 1:
			_checkForEndPoint(sizeOfPrim-1,rgb1,prim,flowDir,geo)

		i = i+1

def startPoints():

	node = hou.pwd()
	geo = node.geometry()

	# Add code to modify contents of geo.
	# Use drop down menu to select examples.
	colors = [(1.0,0.0,0.0),(0.0,1.0,0.0),(0.0,0.0,1.0)]
	activeTuple = ()
	for i in range(len(colors)):
	    rand = random.randrange(0,len(geo.prims()))
	    geo.prims()[rand].vertices()[0].point().setAttribValue('Cd',colors[i])
	    geo.prims()[rand].setAttribValue('Flow',1)
	    geo.prims()[rand].setAttribValue('CurrentPoint',0)

	    activeTuple = activeTuple + (rand,)
	
	primTuple = geo.findGlobalAttrib('ActivePrims')
	primTuple.setSize(len(activeTuple))
	geo.setGlobalAttribValue('ActivePrims',activeTuple)






















