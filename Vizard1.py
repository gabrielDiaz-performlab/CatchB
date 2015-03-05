import smi_beta

def getGazePoint():# Get gaze matrix in local HMD coordinate system
	gazeMat = gaze.getLastGazeMatrix()

	# Transform gaze matrix into world coordinate system
	gazeMat.postMult(viz.MainView.getMatrix())

