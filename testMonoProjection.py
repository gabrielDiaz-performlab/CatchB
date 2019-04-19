

import viz
import vizact
import vizconnect
import vizshape
import viztask
import steamvr

#vizconnect.go('vizConnect/debug')

#############################################
model = viz.add('pit.osgb')

hmd = steamvr.HMD()
viz.link(hmd.getSensor(), viz.MainView)
#hmd.setIPD(0.0)
viz.MainWindow.ipd(0)
viz.go()

s = vizshape.addSphere(.1)
#s.setReferenceFrame(hmd.getSensor())
s.setPosition((0,.7,0))


## Create render texture for camera video feed
#video = viz.addRenderTexture()
#
## Create render node for camera
#cam = viz.addRenderNode()
##cam.setSize(1280*2,720*2)
#
#cam.setRenderTexture(video)
#cam.setProjectionMatrix(vizconnect.getRawTracker('head_tracker').getProjectionMatrix(viz.BOTH_EYE))
#
##cam.setMultiSample(viz.AUTO_COMPUTE)
##cam.setRenderLimit(viz.RENDER_LIMIT_FRAME)
#
## Get handle to screen object and apply video feed to it
#screen = vizshape.addBox([1,1,0,])#,top=False,bottom=False,left=False,right=False,back=False)
#
#screen.setScale([3,2.8,.1])
#
#screen.texture(video)
#
#screen.setReferenceFrame(viz.RF_VIEW)
#
#screen.setPosition([0,0,1])
##screen.setPosition([0,-.12,1])
#screen.renderToAllRenderNodesExcept([cam])
#screen.alpha(0.7)
#
#c1 = steamvr.getCameraList()[0]
#
#cam.renderOnlyIfNodeVisible([screen])
#
#hmd = vizconnect.getRawTracker('head_tracker')
#vdisp = vizconnect.getRawDisplay('rift_display')
#
#vdisp.getHorizontalFOV()
#vdisp.getVerticalFOV()
#
#hmd.getMatrix().getFrustum()
#
####
#
#sensor = steamvr.getExtension().getHMDList()[0]
#
#
####
#
#viz.MainWindow.stereo(viz.STEREO_HORZ | viz.HMD)
#
##window.setProjectionMatrix(sensor.getProjectionMatrix(eye), eye)
##window.setViewOffset(sensor.getViewOffset(eye), eye)
##window.stereo(viz.STEREO_HORZ | viz.HMD)