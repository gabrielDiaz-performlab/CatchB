import viz
import vizact
import vizshape
import smi_beta
import vizconnect
import numpy as np
import math

class gazeVector():
	def __init__(self, eyeTracker, eye, parentNode, renderToWindows = None,gazeVectorColor=viz.RED):
		
		self.eye = eye
		self.eyeTracker = eyeTracker
		self.renderToWindows = renderToWindows
		
		#Creating a line
		viz.startLayer(viz.LINES)
		viz.lineWidth(4)#Set the size of the lines. 
		viz.vertex(0,0,0)
		viz.vertex(0,0,3)
		viz.vertexColor(gazeVectorColor)
		self.gazeLine = viz.endLayer()
		self.gazeLine.visible(True)
		#self.gazeLine.setScale(1,1,1)

		if( self.renderToWindows ):
			self.gazeLine.renderOnlyToWindows(self.renderToWindows)
		self.gazeLine.setParent(parentNode)
		

	def toggleUpdate(self):
		
		def moveGazeVector():
			
			gazeSamp = []
			
			gazeSamp = self.eyeTracker.getLastSample()
			
			if( gazeSamp is None ):
				return
				
			if( self.eye == viz.LEFT_EYE):
				gazeSamp = gazeSamp.leftEye;
			elif( self.eye == viz.RIGHT_EYE ):
				gazeSamp = gazeSamp.rightEye;
			
			
			#3D gaze is provided as a normalized gaze direction vector (gazeDirection) and a gaze base point (gazeBasePoint).
			#Gaze base point is given in mm with respect to the origin of the eyetracker coordinate system.
			# Note: you must flip X
			viewPos_XYZ = np.array(viz.MainView.getPosition(), dtype = float)
			gazeDir_XYZ = np.array([ -gazeSamp.gazeDir_x, gazeSamp.gazeDir_y, gazeSamp.gazeDir_z], dtype = float)
			pupilPos_XYZ = [-gazeSamp.pupilPos_x, gazeSamp.pupilPos_y, gazeSamp.pupilPos_z]
			pupilPos_XYZ = np.divide(pupilPos_XYZ, 1000)

			# Create a node3D
			#gazePoint_XYZ = [viewPos_XYZ[0] + gazeDir_XYZ[0], viewPos_XYZ[1] + gazeDir_XYZ[1], viewPos_XYZ[2] + gazeDir_XYZ[2]]
			gazePoint_XYZ = [gazeDir_XYZ[0], gazeDir_XYZ[1], gazeDir_XYZ[2]]
			#gazePoint_XYZ = np.multiply(1.0, gazePoint_XYZ)
			
			#self.gazeLine.setVertex(0, pupilPos_XYZ[0], pupilPos_XYZ[1], pupilPos_XYZ[2], viz.ABS_PARENT)
			self.gazeLine.setVertex(0, 0, 0, viz.ABS_PARENT)
			self.gazeLine.setVertex(1, gazePoint_XYZ[0], gazePoint_XYZ[1], gazePoint_XYZ[2], viz.ABS_PARENT)
			
			#print 'GazePoint=[', gazePoint_XYZ, '],[', pupilPos_XYZ,']' 
			
			
#		self.node3D.enable(viz.RENDERING)
		
		self.updateAct = vizact.onupdate(viz.PRIORITY_INPUT+1,moveGazeVector)

