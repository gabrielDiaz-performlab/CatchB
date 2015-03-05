import viz
import vizact
import vizshape
import smi_beta
import vizconnect



class gazeSphere():
	def __init__(self,eyeTracker,eye,parentNode,sphereColor=viz.RED):
		
		self.node3D = vizshape.addSphere(radius=0.01, color = sphereColor)
		self.node3D.disable(viz.RENDERING)
		
		self.updateAct = []
		
		self.eyeTracker = eyeTracker
		self.eye = eye
		self.node3D.setParent(parentNode)
		
	def toggleUpdate(self):
	
		def moveGazeSphere():
			
			gazeMat = self.eyeTracker.getLastGazeMatrix()
			
			# Move gaze matrix into world based coordinates
			# I've turned this off /bc I think it moves the point from 
			# head-centered to world-centered coords.  
			# We want head centered.
			#gazeMat.postMult(self.node3D.getParents()[0].getMatrix())
			
			headPos = self.node3D.getParents()[0].getPosition()
			
			# Draw point in head centered coordinates
			#self.node3D.setPosition( gazeMat.getPosition()) + gazeMat.getForward()*2,viz.ABS_PARENT)
			
			self.node3D.setPosition( headPos + gazeMat.getPosition(),viz.ABS_PARENT)
			
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

