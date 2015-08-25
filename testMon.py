

import viz

viz.go(viz.FULLSCREEN)

#viz.window.setFullscreenMonitor(3)

with viz.cluster.MaskedContext(viz.MASTER):
	viz.window.setFullscreenMonitor(1)
	text_2D_screen = viz.addText('MASTER')

	
with viz.cluster.MaskedContext(viz.CLIENT1):
	viz.window.setFullscreenMonitor(3)
	#text_2D_screenB = viz.addText('client')