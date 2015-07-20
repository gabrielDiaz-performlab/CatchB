import viz
import vizshape
import vizmat
import math
import vizact
import Shadow

import physEnv

ft = .3048
inch = 0.0254
m = 1
eps = .01
yard = 1.09361
nan = float('NaN')
            
class room():
    def __init__(self,config=None):

        self.roomnode3D = viz.addGroup()
        self.walls = viz.addGroup()
        self.objects = viz.addGroup()
        
        ##################################
        ## Physical environment
        self.physEnv = physEnv.physEnv()
        ##################################
        
        if config==None:
            print 'No config'
            self.texPath = 'Resources/'
            self.roomWidth = 50.0; #self.wallPos_PosX-self.wallPos_NegX
            self.roomLength = 50.0; #self.wallPos_PosZ-self.wallPos_NegZ
            
            self.translateOnZ = 8.0;
            self.translateOnX = 0.0;
            
            self.wallPos_PosZ = self.roomLength/2 + self.translateOnZ;
            self.wallPos_NegZ = -self.roomLength/2 + self.translateOnZ;            
            self.wallPos_PosX = self.roomWidth/2 + self.translateOnX;
            self.wallPos_NegX = -self.roomWidth/2 + self.translateOnX;
            self.ceilingHeight = 25.0;
            self.drawStandingBox = False
        else:
            
            self.texPath = config.expCfg['experiment']['texturePath'] #'Resources/'
            
            roomSize_WHL = map(float,config.expCfg['room']['roomSize_WHL'])
            roomSize_WHL = [60, 60, 40]# FIX ME: (KAMRAN) 
            self.roomWidth = roomSize_WHL[0]
            self.ceilingHeight = roomSize_WHL[1]
            self.roomLength = roomSize_WHL[2]
            
            self.translateOnX = float(config.expCfg['room']['translateRoom_X'])
            self.translateOnZ = float(config.expCfg['room']['translateRoom_Z'])
            
            self.wallPos_PosZ = self.roomLength/2 + self.translateOnZ;
            self.wallPos_NegZ = -self.roomLength/2 + self.translateOnZ;            
            self.wallPos_PosX = self.roomWidth/2 + self.translateOnX;
            self.wallPos_NegX = -self.roomWidth/2 + self.translateOnX;
            
            self.drawStandingBox = config.expCfg['experiment']['drawStandingBox']
            
            self.isLeftHanded = float(config.expCfg['experiment']['isLeftHanded'])
            
            if( self.drawStandingBox  ):
                self.standingBoxOffset_X = config.expCfg['room']['standingBoxOffset_X']
                self.standingBoxSize_WHL = map(float, config.expCfg['room']['standingBoxSize_WHL'])
            
            self.shiftWorldRelToUser_XYZ = [0,0,0]
                    
            ####################################################################
            ##  Fill room with objects 
            
            self.visObjNames_idx = config.expCfg['visObj']['visObjVarNames']
            self.visObjShapes_idx = config.expCfg['visObj']['visObjShapes']
            self.visObjSizes_idx = eval(config.expCfg['visObj']['visObjSizesString'])
        
            self.fillWithVisObj()
            
            self.shadowSource = []
            self.lightSource = []
            self.setLighting()
            
            ####################################################################
        
        texScale = 1;
        
        wallTexPath = self.texPath  + 'tile_slate.jpg'
        floorTexPath = self.texPath + 'tile_wood.jpg'
        
        planeABCD = [0,-1,0,-self.ceilingHeight]
        self.ceiling = wall(self.physEnv,[self.roomWidth,self.roomLength],[1,0,0,-90],
                                [self.translateOnX,self.ceilingHeight,self.translateOnZ],
                                wallTexPath,texScale,planeABCD);        
                                
        planeABCD = [0,0,-1,-self.wallPos_PosZ]
        self.wall_PosZ = wall(self.physEnv,[self.ceilingHeight,self.roomWidth],[0,0,1,90],
                                [self.translateOnX,self.ceilingHeight/2, self.wallPos_PosZ],
                                wallTexPath,texScale,planeABCD);
       
        planeABCD = [0,0,1,self.wallPos_NegZ] 
        self.wall_NegZ = wall(self.physEnv,[self.roomWidth,self.ceilingHeight],[0,1,0,180],
                                [self.translateOnX,self.ceilingHeight/2, self.wallPos_NegZ],
                                wallTexPath,texScale,planeABCD);
        
        planeABCD = [-1,0,0,-self.wallPos_PosX] 
        self.wall_PosX = wall(self.physEnv,[self.roomLength,self.ceilingHeight],[0,1,0,90],
                                [self.wallPos_PosX,self.ceilingHeight/2,self.translateOnZ ],
                                wallTexPath,texScale,planeABCD);
        
        planeABCD = [1,0,0,self.wallPos_NegX] 
        self.wall_NegX = wall(self.physEnv,[self.roomLength,self.ceilingHeight],[0,-1,0,90],
                                [self.wallPos_NegX,self.ceilingHeight/2,self.translateOnZ ],
                                wallTexPath,texScale,planeABCD);
       
        planeABCD = [0,1,0,0]
        self.floor = wall(self.physEnv,[self.roomWidth,self.roomLength],[1,0,0,90],
                                [self.translateOnX,0, self.translateOnZ],
                                floorTexPath,texScale,planeABCD);
                                
        self.floor.node3D.setParent(self.walls)
        self.ceiling.node3D.setParent(self.walls)
        self.wall_PosZ.node3D.setParent(self.walls)
        self.wall_NegZ.node3D.setParent(self.walls)
        self.wall_PosX.node3D.setParent(self.walls)
        self.wall_NegX.node3D.setParent(self.walls)
        
        self.walls.setParent( self.roomnode3D )
        self.objects.setParent( self.roomnode3D )
        
        if( self.drawStandingBox ):
            self.createStandingBox()
        
    def fillWithVisObj(self):
        # This little bit of code fills the room with objects specified in the config file
        
        
        for idx in range(len(self.visObjNames_idx)):
                if( len(self.visObjNames_idx[idx])>0 ):
                    execString = 'self.' + self.visObjNames_idx[idx] + ' = visObj(self,self.visObjShapes_idx[idx],self.visObjSizes_idx[idx])'
                    print 'VisEnv:Room: Added ' + self.visObjNames_idx[idx]
                    exec(execString)
        
    def createStandingBox(self):
        
            
            # Draw the standing box
            
            boxSizeInfo = [ self.standingBoxSize_WHL[0], self.standingBoxSize_WHL[1],self.standingBoxSize_WHL[2]]
            
            self.standingBox = vizshape.addBox( boxSizeInfo,color=viz.GREEN,splitFaces = True,back=True)
            self.standingBox.emissive([0,1,0])
            self.standingBox.alpha(0.5)
            
            if( self.isLeftHanded ): self.standingBoxOffset_X *= -1;
            
            self.standingBox.setPosition(float(-self.standingBoxOffset_X),self.standingBoxSize_WHL[1]/2,.01)            

            self.standingBox.color(1,0,0,node='back')            
            self.standingBox.emissive(1,0,0,node='back')
            self.standingBox.alpha(0.7,node='back')

            self.standingBox.setParent(self.objects)
            #self.standingBox.disable(viz.CULLING)
            self.standingBox.disable(viz.CULL_FACE)

            
        
   
        
    def setLighting(self):
        
        viz.MainView.getHeadLight().disable()
        #viz.MainView.get
        self.lightSource = viz.addLight() 
        self.lightSource.enable() 
        self.lightSource.position(0, self.ceilingHeight, 0) 
        self.lightSource.spread(180) 
        self.lightSource.intensity(2)
    
        
        ### ADD A SHADOW
        #SHADOW_RES = 256*10
        SHADOW_RES = 100*10
        SHADOW_PROJ_POS = (0, self.ceilingHeight, 0)
        SHADOW_AREA = (self.roomWidth,self.roomLength)
        
        #Create shadow projector
        self.shadowSource = Shadow.ShadowProjector(size=SHADOW_RES,pos=SHADOW_PROJ_POS,area=SHADOW_AREA)

