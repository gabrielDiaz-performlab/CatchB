import viz
import vizact
import vizshape




# Connect to Oculus HMD
import oculus
#hmd = oculus.Rift()

hmd = oculus.Rift(renderMode=oculus.RENDER_CLIENT)

model = viz.addChild('dojo.osgb')

# Launch graphics windowcc 
viz.setMultiSample(8)
viz.go(viz.FULLSCREEN)