class gazeSphere():
	def __init__(self,eyeTracker,eye,parentNode,renderToWindows = None,sphereColor=viz.RED):
		
		self.sizeInDegrees = 0.5
		self.sphereDistance = 1
		self.renderToWindows = renderToWindows
		from math import tan, radians
		
		self.radius = tan(radians(self.sizeInDegrees)) * self.sphereDistance
		#with viz.cluster.MaskedContext(viz.CLIENT1):
		self.node3D = vizshape.addSphere(radius=self.radius, color = sphereColor, alpha = 0.4)
		
		if( self.renderToWindows ):
			self.node3D.renderOnlyToWindows(self.renderToWindows)
		
		self.node3D.disable(viz.RENDERING)
		
		self.updateAct = []
		
		self.eyeTracker = eyeTracker
		self.eye = eye
		self.node3D.setParent(parentNode)
		
		
	def toggleUpdate(self):
	
		def moveGazeSphere():
			
			gazeSamp = []
			
			#if( self.eye == viz.BOTH_EYE):
			gazeSamp = self.eyeTracker.getLastSample()
			
			if( gazeSamp is None ):
				return
				
			#timestamp = gazeSamp.timestamp
			
			if( self.eye == viz.LEFT_EYE):
				gazeSamp = gazeSamp.leftEye;
			elif( self.eye == viz.RIGHT_EYE ):
				gazeSamp = gazeSamp.rightEye;
			
			
			#3D gaze is provided as a normalized gaze direction vector (gazeDirection) and a gaze base point (gazeBasePoint).
			#Gaze base point is given in mm with respect to the origin of the eyetracker coordinate system.
			# Note: you must flip X
			gazeDirXYZ = [ -gazeSamp.gazeDir_x, gazeSamp.gazeDir_y, gazeSamp.gazeDir_z]
			gazePointXYZ = self.sphereDistance * gazeDirXYZ
			
			#with viz.cluster.MaskedContext(viz.CLIENT1):# show
			self.node3D.setPosition( gazePointXYZ,viz.ABS_PARENT)
			
			
		self.node3D.enable(viz.RENDERING)
		
		self.updateAct = vizact.onupdate(viz.PRIORITY_INPUT+1,moveGazeSphere)