class wall():
    def __init__(self,physEnv,dimensions,axisAngle,position,texPath,texScale,planeABCD):
        
        # A wall object invludes a specialized node3D
        # This node3D is actually a texQuad

        ################################################################################################
        ################################################################################################
        ## Set variables
        
        self.dimensions = dimensions;
        self.axisAngle = axisAngle;
        self.position = position;
        self.texPath = texPath;
        self.texScale = texScale;
        
        ################################################################################################
        ################################################################################################
        ##  Create node3D: a texture quad
        
        self.node3D = viz.addTexQuad()
        self.node3D.setScale(dimensions[0],dimensions[1])
        self.node3D.setPosition(position)
        self.node3D.setAxisAngle(axisAngle)
        self.node3D.disable(viz.DYNAMICS)
        self.node3D.enable([viz.LIGHTING,viz.CULL_FACE])

        # Put texture on the quad  
        matrix = vizmat.Transform()
        matrix.setScale([dimensions[0]/texScale,dimensions[1]/texScale,texScale])
        
        self.node3D.texmat(matrix)
        
        self.texObj = viz.addTexture(texPath)
        self.texObj.wrap(viz.WRAP_T, viz.REPEAT)
        self.texObj.wrap(viz.WRAP_S, viz.REPEAT)
        self.node3D.texture(self.texObj)
        
        ################################################################################################
        ################################################################################################
        ##  Create physNode plane
        
        self.physNode = physEnv.makePhysNode('plane',planeABCD)
        
