import viz
import vizact
import vizshape
import smi
import vizconnect
import numpy as np
import math

nan = float('NaN')

class gazeVector():
	def __init__(self, eyeTracker, eye, parentNode, renderToWindows = None,gazeVectorColor=viz.RED):
		
		self.eye = eye
		self.eyeTracker = eyeTracker
		self.renderToWindows = renderToWindows
		
		#Creating a line
		viz.startLayer(viz.LINES)
		viz.lineWidth(7)#Set the size of the lines. 
		viz.vertex(0,0,0)
		viz.vertex(0,0,3)
		viz.vertexColor(gazeVectorColor)
		self.gazeLine = viz.endLayer()
		self.gazeLine.visible(True)
		#self.gazeLine.setScale(1,1,1)

#		if( self.renderToWindows ):
#			self.gazeLine.renderOnlyToWindows(self.renderToWindows)
		
		self.gazeLine.setParent(parentNode)
		
	def toggleUpdate(self):
		
		def moveGazeVector():
			
			gazeDirXYZ = False

			if( self.eye == viz.LEFT_EYE):
				gazeDirXYZ = self.eyeTracker.getLeftGazeDirection();
			elif( self.eye == viz.RIGHT_EYE ):
				gazeDirXYZ = self.eyeTracker.getRightGazeDirection();
			
			self.gazeLine.setVertex(0, 0, 0, viz.ABS_PARENT)
			self.gazeLine.setVertex(1, gazeDirXYZ[0], gazeDirXYZ[1], gazeDirXYZ[2], viz.ABS_PARENT)

		self.updateAct = vizact.onupdate(viz.PRIORITY_INPUT+1,moveGazeVector)

class gazeSphere():
	def __init__(self,eyeTracker,eye,parentNode,renderToWindows = None,sphereColor=viz.RED):
		
		self.sizeInDegrees = 1.0
		self.sphereDistance = 1
		self.renderToWindows = renderToWindows
		from math import tan, radians
		
		self.radius = tan(radians(self.sizeInDegrees)) * self.sphereDistance
		self.node3D = vizshape.addSphere(radius=self.radius, color = sphereColor, alpha = 0.4)
		
		if( self.renderToWindows ):
			self.node3D.renderOnlyToWindows(self.renderToWindows)
		
		self.node3D.disable(viz.RENDERING)
		
		self.updateAct = []
		
		self.eyeTracker = eyeTracker
		self.eye = eye
		
		if self.eye == viz.RIGHT_EYE:
			
			self.node3D.setReferenceFrame(viz.RF_VIEW)
			self.node3D.setPosition([IOD/2,0,0])
		
		elif self.eye == viz.LEFT_EYE:
			
			self.node3D.setReferenceFrame(viz.RF_VIEW)
			self.node3D.setPosition([-IOD/2,0,0])			

		
	def toggleUpdate(self):
	
		def moveGazeSphere():
			
			gazeDirXYZ = False

			if( self.eye == viz.LEFT_EYE):
				gazeDirXYZ = self.eyeTracker.getLeftGazeDirection();
			elif( self.eye == viz.RIGHT_EYE ):
				gazeDirXYZ = self.eyeTracker.getRightGazeDirection();
			
			if gazeDirXYZ == [nan,nan,nan]:
				self.node3D.alpha = 0
			else:
				self.node3D.alpha = 1
			
				#3D gaze is provided as a normalized gaze direction vector (gazeDirection) and a gaze base point (gazeBasePoint).
				#Gaze base point is given in mm with respect to the origin of the eyetracker coordinate system.
				# Note: you must flip X
				#gazeDirXYZ = [ -gazeSamp.gazeDirection.x, gazeSamp.gazeDirection.y, gazeSamp.gazeDirection.z]
				gazePointXYZ = self.sphereDistance * gazeDirXYZ
				
				#with viz.cluster.MaskedContext(viz.CLIENT1):# show
				self.node3D.setPosition( gazePointXYZ,viz.ABS_PARENT)
			
			
		self.node3D.enable(viz.RENDERING)
		
		self.updateAct = vizact.onupdate(viz.PRIORITY_INPUT+1,moveGazeSphere)