class calibrationTools():
	
	def __init__(self, parentNode):

		self.calibrationInProgress = False
		self.parentNode = parentNode
		self.minimumAngle = (15.0 * np.pi)/(60*180) # We want the calibration point subtend 5 arcmin to the subject's eye
		self.calibrationSphereRadius = 0.02
		#self.calibrationSphere = vizshape.addSphere(self.calibrationSphereRadius, color = viz.PURPLE)
		#self.setSphereRadius(0, 0, 0.02)
	def dotproduct(self, v1, v2):
	  return sum((a*b) for a, b in zip(v1, v2))
	def length(self, v):
	  return math.sqrt(self.dotproduct(v, v))

	def angle(self, v1, v2):
	  return math.acos(self.dotproduct(v1, v2) / (self.length(v1) * self.length(v2)))

	def calculateAngularError(self, node1, node2, textObject):
		#V1 = Ball_Pos_XYZ[:,FrameNumber] - cyclopEyeNode.getPosition(viz.ABS_GLOBAL)
		#V2 = eyeGazeSphere.getPosition(viz.ABS_GLOBAL) - cyclopEyeNode.getPosition(viz.ABS_GLOBAL)
		#V2 = [a - b for a, b in zip(eyeGazeSphere.getPosition(viz.ABS_GLOBAL), cyclopEyeNode.getPosition(viz.ABS_GLOBAL))]
		# XYZ = [l1[idx][0] - l2[idx][0] , l1[idx][1] - l2[idx][1], l1[idx][2] - l2[idx][2]  for idx in range(len(l1))]
		vector1 = node1.getPosition(viz.ABS_PARENT)
		#V1 = [a - b for a, b in zip(vector1, self.parentNode.getPosition(viz.ABS_GLOBAL))]
		V1 = vector1
		if (node2 == 0.0):
			V2 = self.calibrationPositions[self.calibrationCounter,:]# + self.parentNode.getPosition(viz.ABS_GLOBAL)
		else:
			#V2 = vector2.getPosition()
			V2 = [b - a for a, b in zip(node1.getPosition(viz.ABS_GLOBAL), node2.getPosition(viz.ABS_GLOBAL))]
		self.errorAngle = np.multiply(self.angle(V1,V2), 180/np.pi)
		#print 'Angular Error = %.2f %c'%(errorAngle, u"\u00b0")
		#print 'Angular Error = %.2f %c'%(self.errorAngle, u"\u00b0")
		textObject.message('AE = %.2f %c'%(self.errorAngle, u"\u00b0"))
		textObject.setPosition(-3, 0, 5, viz.ABS_PARENT)
		if ( self.errorAngle < 15 ):
			textObject.color(self.errorAngle/15.0, 1 - self.errorAngle/15.0,0)
		else:
			textObject.color(1, 0, 0)


	def create3DCalibrationPositions(self, xRange, yRange, zRange, numberOfGridPoints):
		x = np.linspace(xRange[0], xRange[1], numberOfGridPoints)
		y = np.linspace(yRange[0], yRange[1], numberOfGridPoints)
		z = np.linspace(zRange[0], zRange[1], numberOfGridPoints)

		points = np.array([])
		points.resize(1,3)
		for i in x:
			for j in y:
				for k in z:
					points = np.vstack((points, [i,j,k]))

		points = np.delete(points, 0, 0)
		self.calibrationPositions = points
		self.numberOfCalibrationPoints = self.calibrationPositions.shape[0]
		print 'calibration points', points
		print '# of Calibration Points =', self.numberOfCalibrationPoints


	def myCalibrationMethod(self):
		
		if ( self.calibrationInProgress == False):
			self.calibrationInProgress = True
			self.calibrationCounter = 0
			self.calibrationSphere = vizshape.addSphere(self.calibrationSphereRadius, color = viz.PURPLE)
			self.calibrationSphere.setParent(self.parentNode)
			self.setSphereRadius(self.parentNode.getPosition(viz.ABS_GLOBAL), self.calibrationPositions[self.calibrationCounter,:], 0)
			print 'FirstPos', self.calibrationPositions[self.calibrationCounter,:]
			newPos = [self.calibrationPositions[self.calibrationCounter,0], self.calibrationPositions[self.calibrationCounter,1], self.calibrationPositions[self.calibrationCounter,2]]
			self.calibrationSphere.setPosition(newPos[0], newPos[1], newPos[2],viz.ABS_PARENT)
			print 'Calibration Procedure Started'
		else:
			self.calibrationInProgress = False
			self.calibrationCounter = 0
			self.calibrationSphere.remove()
			print 'Quit Calibration!!'
			
	def updateCalibrationPoint(self):
		
		if(self.calibrationInProgress == True):
			self.calibrationCounter +=1
			if( self.calibrationCounter < self.numberOfCalibrationPoints ):
				newPos = [self.calibrationPositions[self.calibrationCounter,0], self.calibrationPositions[self.calibrationCounter,1], self.calibrationPositions[self.calibrationCounter,2]]
				self.calibrationSphere.setPosition(newPos[0], newPos[1], newPos[2],viz.ABS_PARENT)
				self.setSphereRadius(self.parentNode.getPosition(viz.ABS_GLOBAL), self.calibrationPositions[self.calibrationCounter,:], 0)
				#print 'Calibratring for Point[%d]' %(self.calibrationCounter), 'at [%f %f %f]' % (newPos[0], newPos[1], newPos[2])
			else:
				self.calibrationInProgress = False
				self.calibrationCounter = 0
				self.calibrationSphere.remove()
				print 'Calibration Done Successfully'
			
		
	def setSphereRadius(self, eyePos, targetPos, radius):

		if ( radius  == 0 ):
			distance = np.linalg.norm(targetPos)
			self.calibrationSphereRadius = distance * np.tan(self.minimumAngle)
			print 'Radius Changed to ', self.calibrationSphereRadius,' theta = ', 0.5 * 180 * np.arctan( self.calibrationSphereRadius/distance )/np.pi
		else:
			self.calibrationSphereRadius = radius
			print '==>Radius Changed to ', self.calibrationSphereRadius
		ratio = self.calibrationSphereRadius/0.02
		self.calibrationSphere.setScale([ratio, ratio, ratio], viz.ABS_PARENT)