class visObj(viz.EventClass):
    def __init__(self,room,shape,size,position=[0,.25,-3],color=[.5,0,0],alpha = 1):
       
        
        ################################################################################################
        ################################################################################################
        ## Set variables
        
        self.elasticity = 1;
        self.color_3f = color
        self.position = position
        self.shape = shape
        self.alpha = alpha
        self.isDynamic = 0
        self.isVisible = 1
        self.inFloorCollision = 0
        
        # Note that size info is particular to the shape
        # For ball, just a radius
        # for box, lenght width and height
        # etc.
        
        self.size = size
        self.parentRoom = room;
        
        self.node3D = 0
        self.obj = []
            
        ################################################################################################
        ################################################################################################
        ## Variables related to automated updating with physics or motion capture
        
        self.updateAction = 0
        
        ################################################################################################
        ################################################################################################
        ## Create visual object
        
        self.makeBasicVizShape()
        #self.node3D.color(self.color_3f)
        self.setColor(self.color_3f)
        self.node3D.visible(True)

        ## Create physical object
        self.node3D.dynamic() # This command speeds up rendering, supposedly    
        #self.enablePhysNode()
        
    def __del__(self):
        
        #print viz.getFrameNumber()
        
        # Stop updating node3D
        if( self.updateAction ):
            self.updateAction.remove()
        
        # Remove physical component
        if( self.physNode ):
            self.physNode.remove()
            self.physNode = False
                
        # Remove visual component
        self.node3D.remove()
     
    def remove(self):
        
        self.__del__()
        
    def makeBasicVizShape(self):
        
        # Returns a pointer to a vizshape object
        # This is added to the room.objects parent
        newnode3D = []
        
        if(self.shape == 'box' ):
            #print 'Making box node3D'
            
            if( type(self.size) == float or len(self.size) !=3): 
                print '**********Invalid size for box'
                print 'Check rigidBodySizesString.  Expected 3 val for box: height,width,length.'
                print 'Got: ' + str(self.size)
                import winsound
                winsound.Beep(1000,250)
            lwh = [self.size[1],self.size[2],self.size[0]]
            newnode3D = vizshape.addBox(lwh ,alpha = self.alpha,color=viz.RED)
            
        elif(self.shape == 'sphere'):
            
            if( type(self.size) == list and len(self.size) == 1 ):
                self.size = float(self.size[0])
                
            if( type(self.size) != float):  # accept a float
                
                print '**********Invalid size for sphere'
                print 'Check rigidBodySizesString.  Expected 1 val for sphere: radius'
                print 'Got: ' + str(self.size)
                import winsound
                winsound.Beep(1000,250)
            
            #print 'Making sphere node3D'
            newnode3D = vizshape.addSphere(radius = float(self.size), alpha = self.alpha,color=viz.BLUE,slices=10, stacks=10)
        
        elif('cylinder' in self.shape):
            
            if( type(self.size) == float or len(self.size) !=2): 
                
                print '**********Invalid size for cylinder'
                print 'Check rigidBodySizesString.  Expected 2 val for cylinder: height,radius'
                print 'Got: ' + str(self.size)
                import winsound
                winsound.Beep(1000,250)
                
            #print 'Making cylinder node3D'
            
            if( self.shape[-2:] == '_X' or self.shape[-2:] == '_Y' or self.shape[-2:] == '_Z' ):
                axisString = 'vizshape.AXIS' + self.shape[-2:]
                print axisString + axisString + axisString + axisString
                evalString = 'vizshape.addCylinder(height=self.size[0],radius=self.size[1], alpha = self.alpha,color=viz.BLUE,axis=' + axisString + ')'
                
                newnode3D = eval(evalString)
            else:
                newnode3D = vizshape.addCylinder(height=self.size[0],radius=self.size[1], alpha = self.alpha,color=viz.BLUE, axis = vizshape.AXIS_Y )
            
        if( newnode3D ) :
                    
            self.node3D = newnode3D
            
        else:
            
            print 'vizEnv.room.makeBasicVizShape(): Unable to create node3D'
            import winsound
            winsound.Beep(1000,250)
        
        #if(self.parentRoom):
        newnode3D.setParent(self.parentRoom.objects)


        
    def setVelocity(self,velocity):
        
        #self.node3D.setVelocity(velocity)
        if( self.physNode.body ):
            self.physNode.body.setLinearVel(velocity)
    
    def getVelocity(self):
        
        #self.node3D.setVelocity(velocity)
        if( self.physNode.body ):
            return self.physNode.body.getLinearVel()
    
    def getAngularVelocity(self):
        
        #self.node3D.setVelocity(velocity)
        if( self.physNode.body ):
            return self.physNode.body.getAngularVel()
            
    def setPosition(self,position):

        self.physNode.setPosition(position)
        self.node3D.setPosition(position)
        
    def setColor(self,color3f):
        
        self.node3D.color(color3f)
        #self.node3D.ambient(color3f)
        #self.node3D.specular(color3f)
    
    def projectShadows(self,targetnode3D):
    
        #add avatar as shadow caster
        self.parentRoom.shadowSource.addCaster(self.node3D)

        #Add ground as shadow receiver
        self.parentRoom.shadowSource.addReceiver(targetnode3D)
        