class calibrationTools():
	
	def __init__(self, parentNode,cyclopEyeSphere,renderToWindows = None, config = None, room = None):

		self.config = config
		self.room = room
		self.calibrationInProgress = False
		self.parentNode = parentNode
		self.renderToWindows = renderToWindows
		self.calibrationSphere = None

		self.cyclopEyeSphere = cyclopEyeSphere
		
		self.minimumAngle = float(self.config.expCfg['room']['minimumStimuliSize'])
		self.minimumAngle = (self.minimumAngle * np.pi)/(60*180) # We want the calibration point subtend 15 arcmin to the subject's eye
		
		self.calibTargetSizeDegs = float(self.config.expCfg['room']['calibTargetSizeDegs'])
		
		self.localAction = None
		self.initialValue = 0.02
		self.calibrationSphereRadius = self.initialValue
		self.calibrationBlockCounter = 900
		self.calibrationCounter = 0
		
		self.maximumAngularError = float(self.config.expCfg['room']['maximumAngularError'])
		self.textObjectPosition = map(float,self.config.expCfg['room']['textObjectPosition'])

		self.calibrationPositionRange_X = self.config.expCfg['room']['calibrationPointsRange_X']
		self.calibrationPositionRange_Y = self.config.expCfg['room']['calibrationPointsRange_Y']
		self.calibrationDepth = self.config.expCfg['room']['calibrationDepth']
		self.numberOfCalibrationPoints =  float(self.config.expCfg['room']['calibrationPointPerPlane'])
		
		self.create3DCalibrationPositions(self.calibrationPositionRange_X, 
			self.calibrationPositionRange_Y, 
			self.calibrationDepth,
			self.numberOfCalibrationPoints)


	def dotproduct(self, v1, v2):
	  return sum((a*b) for a, b in zip(v1, v2))

	def length(self, v):
	  return math.sqrt(self.dotproduct(v, v))

	def angle(self, v1, v2):
	  return math.acos(self.dotproduct(v1, v2) / (self.length(v1) * self.length(v2)))

	def calculateAngularError(self, node1, node2, textObject):
		
		vector1 = node1.getPosition(viz.ABS_PARENT)
		V1 = vector1
		
		if (node2 == 0.0):
			if ( self.calibrationCounter < 27 ):
				V2 = self.calibrationPositions[self.calibrationCounter,:]# + self.parentNode.getPosition(viz.ABS_GLOBAL)
			else:
				V2 = self.calibrationSphere.getPosition()
		else:
			V2 = [b - a for a, b in zip(node1.getPosition(viz.ABS_GLOBAL), node2.getPosition(viz.ABS_GLOBAL))]
		
		self.errorAngle = np.multiply(self.angle(V1,V2), 180/np.pi)
		
		#print 'Angular Error = %.2f %c'%(errorAngle, u"\u00b0")
		#print 'Angular Error = %.2f %c'%(self.errorAngle, u"\u00b0")

		textObject.message('AE = %.1f %c'%(self.errorAngle, u"\u00b0"))

		textObject.setPosition(self.textObjectPosition, viz.ABS_PARENT)
		
		if ( self.errorAngle < self.maximumAngularError ):
			textObject.color(self.errorAngle/self.maximumAngularError, 1 - self.errorAngle/self.maximumAngularError, 0)
		else:
			textObject.color(viz.RED)

	
	def create3DCalibrationPositions(self,xRange,yRange,distance,numberOfGridPoints):
		#, xRange, yRange, zRange, numberOfGridPoints):
