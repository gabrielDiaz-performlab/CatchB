"""
Example script demonstrating usage of SMI module.

Before running the script, please ensure the following:
	- You are running Vizrd 5.1 (32-bit)
	- Vizard is running with admin privileges
	- SMI iViewNG-HMD is installed in default "Program Files" location
	- Oculus 0.4.4 runtime is installed
	- Oculus Rift is in "Extend Desktop to the HMD" display modec

Key controls:cc
	C		- Calibrate
	G		- Toggle gaze marker
	Arrows	- Navigate
	Esc		- Exit
"""

import viz
import vizact
import vizshape
import smi_beta

# Launch graphics windowcc 
viz.setMultiSample(8)

model = viz.addChild('dojo.osgb')

# Launch graphics windowcc 
viz.setMultiSample(8)
viz.go(viz.FULLSCREEN)
#viz.go()

# Connect to Oculus HMD
import oculus
hmd = oculus.Rift(renderMode=oculus.RENDER_CLIENT)
if not hmd.getSensor():
	sys.exit('Oculus Rift not detected')

# Connect to SMI iView HMD
gaze = smi_beta.iViewHMD()

# Add indicators to place at gaze intersection point
point = vizshape.addSphere(radius=0.05, color=viz.RED)
point.disable(viz.INTERSECTION)

#lPoint = vizshape.addSphere(radius=0.05, color=viz.GREEN)
#rPoint.disable(viz.INTERSECTION)
#
#lPoint = vizshape.addSphere(radius=0.05, color=viz.BLUE)
#rPoint.disable(viz.INTERSECTION)

# Setup keyboard callbacks to display gaze calibration
vizact.onkeydown('c', gaze.calibrate)
vizact.onkeydown('g', point.visible, viz.TOGGLE)

# Add environment model
model = viz.addChild('dojo.osgb')
model.hint(viz.OPTIMIZE_INTERSECT_HINT)

class LookTarget(viz.VizNode):

	def __init__(self):

		intersect = vizshape.addSphere(radius=0.1)
		intersect.disable(viz.RENDERING)

		render = vizshape.addSphere(radius=0.075, color=viz.WHITE, parent=intersect)
		render.disable(viz.INTERSECTION)

		viz.VizNode.__init__(self, intersect.id)

		self._render = render
		self._looking = False

	def setLooking(self, looking):
		if looking != self._looking:
			self._looking = looking
			if looking:
				#self.runAction(vizact.sizeTo([1.5]*3, time=0.3, interpolate=vizact.easeOutStrong))
				self._render.runAction(vizact.fadeTo(viz.RED, time=0.3, interpolate=vizact.easeOutStrong))
			else:
				#self.runAction(vizact.sizeTo([1.0]*3, time=0.3, interpolate=vizact.easeOutStrong))
				self._render.runAction(vizact.fadeTo(viz.WHITE, time=0.3, interpolate=vizact.easeOutStrong))

	def getLooking(self):
		return self._looking

# Create look targets
for x in range(4):
	for y in range(4):
		target = LookTarget()
		target.setPosition(((x*0.5-0.75), (y*0.5+0.75), 2.5))

lastLookTarget = None
def updateGaze():
	"""Called every frame to update user gaze from latest sample"""
	global lastLookTarget
	
	
	# Get gaze matrix in local HMD coordinate system
	gazeMat = gaze.getLastGazeMatrix()

	# Transform gaze matrix into world coordinate system
	gazeMat.postMult(viz.MainView.getMatrix())

	# Intersect world gaze vector with scene
	line = viz.Line(begin = gazeMat.getPosition(), dir = gazeMat.getForward(), length=1000)
	info = viz.intersect(line.begin, line.end)
	if info.valid:

		# Place model at intersection point
		point.setPosition(info.point)

	# Update look target
	target = info.object if isinstance(info.object,LookTarget) else None
	if target != lastLookTarget:
		if lastLookTarget:
			lastLookTarget.setLooking(False)
		lastLookTarget = target
		if lastLookTarget:
			lastLookTarget.setLooking(True)

vizact.onupdate(viz.PRIORITY_LINKS+1, updateGaze)

# Setup navigation node and link to main view
navigationNode = viz.addGroup()
viewLink = viz.link(navigationNode, viz.MainView)
#viewLink.preMultLinkable(hmd.getSensor())

# Apply user profile eye height to view
profile = hmd.getProfile()
if profile:
	viewLink.setOffset([0,profile.eyeHeight,0])
else:
	viewLink.setOffset([0,1.8,0])

# Setup arrow key navigation
MOVE_SPEED = 2.0
def UpdateView():
	yaw,pitch,roll = viewLink.getEuler()
	m = viz.Matrix.euler(yaw,0,0)
	dm = viz.getFrameElapsed() * MOVE_SPEED
	if viz.key.isDown(viz.KEY_UP):
		m.preTrans([0,0,dm])
	if viz.key.isDown(viz.KEY_DOWN):
		m.preTrans([0,0,-dm])
	if viz.key.isDown(viz.KEY_LEFT):
		m.preTrans([-dm,0,0])
	if viz.key.isDown(viz.KEY_RIGHT):
		m.preTrans([dm,0,0])
	navigationNode.setPosition(m.getPosition(), viz.REL_PARENT)
vizact.ontimer(0,UpdateView)