#    def setMocapMarker(self,mocap,markerIndex):        
#       
#       self.markerObject = mocap.returnPointerToMarker(markerIndex)
#    
#    def setMocapRigidBody(self,mocap,rigidBodyFileString):        
#       
#       self.rigidBodyFile = mocap.returnPointerToRigid(rigidBodyFileString)
    
    def enablePhysNode(self):

        ## Create physical object
        self.physNode = self.parentRoom.physEnv.makePhysNode(self.shape,self.position,self.size)
        self.setVelocity([0,0,0])
        self.physNode.disableMovement()
    
    def linkToPhysNode(self):

        #print'linkToPhysNode ==>' self.physNode.node3D.getPosition()
        self.updateAction = viz.link( self.physNode.node3D, self.node3D )
        
        #if( self.physNode ):
            #return vizact.onupdate(viz.PRIORITY_LINKS,self.physNode.linkPose,self.node3D )
    
    def setBounciness(self,bounciness):        

        self.physNode.setBounciness(bounciness)
    
    def linkPhysToVis(self):
        self.physNode.isLinked = 1;
        self.updateAction = viz.link( self.node3D, self.physNode.node3D)
        self.updateAction.setDstFlag(viz.ABS_GLOBAL)
        self.updateAction.setSrcFlag(viz.ABS_GLOBAL)

class mocapMarkerSphere(visObj):
    def __init__(self,mocap,room,markerNum):
        #super(visObj,self).__init__(room,'sphere',.04,[0,0,0],[.5,0,0],1)

        position = [0,0,0]
        shape = 'sphere'
        color=[.5,0,0]
        size = [.015]
        
        visObj.__init__(self,room,shape,size,position,color)
        
        #self.physNode.enableMovement()
        self.markerNumber = markerNum
        self.mocapDevice = mocap
        self.toggleUpdateWithMarker()

if __name__ == "__main__":

    import vizact
    useConfig = True
    
    if useConfig:
        
        #########################################################
        #########################################################
        # Configure the simulation using VRLABConfig
        # This also enables mocap tracking of markers and 
        # rigid bodies specified in config expConfigName
        
        expConfigName = 'badmintonTest.cfg'
        import vrlabConfig
        config = vrlabConfig.VRLabConfig(expConfigName)
        room = room(config )
        
        #########################################################
        # Link mainview to hmd rigid body
        # note that 'hmd' is used to search rigid body files for the partial string
        # in my current setup, it will find hmd-oculus.rb and link to that
        
        if( config.use_phasespace and config.use_HMD and config.mocap.returnPointerToRigid('hmd') ):
                
                config.mocap.enableHMDTracking()
                
                vizact.onkeydown('-',config.mocap.disableHMDTracking)
                vizact.onkeydown('=',config.mocap.enableHMDTracking)
                
                vizact.onkeydown( 'h', config.mocap.resetRigid, 'hmd' );
                vizact.onkeydown( 'H', config.mocap.saveRigid, 'hmd' );
        else:
            
            viz.MainView.setPosition([room.wallPos_NegX +.1, 2, room.wallPos_NegZ +.1])
            viz.MainView.lookAt([0,2,0])
        
    else:
        
        #########################################################
        ##  Just create the basic visual environment
        
        viz.window.setFullscreenMonitor([1]) 
        viz.setMultiSample(4)
        viz.MainWindow.clip(0.01 ,200)
        
        viz.go(viz.FULLSCREEN)
       
        viz.MainView.setPosition([-5,2,10.75])
        viz.MainView.lookAt([0,2,0])        
        viz.vsync(1)
        room = room()
        