#		
#		xRange = 20
#		yRange = 20
#		numberOfGridPoints = 9
#		distance = 3

		pi = np.pi

		def calcLoc(xDegs,yDegs,dist):
			xLoc =  dist * np.sin(np.deg2rad(90.-yDegs)) * np.cos(np.deg2rad(90.-xDegs)) #np.rad2deg(np.sin(np.deg2rad(xDegs)) * dist)
			zLoc =  dist * np.sin(np.deg2rad(90.-yDegs)) * np.sin(np.deg2rad(90.-xDegs)) 
			yLoc =  dist * np.cos(np.deg2rad(90.-yDegs)) 
			return [xLoc,yLoc,zLoc]
				
		
		x = np.tile(np.linspace(-xRange/2, xRange/2, int(np.sqrt(numberOfGridPoints))),3)
		y = np.repeat(np.linspace(-yRange/2, xRange/2, int(np.sqrt(numberOfGridPoints))),3)
		y = y-10

		self.calibrationPositions = np.array([calcLoc(xx,yy,dd) for xx,yy,dd in zip(x,y,[distance]*len(x))],dtype=np.float)
		self.numberOfCalibrationPoints = len(self.calibrationPositions)

	def toggleRoomWallsVisibility(self):

		self.room.ceiling.node3D.visible(viz.TOGGLE)
		self.room.floor.node3D.visible(viz.TOGGLE)
		self.room.wall_PosZ.node3D.visible(viz.TOGGLE)
		self.room.wall_NegZ.node3D.visible(viz.TOGGLE)
		self.room.wall_PosX.node3D.visible(viz.TOGGLE)
		self.room.wall_NegX.node3D.visible(viz.TOGGLE)
		
	def checkActionDone(self):
		distance = np.array(self.calibrationSphere.getPosition()) - np.array([-3.0,0.0,6.0])
		#print 'Distance', distance
		if(abs( self.length(distance)) < 0.1):
			self.calibrationInProgress = False
			self.localAction.remove()
			self.text_object.remove()
			self.calibrationCounter = 0

			self.targetMovingAction.remove()
			self.calibrationCounter = 100
			self.calibrationSphere.remove()
			self.toggleRoomWallsVisibility()
			print 'Quit Dynamic Calibration!!'
			
	def dynamicCalibrationMethod(self):
		
		if ( self.calibrationInProgress == False ):
			self.calibrationInProgress = True
			self.toggleRoomWallsVisibility()
			self.calibrationCounter = 27
			self.calibrationSphereRadius = self.initialValue
			self.calibrationSphere = vizshape.addSphere(self.calibrationSphereRadius, color = viz.PURPLE)
			self.calibrationSphere.emissive(viz.PURPLE)
			self.calibrationSphere.setParent(self.parentNode)
			newPos = [-3,-.5,12]
			self.setSphereRadius(self.parentNode.getPosition(viz.ABS_GLOBAL), newPos, 0)
			self.calibrationSphere.setPosition(newPos[0], newPos[1], newPos[2],viz.ABS_PARENT)
			self.targetMovingAction = vizact.onupdate(viz.PRIORITY_INPUT+1, self.checkActionDone)

			self.text_object = viz.addText('')
			self.text_object.setParent(self.calibrationSphere)
			self.text_object.renderOnlyToWindows([self.renderToWindows])
			self.localAction = vizact.onupdate(viz.PRIORITY_INPUT+1,self.calculateAngularError, self.cyclopEyeSphere.node3D, 0.0, self.text_object)#self.currentTrial.ballObj.node3D

			print 'Dynamic Calibration Procedure Started'
			#Use a moveTo action to move a node to the point [0,0,25] at 2 meters per second  
			self.moveAction = vizact.moveTo([-3,-0.5,12],speed=2)
			self.calibrationSphere.addAction(self.moveAction)
			self.moveAction = vizact.moveTo([3,-0.5,12],speed=2)
			self.calibrationSphere.addAction(self.moveAction)
			self.moveAction = vizact.moveTo([3,3,12],speed=2)
			self.calibrationSphere.addAction(self.moveAction)
			self.moveAction = vizact.moveTo([-3,3,12],speed=2)
			self.calibrationSphere.addAction(self.moveAction)
			self.moveAction = vizact.moveTo([-3,-0.5,12],speed=2)
			self.calibrationSphere.addAction(self.moveAction)

			self.moveAction = vizact.moveTo([-3,-0.5,6],speed=2)
			self.calibrationSphere.addAction(self.moveAction)
			self.moveAction = vizact.moveTo([3,-0.5,6],speed=2)
			self.calibrationSphere.addAction(self.moveAction)
			self.moveAction = vizact.moveTo([3,3,6],speed=2)
			self.calibrationSphere.addAction(self.moveAction)
			self.moveAction = vizact.moveTo([-3,3,6],speed=2)
			self.calibrationSphere.addAction(self.moveAction)
			self.moveAction = vizact.moveTo([-3,0,6],speed=2)
			self.calibrationSphere.addAction(self.moveAction)



		else:
			self.localAction.remove()
			self.text_object.remove()
			self.calibrationInProgress = False
			self.calibrationCounter = 0
			self.calibrationSphere.remove()
			self.toggleRoomWallsVisibility()
			print 'Quit Dynamic Calibration!!'


	def staticCalibrationMethod(self):
		
		if ( self.calibrationInProgress == False ):
			
			self.calibrationBlockCounter += 100
			self.toggleRoomWallsVisibility()
			self.calibrationInProgress = True
			self.calibrationCounter = 0
			self.calibrationSphereRadius = self.initialValue
			
			self.calibrationSphere = vizshape.addSphere(0.5, color = viz.PURPLE)
			self.calibrationSphere.emissive(viz.PURPLE)
			#self.calibrationSphere.setParent(self.parentNode)
	
			self.calibrationSphere.setReferenceFrame(viz.RF_VIEW)
			
		
			#self.setSphereRadius(self.parentNode.getPosition(viz.ABS_GLOBAL), self.calibrationPositions[self.calibrationCounter,:], .5)
			
			print 'FirstPos', self.calibrationPositions[self.calibrationCounter,:]
			
			newPos = [self.calibrationPositions[self.calibrationCounter,0], self.calibrationPositions[self.calibrationCounter,1], self.calibrationPositions[self.calibrationCounter,2]]
			self.calibrationSphere.setPosition(newPos[0], newPos[1], newPos[2],viz.ABS_PARENT)
			
			scale = 2 * np.arctan( (self.calibTargetSizeDegs/2.0) / self.calibrationDepth ) 
			print('Set scale to ' + str(scale))
			self.calibrationSphere.setScale([scale]*3)

			self.text_object = viz.addText('')
			self.text_object.setParent(self.calibrationSphere)
			self.text_object.renderOnlyToWindows([self.renderToWindows])
			
			self.localAction = vizact.onupdate(viz.PRIORITY_INPUT+1,self.calculateAngularError, self.cyclopEyeSphere, 0.0, self.text_object)#self.currentTrial.ballObj.node3D

			print 'Static Calibration Started'
		else:
			self.calibrationInProgress = False
			self.calibrationCounter = 0
			self.calibrationSphere.remove()
			self.localAction.remove()
			self.text_object.remove()
			self.toggleRoomWallsVisibility()
			print 'Quit Static Calibration!!'

			
	def updateCalibrationPoint(self):
		
		#if( self.calibrationInProgress == True ):
			
		self.calibrationCounter +=1
		newPos = [self.calibrationPositions[self.calibrationCounter,0], self.calibrationPositions[self.calibrationCounter,1], self.calibrationPositions[self.calibrationCounter,2]]
		self.calibrationSphere.setPosition(newPos[0], newPos[1], newPos[2],viz.ABS_PARENT)
		
		#self.setSphereRadius(self.parentNode.getPosition(viz.ABS_GLOBAL), self.calibrationPositions[self.calibrationCounter,:], 0)
		
		print 'Calibratring for Point[%d]' %(self.calibrationCounter), 'at [%f %f %f]' % (newPos[0], newPos[1], newPos[2])
		print 'Counter', self.calibrationBlockCounter + self.calibrationCounter
		return True
			
	def endCalibration(self):
		
		self.calibrationInProgress = False
		self.calibrationCounter = 0
		self.calibrationSphere.remove()
		self.localAction.remove()
		self.text_object.remove()
		self.toggleRoomWallsVisibility()
		#print 'Calibration Done Successfully'
		
#	def setSphereRadius(self, eyePos, targetPos, radius):
#
#		if ( radius  == 0 ):
#			distance = np.linalg.norm(targetPos)
#			self.calibrationSphereRadius = distance * np.tan(self.minimumAngle)
#			#print 'Radius Changed to ', self.calibrationSphereRadius,' theta = ', 0.5 * 180 * np.arctan( self.calibrationSphereRadius/distance )/np.pi
#		else:
#			self.calibrationSphereRadius = radius
#			#print '==>Radius Changed to ', self.calibrationSphereRadius
#		ratio = self.calibrationSphereRadius/self.initialValue
#		self.calibrationSphere.setScale([ratio, ratio, ratio], viz.ABS_PARENT)
#		print 'SetSphere to :',self.calibrationSphereRadius
#
