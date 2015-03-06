import viz
import vizact
import vizshape
import smi_beta
import vizconnect



class gazeSphere():
	def __init__(self,eyeTracker,eye,parentNode,renderToWindows = None,sphereColor=viz.RED):
		
		self.sizeInDegrees = 1
		self.sphereDistance = 1
		self.renderToWindows = renderToWindows
		from math import tan, radians
		
		self.radius = tan(radians(self.sizeInDegrees)) * self.sphereDistance
		
		#with viz.cluster.MaskedContext(viz.CLIENT1):
		self.node3D = vizshape.addSphere(radius=self.radius, color = sphereColor)
		
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
		
		self.updateAct = vizact.onupdate(viz.PRIORITY_LINKS+1,moveGazeSphere)

#
#class gazeViz():
#	
#	def __init__(self,eyeTracker):
#			
#		self.both_sphere = gazeSphere(eyeTracker,viz.BOTH_EYE,viz.RED)
#		self.left_sphere = gazeSphere(eyeTracker,viz.LEFT_EYE,viz.RED)
#		self.right_sphere = gazeSphere(eyeTracker,viz.RIGHT_EYE,viz.RED)
#		
		
#	def toggleDrawGaze(self,eyeTracker, eye = viz.BOTH_EYE):
#		
#		if( self.parentsSet is False):
#			print 'Parents not yet set!  use gazeTools.setParents()'
#		
#		sphere = []
#		
#		if( eye == viz.BOTH_EYE ): 
#			sphere = self.both_sphere
#
#		elif( eye == viz.RIGHT_EYE ): 
#			sphere = self.right_sphere
#			
#		elif( eye == viz.LEFT_EYE ): 
#			sphere = self.left_sphere
#			
#		def drawGaze(sphere):
#			gazeMat = eyeTracker.getLastGazeMatrix(eye)
#			gazeMat.postMult(viz.MainView.getMatrix())
#			
#			sphere.node3D.setPosition( gazeMat.getPosition() + [0,0,2],viz.ABS_PARENT)
#		
#		sphere.node3D.enable(viz.RENDERING)
#		sphere.updateAct = vizact.onupdate(viz.PRIORITY_LINKS+1,drawGaze,sphere)

