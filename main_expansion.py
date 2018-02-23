from __future__ import print_function

"""
Runs an experiment.
(Please add a better module docstring.)
"""

import datetime
import logging
import math
import os.path
import platform
import random
from ctypes import *  # eyetrackka

import numpy as np
import pandas as pd

import ode
import physEnv
import smi
import visEnv
import viz

# relative path imports
viz.res.addPath('resources')
sys.path.append('utils')

import vizact
import vizconnect
import vizshape
import viztask
from configobj import ConfigObj, flatten_errors
from drawNumberFromDist import *
from gazeTools import calibrationTools, gazeSphere, gazeVector
from validate import Validator


#expConfigFileName = 'gd_pilot.cfg'

expConfigFileName = 'gdExpansionPilot.cfg'

print('**************** USING' + expConfigFileName + '****************')

# Room coordinates?
ft = .3048
inch = 0.0254
m = 1
eps = .01
nan = float('NaN')  # Pandas?

class soundBank():
    """
    Create a globally accessible soundbank.
    To access within a member function,	import the global variable with 'global soundbank'
    """
    def __init__(self):
        """Register sounds. It makes sense to do it once per experiment."""
        self.bounce = '/Resources/bounce.wav'
        self.buzzer = '/Resources/BUZZER.wav'
        self.bubblePop = '/Resources/bubblePop3.wav'
        self.highDrip = '/Resources/highdrip.wav'
        self.cowbell = '/Resources/cowbell.wav'
        self.gong = '/Resources/gong.wav'

        viz.playSound(self.bounce, viz.SOUND_PRELOAD)
        viz.playSound(self.buzzer, viz.SOUND_PRELOAD)
        viz.playSound(self.bubblePop, viz.SOUND_PRELOAD)
        viz.playSound(self.highDrip, viz.SOUND_PRELOAD)
        viz.playSound(self.cowbell, viz.SOUND_PRELOAD)
        viz.playSound(self.gong, viz.SOUND_PRELOAD)

soundBank = soundBank()

class Configuration():
    """
    Add docstring
    """

    def __init__(self, expCfgName=""):
        """
        Opens and interprets both the system config (as defined by the
        <platform>.cfg file) and the experiment config (as defined by
        the file in expCfgName). Both configurations MUST conform the
        specs given in sysCfgSpec.ini and expCfgSpec.ini respectively.
        It also initializes the system as specified in the sysCfg.
        """
        self.eyeTracker = []
        self.writables = list()

        if expCfgName:
            self.__createExpCfg(expCfgName)
        else:
            self.expCfg = None

        self.__createSysCfg()

        for pathName in self.sysCfg['set_path']:
            viz.res.addPath(pathName)

        self.vizconnect = vizconnect.go('vizConnect/' + self.sysCfg['vizconfigFileName'])
        self.__postVizConnectSetup()

    def __postVizConnectSetup(self):
        '''
        This is where one can run any system-specific code that vizconnect can't handle
        '''
        
        dispDict = vizconnect.getRawDisplayDict()
        self.clientWindow = dispDict['exp_display']
        

        if self.sysCfg['use_wiimote']:
            # Create wiimote holder
            self.wiimote = 0
            self.__connectWiiMote()

        if self.sysCfg['use_hmd'] and self.sysCfg['hmd']['type'] == 'DK2':
            self.hmdWindow = dispDict['rift_display']
            self.__setupOculusMon()

        if self.sysCfg['use_hmd'] and self.sysCfg['hmd']['type'] == 'VIVE':
            import steamvr
            self.hmdWindow = dispDict['rift_display']
            self.__setupViveMon()

        ###  This is one way to implement controller support for the vive
        #            def ControllerTask(controller):
        #
        #                while True:
        #
        #                    # Wait for trigger to press
        #                    yield viztask.waitSensorDown(controller, steamvr.BUTTON_TRIGGER)
        #
        #                    #get an end point
        #                    line = controller.model.getLineForward(viz.ABS_GLOBAL, length=300.0)
        #
        #                    intersection_info = viz.intersect(line.begin, line.end)
        #
        #                    #if intersection_info.valid:
        #                    #    controller.line.setVertex(1,intersection_info.intersectPoint)
        #
        #                    # Start highlighting task
        #                    #highlightTask = viztask.schedule(showPointer(controller))
        #                    controller.line.visible(True)
        #
        #                    #hmm, couldset line end vertexhere, but might not work as anticipated
        #
        #                    # Wait for trigger to release
        #                    yield viztask.waitSensorUp(controller, steamvr.BUTTON_TRIGGER)
        #
        #                    # Stop highlighting task
        #                    controller.line.visible(False)
        #
        #            # Add controllers
        #            #controller_tracker = vizconnect.getTracker('r_hand_tracker')
        #            controllerList = steamvr.getControllerList()
        #            if len(controllerList) > 0:
        #                controller = steamvr.getControllerList()[0]
        #
        #                # Create model for controller
        #                controller.model = controller.addModel()
        #                controller.model.disable(viz.INTERSECTION)
        #                #controller.visible(viz.ON)
        #                viz.link(controller, controller.model)
        #
        #                # Create pointer line for controller
        #                viz.startLayer(viz.LINES)
        #                viz.vertexColor(viz.WHITE)
        #                viz.vertex([0,0,0])
        #                viz.vertex([0,0,300])
        #                controller.line = viz.endLayer(parent=controller.model)
        #                controller.line.dynamic()
        #                controller.line.disable([viz.INTERSECTION, viz.SHADOW_CASTING])
        #                controller.line.visible(False)
        #
        #                self.controller = controller
        #
        #            # Setup task for drawing line
        #            viztask.schedule(ControllerTask(self.controller))

        if self.sysCfg['use_eyetracking'] and self.sysCfg['eyetracker']['type'] == 'SMIDK2':
        
            self.use_eyeTracking = True
            self.__connectSMIDK2()        
            
        if self.sysCfg['use_eyetracking'] and self.sysCfg['eyetracker']['type'] == 'SMIVIVE':
        
            self.use_eyeTracking = True
            self.__connectSMIVive()   

        elif self.sysCfg['use_eyetracking'] and self.sysCfg['eyetracker']['type'] == 'PUPIL':
            self.use_eyeTracking = True
            self.__connectPUPILVR()
        else:
            print('Invalid eyetracker type specified in sysconfig')
            self.use_eyeTracking = False

        self.eyeTrackingCal = False

        self.writer = None  # Will get initialized later when the system starts
        self.writables = list()

        if self.sysCfg['use_phasespace']:

            from mocapInterface import phasespaceInterface
            self.mocap = phasespaceInterface(self.sysCfg)

            self.use_phasespace = True
        else:
            self.use_phasespace = False

        viz.setOption("viz.glfinish", 1)
        viz.setOption("viz.dwm_composition", 0)

    def __createExpCfg(self, expCfgName):
        """
        Parses and validates a config obj
        Variables read in are stored in configObj
        """

        print("Loading experiment config file: " + expCfgName)

        # This is where the parser is called.
        expCfg = ConfigObj(expCfgName, configspec='expCfgSpec.ini', raise_errors=True, file_error=True)

        validator = Validator()
        expCfgOK = expCfg.validate(validator)
        if expCfgOK == True:
            print("Experiment config file parsed correctly")
        else:
            print('Experiment config file validation failed!')
            res = expCfg.validate(validator, preserve_errors=True)
            for entry in flatten_errors(expCfg, res):
                # each entry is a tuple
                section_list, key, error = entry
                if key:
                    section_list.append(key)
                else:
                    section_list.append('[missing section]')
                section_string = ', '.join(section_list)
                if error == False:
                    error = 'Missing value or section.'
                print(section_string, ' = ', error)
            sys.exit(1)

        if expCfg.has_key('_LOAD_'):
            for ld in expCfg['_LOAD_']['loadList']:
                print('Loading: ' + ld + ' as ' + expCfg['_LOAD_'][ld]['cfgFile'])
                curCfg = ConfigObj(expCfg['_LOAD_'][ld]['cfgFile'], configspec=expCfg['_LOAD_'][ld]['cfgSpec'], raise_errors=True, file_error=True)
                validator = Validator()
                expCfgOK = curCfg.validate(validator)
                if expCfgOK == True:
                    print("Experiment config file parsed correctly")
                else:
                    print('Experiment config file validation failed!')
                    res = curCfg.validate(validator, preserve_errors=True)
                    for entry in flatten_errors(curCfg, res):
                        # each entry is a tuple
                        section_list, key, error = entry
                        if key is not None:
                            section_list.append(key)
                        else:
                            section_list.append('[missing section]')
                        section_string = ', '.join(section_list)
                        if error == False:
                            error = 'Missing value or section.'
                        print(section_string, ' = ', error)
                    sys.exit(1)
                expCfg.merge(curCfg)

        self.expCfg = expCfg

    def __setWinPriority(self, pid=None, priority=5):
        """ Set The Priority of a Windows Process.  Priority is a value between 0-5 where
            2 is normal priority.  Default sets the priority of the current
            python process but can take any valid process ID. """
        import win32api, win32process, win32con

        priorityclasses = [win32process.IDLE_PRIORITY_CLASS,
                           win32process.BELOW_NORMAL_PRIORITY_CLASS,
                           win32process.NORMAL_PRIORITY_CLASS,
                           win32process.ABOVE_NORMAL_PRIORITY_CLASS,
                           win32process.HIGH_PRIORITY_CLASS,
                           win32process.REALTIME_PRIORITY_CLASS]
        if not pid:
            pid = win32api.GetCurrentProcessId()

        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        win32process.SetPriorityClass(handle, priorityclasses[priority])

    def __createSysCfg(self):
        """
        Set up the system config section (sysCfg)
        """

        # Get machine name
        sysCfgName = platform.node()+".cfg"

        if not os.path.isfile(sysCfgName):
            sysCfgName = "defaultSys.cfg"

        print("Loading system config file: " + sysCfgName)

        # Parse system config file
        sysCfg = ConfigObj(sysCfgName, configspec='sysCfgSpec.ini', raise_errors=True)

        validator = Validator()
        sysCfgOK = sysCfg.validate(validator)

        if sysCfgOK:
            print("System config file parsed correctly")
        else:
            print('System config file validation failed!')
            res = sysCfg.validate(validator, preserve_errors=True)
            for entry in flatten_errors(sysCfg, res):
                # each entry is a tuple
                section_list, key, error = entry
                if key is not None:
                    section_list.append(key)
                else:
                    section_list.append('[missing section]')
                section_string = ', '.join(section_list)
                if error == False:
                    error = 'Missing value or section.'
                print(section_string, ' = ', error)
            sys.exit(1)
        self.sysCfg = sysCfg

    def __setupViveMon(self):
        """
        Setup for the htc vive
        Relies upon a cluster enabling a single client on the local machine
        THe client enables a mirrored desktop view of what's displays inside the vive
        Note that this does some juggling of monitor numbers for you.
        """
        
        displayList = self.sysCfg['displays']

        if len(displayList) < 2:
            print('Display list is <1.  Need two displays.')
        else:
            print('Using display number ' + str(displayList[0]) + ' for vive display.')
            print('Using display number ' + str(displayList[1]) + ' for mirrored display.')

        ### Set the vive and exp displays

        viveMon = []
        expMon = displayList[1]

        with viz.cluster.MaskedContext(viz.MASTER):

            # Set monitor to the vive
            monList = viz.window.getMonitorList()

            for mon in monList:
                #TODO: test if this works with Vive
                if mon.name == 'HTC Vive':
                    viveMon = mon.id

            viz.window.setFullscreenMonitor(viveMon)
            viz.window.setFullscreen(1)

        with viz.cluster.MaskedContext(viz.CLIENT1):

            count = 1
            while viveMon == expMon:
                expMon = count

            viz.window.setFullscreenMonitor(expMon)
            viz.window.setFullscreen(1)

    def __setupOculusMon(self):
        """
        Setup for the oculus rift dk2
        Relies upon a cluster enabling a single client on the local machine
        THe client enables a mirrored desktop view of what's displays inside the oculus DK2
        Note that this does some juggling of monitor numbers for you.
        """

        #viz.window.setFullscreenMonitor(self.sysCfg['displays'])
        #hmd = oculus.Rift(renderMode=oculus.RENDER_CLIENT)

        displayList = self.sysCfg['displays']

        if len(displayList) < 2:
            print('Display list is <1.  Need two displays.')
        else:
            print('Using display number ' + str(displayList[0]) + ' for oculus display.')
            print('Using display number ' + str(displayList[1]) + ' for mirrored display.')

        ### Set the rift and exp displays

        riftMon = []
        expMon = displayList[1]

        with viz.cluster.MaskedContext(viz.MASTER):

            # Set monitor to the oculus rift
            monList = viz.window.getMonitorList()

            for mon in monList:
                if mon.name == 'Rift DK2':
                    riftMon = mon.id

            viz.window.setFullscreenMonitor(riftMon)
            viz.window.setFullscreen(1)

        with viz.cluster.MaskedContext(viz.CLIENT1):

            count = 1
            while riftMon == expMon:
                expMon = count

            viz.window.setFullscreenMonitor(expMon)
            viz.window.setFullscreen(1)

    def __connectWiiMote(self):

        wii = viz.add('wiimote.dle')#Add wiimote extension

        # Replace old wiimote
        if self.wiimote:
            print('Wiimote removed.')
            self.wiimote.remove()

        self.wiimote = wii.addWiimote()# Connect to first available wiimote

        vizact.onexit(self.wiimote.remove) # Make sure it is disconnected on quit

        self.wiimote.led = wii.LED_1 | wii.LED_4 #Turn on leds to show connection

    def __connectSMIVive(self):

            
        smi = viz.add('smi_vive.dle')
        self.eyeTracker = smi.addEyeTracker()
        if not self.eyeTracker:
            sys.exit('Eye tracker not detected')
        else:
            print('****Using SMI Viveintegration****')

    def __connectSMIDK2(self):

        import oculus
        import smi

        if self.sysCfg['sim_trackerData']:
            self.eyeTracker = smi.iViewHMD(simulate=True)
        else:
            self.eyeTracker = smi.iViewHMD()
            

    def __connectPUPILVR(self):

        import pupil

        if self.sysCfg['sim_trackerData']:
            self.eyeTracker = pupil.HMD(simulate=True)
        else:
            self.eyeTracker = pupil.HMD()

class Experiment(viz.EventClass):
    """
    Experiment manages the basic operation of the experiment.
    """

    def __init__(self, expConfigFileName):
        """
        Event classes can register their own callback functions. This makes it possible to register
        callback functions (e.g. activated by a timer event) within the class (that accept the
        implied self argument) eg self.callbackFunction(arg1) would receive args (self, arg1) If
        this were not an eventclass, the self arg would not be passed = badness.
        """
        viz.EventClass.__init__(self) # isn't this called already when Experiment is instantiated?

        ##############################################################
        ##############################################################
        ## Use config to setup hardware, motion tracking, frustum, eyeTrackingCal.
        ##  This draws upon the system config to setup the hardware / HMD

        self.config = Configuration(expConfigFileName)

        ################################################################
        ################################################################
        ## Set states

        self.inCalibrateMode = False
        self.inHMDGeomCheckMode = False
        self.setEnabled(False)
        self.test_char = None

        self.calibrationFrameCounter = 0
        self.totalCalibrationFrames = self.config.sysCfg['eyetracker']['recordCalibForNFrames']
        self.calibTools = False

        #self.standingBoxSize_WHL = map(float, config.expCfg['room']['standingBoxSize_WHL'])
        ################################################################
        ################################################################
        # Create visual and physical objects (the room)

        self.room = visEnv.room(self.config)

        self.viewAct = []
        self.hmdLinkedToView = False
        self.headTracker = []

        ################################################################
        ################################################################
        # Build block and trial list

        self.blockNumber = 0
        self.trialNumber = 0
        self.inProgress = True

        self.enableWritingToLog = False
        self.calibrationDoneSMI = False

        self.gazeVector = []
        self.eyeBallVector = []

        self.blocks_bl = []

        for bIdx in range(len(self.config.expCfg['experiment']['blockList'])):
            self.blocks_bl.append(block(self.config, bIdx, self.room))

        self.currentTrial = self.blocks_bl[self.blockNumber].trials_tr[self.trialNumber]


        #		################################################################
        #		################################################################
        #		##  Misc. Design specific items here.

        # Setup launch trigger
        self.launchKeyIsCurrentlyDown = False

        self.minLaunchTriggerDuration = self.config.expCfg['experiment']['minLaunchTriggerDuration']

        if self.config.sysCfg['use_phasespace']:
            self.linkObjectsUsingMocap()
        
        elif self.config.sysCfg['use_hmd'] and self.config.sysCfg['hmd']['type'] == 'VIVE':
            self.setupPaddleVive()

        self.config.expCfg['maxReach'] = False
        self.isLeftHanded = self.config.expCfg['experiment']['isLeftHanded']

        if self.config.use_eyeTracking:
            pass
            #self.showEyeTrack()
            #self.config.eyeTracker.showPositionalGuidance()
            
        if self.config.sysCfg['use_wiimote']:
            self.registerWiimoteActions()


        ##############################################################
        ##############################################################
        ## Callbacks and timers

        vizact.onupdate(viz.PRIORITY_PHYSICS, self._checkForCollisions)
        self.callback(viz.KEYDOWN_EVENT, self.onKeyDown)
        self.callback(viz.KEYUP_EVENT, self.onKeyUp)
        self.callback(viz.TIMER_EVENT, self._timerCallback)

        self.perFrameTimerID = viz.getEventID('perFrameTimerID') # Generates a unique ID.
        self.starttimer(self.perFrameTimerID, viz.FASTEST_EXPIRATION, viz.FOREVER)

        self.changeBallRadiusID = viz.getEventID('changeBallRadiusID') # Generates a unique ID.
        self.currentTrial.changeBallRadiusID = self.changeBallRadiusID

        # maxFlightDurTimerID times out balls a fixed dur after launch
        self.maxFlightDurTimerID = viz.getEventID('maxFlightDurTimerID')

        if( self.currentTrial.useBlankDur ):
            self.ballPreBlankDurTimerID = viz.getEventID('ballPreBlankDurTimerID') # On until
            self.ballBlankDurTimerID = viz.getEventID('ballBlankDurTimerID')

        ############################################################
        #############################################################
        # Setup per-frame data output
        self.setupFileIO()

        with viz.cluster.MaskedContext(viz.MASTER):
            vizact.onupdate(viz.PRIORITY_LAST_UPDATE, self.addDataToLog)

        self.eventFlag = eventFlag()

    def _timerCallback(self, timerID):
        """
        Add Docstring.
#        """
        #        ct = self.currentTrial
        #
        #        if timerID == self.changeBallRadiusID and ct.ballHasHitPaddle == False:
        #
        #            currentDistance = np.sqrt(np.sum(np.power(np.subtract(ct.ballObj.node3D.getPosition(),ct.ballFinalPos_XYZ),2)))
        #
        #            totalChangeInBallSize = (ct.initialBallRadiusM * ct.expansionGain) - ct.initialBallRadiusM
        #
        #            proportionOfFlightTravelled = (ct.ballObj.initialDistance - currentDistance) / ct.ballObj.initialDistance
        #            newRadius = ct.initialBallRadiusM + (totalChangeInBallSize * proportionOfFlightTravelled )
        #            print( 'CurDist: %s New Radius: %s' % (str(currentDistance), str(newRadius) ))
        #            ct.setBallRadius(newRadius )
        #
        if timerID == self.maxFlightDurTimerID:

            print('Removing ball!')
            self.currentTrial.removeBall()
            self.room.standingBox.visible(viz.TOGGLE)
            self.endTrial()

        elif self.currentTrial.useBlankDur and timerID == self.ballPreBlankDurTimerID:

            if self.currentTrial.blankDur != 0.0:
                self.currentTrial.ballObj.node3D.visible(False)
                self.starttimer(self.ballBlankDurTimerID, self.currentTrial.blankDur)
                self.eventFlag.setStatus('ballRenderOff')

        elif self.currentTrial.useBlankDur and timerID == self.ballBlankDurTimerID:

            self.currentTrial.ballObj.node3D.visible(True)
            self.eventFlag.setStatus('ballRenderOn')

    def _checkForCollisions(self):


        """
        Add Docstring.
        """
        thePhysEnv = self.room.physEnv
        if thePhysEnv.collisionDetected == False:
            # No collisions this time!
            return

        theFloor = self.room.floor
        theBackWall = self.room.wall_NegZ
        theBall = self.currentTrial.ballObj

        if self.room.paddle:
            thePaddle = self.room.paddle
        if self.room.passingPlane:
            thePassingPlane = self.room.passingPlane

        for idx in range(len(thePhysEnv.collisionList_idx_physNodes)):
            physNode1 = thePhysEnv.collisionList_idx_physNodes[idx][0]
            physNode2 = thePhysEnv.collisionList_idx_physNodes[idx][1]

            # BALL / FLOOR
            if theBall:

                if(self.currentTrial.ballHasBouncedOnFloor == False and
                       (physNode1 == theFloor.physNode and physNode2 == theBall.physNode or
                                    physNode1 == theBall.physNode and physNode2 == theFloor.physNode)):
                    self.eventFlag.setStatus('ballOnFloor')

                    self.currentTrial.ballHasBouncedOnFloor = True

                    # This is an example of how to get contact information
                    #bouncePos_XYZ, normal, depth, geom1, geom2 = thePhysEnv.contactObjects_idx[0].getContactGeomParams()
                    #print('Bounce Point', bouncePos_XYZ)

                    #self.currentTrial.ballOnPaddlePos_XYZ = bouncePos_XYZ

                    #print 'Ball has hit the ground.'
                    viz.playSound(soundBank.bounce)

                #                    # Compare pre-bounce flight dur with predicted pre-bounce flight dur
                #                    actualPreBounceFlightDur =  float(viz.getFrameTime()) - self.currentTrial.launchTime
                #                    durationError = self.currentTrial.predictedPreBounceFlightDur - actualPreBounceFlightDur
                #                    self.currentTrial.flightDurationError = durationError
                #
                #                    print ('Predicted: ' + str(self.currentTrial.predictedPreBounceFlightDur))
                #                    print ('Actual   : ' + str(actualPreBounceFlightDur))
                #
                #                    print ( 'Flight duration error: ' + str(durationError))

                # BALL / PADDLE
                if (self.currentTrial.ballHasHitPaddle == False and
                        (physNode1 == thePaddle.physNode and physNode2 == theBall.physNode or
                                     physNode1 == theBall.physNode  and physNode2 == thePaddle.physNode)):

                    self.eventFlag.setStatus('ballOnPaddle')
                    self.currentTrial.ballHasHitPaddle = True
                    viz.playSound(soundBank.cowbell)

                    if self.currentTrial.ballResizeAct:
                        self.currentTrial.ballResizeAct.remove()

                    theBall.physNode.updateNodeAct.remove()
                    theBall.updateAction.remove()

                    # self.ballObj.physNode.setStickUponContact( room.paddle.physNode.geom )
                    if theBall.physNode.queryStickyState(thePaddle.physNode):

                        # Could also be acheived by turning of physics via the physnode


                        theBall.node3D.setParent(thePaddle.node3D)
                        #collPoint_XYZ = theBall.node3D.getPosition(viz.ABS_PARENT)
                        collPoint_XYZ =  theBall.physNode.collisionPosLocal_XYZ

                        print('Collision Location: ', collPoint_XYZ)
                        theBall.node3D.setPosition(collPoint_XYZ, viz.ABS_PARENT)

                        self.currentTrial.ballOnPaddlePosLoc_XYZ = collPoint_XYZ

                        # If you don't set position in this way (on the next frame using vizact.onupdate),
                        # then it doesn't seem to update correctly.
                        # My guess is that this is because the ball's position is updated later on this frame using

                        vizact.onupdate(viz.PRIORITY_LINKS, theBall.node3D.setPosition, collPoint_XYZ[0], collPoint_XYZ[1], collPoint_XYZ[2], viz.ABS_PARENT)

                    #                if (physNode1 == theBackWall.physNode and physNode2 == theBall.physNode or
                    #                        physNode1 == theBall.physNode and physNode2 == theBackWall.physNode):
                    #                    #self.eventFlag.setStatus(5)
                    #                    self.eventFlag.setStatus('ballOnBackWall')
                    #                    #print 'Ball has hit the back wall.'
                    #
                    #                    viz.playSound(soundBank.bounce)

    # TODO: Move this to logging/recording module
    def setupFileIO(self):
        """
        set up a logger and add handlers
        """
        self.logger = logging.getLogger()
        now = datetime.datetime.now()

        dateTimeStr = str(now.year) + '-' + str(now.month) + '-' + str(now.day) + '-' + str(now.hour) + '-' + str(now.minute)

        dataOutPutDir = self.config.sysCfg['writer']['outFileDir'] + '//' +str(dateTimeStr) + '//'

        if not os.path.exists(dataOutPutDir):
            os.makedirs(dataOutPutDir)

        self.fhandler = logging.FileHandler(filename=dataOutPutDir + 'exp_data-' + dateTimeStr + '.dict', mode='w')
        formatter = logging.Formatter('%(message)s')
        self.fhandler.setFormatter(formatter)
        self.logger.addHandler(self.fhandler)
        self.logger.setLevel(logging.DEBUG)

        from shutil import copyfile

        # Copy config files
        copyfile('.\\' + expConfigFileName, dataOutPutDir+expConfigFileName) # exp config
        copyfile('.\\expCfgSpec.ini', dataOutPutDir + 'expCfgSpec.ini') # exp config spec1

        copyfile('.\\' + os.environ['COMPUTERNAME'] + '.cfg', dataOutPutDir + os.environ['COMPUTERNAME'] + '.cfg') # system config
        copyfile('.\\sysCfgSpec.ini', dataOutPutDir + 'sysCfgSpec.ini') # system config spec


    def start(self):
        """
        This is called when the experiment should begin.
        """
        self.setEnabled(True)

    def startPerForMCalibration(self):
        """
        Enters the calibration for eye tracking.
        Note, that for this to work, toggling
        # self.config.camera must turn off your world model
        # This is setup in testRoom.init().

        # Example of what's needed in testRoom.init
        self.room = viz.addGroup()
        self.model = viz.add('pit.osgb',parent = self.room)
        """

        self.inCalibrateMode = True

        self.calibTools = calibrationTools(self.gazeNodes.cycGazePoint, clientWindowID, self.gazeNodes.cycEyeBase, self.config, self.room)
        self.calibTools.create3DCalibrationPositions(self.calibTools.calibrationPositionRange_X, self.calibTools.calibrationPositionRange_Y, self.calibTools.calibrationPositionRange_Z, self.calibTools.numberOfCalibrationPoints)


        if not self.config.sysCfg['use_eyetracking']:
            print('Eyetracker not setup')
            return

        #####


        #self.config.eyeTrackingCal.toggleCalib()

        # gray 
        #with viz.cluster.MaskedContext(viz.MASTER):
        disp = vizconnect.getRawDisplayDict()

        for key in disp:
            disp[key].clearcolor(viz.GRAY)
        #
        #        viz.MainView.setPosition(0, 0, 0)
        #        viz.MainView.setAxisAngle(0, 1, 0, 0)
        #        viz.MainView.velocity([0, 0, 0])

        if self.room:
            self.room.walls.visible(viz.TOGGLE)
            self.room.objects.visible(viz.TOGGLE)
            self.room.standingBox.visible(viz.TOGGLE)
            self.room.paddle.node3D.visible(viz.TOGGLE)

        #        self.config.eyeTrackingCal.updateOffset('s')
        #        self.config.eyeTrackingCal.updateOffset('w')
        self.calibTools.staticCalibrationMethod()

    def endPerForMCalibration(self):

        self.inCalibrateMode = False
        self.calibrationCounter = 0
        self.calibTools.endCalibration()

        if self.room:
            self.room.walls.visible(viz.TOGGLE)
            self.room.objects.visible(viz.TOGGLE)
            self.room.standingBox.visible(viz.TOGGLE)
            self.room.paddle.node3D.visible(viz.TOGGLE)

    def createCamera(self):
        """
        Currently, this function does nothing.
        Head camera is generally initialized as part of the system calls. Additional changes should be added here.
        """
        pass

    def updateGazePoints(self):
        displayOffset = 0.15
        self.myDisplay.setPosition(viz.MainView.getPosition() - [0.0, 0.0, displayOffset])


    def callSMICalibration(self):

        numCalibPoint = self.config.sysCfg['eyetracker']['smiNumCalibPoints']

        self.calibrationDoneSMI = True
        eyeTracker = experimentObject.config.eyeTracker
        smiCalibType = np.where(numCalibPoint == np.array([0,1,3,5,9]))[0][0]
        eyeTracker.calibrate(type=smiCalibType) # SMI calibTypes listed at top of smi.py
        print('calibrationDoneSMI ==> ', self.calibrationDoneSMI)

    #    def callPerForMCalibration(self):
    #
    #        print('Static Calibration Method is Called')
    #        self.calibTools.staticCalibrationMethod()

    def updateCalibrationPoint(self):
        self.calibTools.updateCalibrationPoint()

    def recordCalibrationData(self):
        print('Data Recording Started for Calibration')
        self.calibTools.calibrationSphere.color(viz.YELLOW)
        self.enableWritingToLog = True
        self.calibrationFrameCounter = 0

    def setMaxReachAndViewHeight(self):


        self.config.viewHeight = viz.MainView.getPosition()[1]

        paddle = self.room.paddle
        inverseViewMat = np.reshape(viz.MainView.getMatrix().inverse(),[4,4]).T
        paddlePosInHeadSpace_XYZ = np.dot(np.reshape(np.array(inverseViewMat),[4,4]).T ,np.append(paddle.node3D.getPosition(),1))

        self.config.expCfg['maxReach'] = np.abs(paddlePosInHeadSpace_XYZ[0])

        print('*** Max reach set to %1.1f m ***'  %self.config.expCfg['maxReach'])
        if( paddlePosInHeadSpace_XYZ[0] < 0 ):
            self.isLeftHanded = True
            self.config.expCfg['experiment']['isLeftHanded'] = True



    def onKeyDown(self, key):
        """
        Interactive commands can be given via the keyboard.
        Some are provided here. You'll likely want to add more.
        """
        if self.config.use_phasespace:
            
            mocapSys = self.config.mocap
            paddleRigid = mocapSys.returnPointerToRigid('paddle')

            if self.config.sysCfg['hmd']['type'] == 'VIVE':
                hmdTracker = vizconnect.getTracker('head_tracker')
            else:
                hmdRigid = mocapSys.returnPointerToRigid('hmd')
            
        else:
            mocapSys = []
            hmdRigid = []
            paddleRigid = []

            ##########################################################
            ##########################################################
            ## Keys used in the default mode

        #        if key == 'z':
        #
        #            print('Dynamic Calibration Method is Called')
        #            self.enableWritingToLog = True
        #            self.calibTools.dynamicCalibrationMethod()

        if self.inCalibrateMode:

            if key == 'q':

                if( self.calibTools.calibrationCounter < self.calibTools.numberOfCalibrationPoints-1 ):
                    self.calibTools.updateCalibrationPoint()
                else:
                    self.endPerForMCalibration()

            if key == 'k':
                self.recordCalibrationData()

            if key == 'e':
                self.endPerForMCalibration()

        elif not self.inCalibrateMode:

            if key == 'c' and self.config.eyeTracker:
                self.callSMICalibration()

            elif key == 'e':

                self.startPerForMCalibration()

            elif key == 'Z':
                self.setMaxReachAndViewHeight()

            elif key == 'M':
                # Toggle the link between the HMD and Mainview
                if self.hmdLinkedToView:
                    if self.viewAct.getEnabled():
                        self.viewAct.disable()
                    else:
                        self.viewAct.enable()
            elif key == 'p':
                mocapSys.resetRigid('paddle')
            elif key == 'P':
                mocapSys.saveRigid('paddle')
            elif key == 'h':
                #print 'reset HMD Rigid Body'
                mocapSys.resetRigid('hmd')
            elif key == 'H':
                print('save HMD Rigid Body')
                mocapSys.saveRigid('hmd')
            elif key == 'W':
                self.connectWiiMote()
            elif key == ' ':
                self.launchKeyDown()

            elif key == 'r':

                vizconnect.getTracker('rift_tracker').resetHeading()

                ##########################################################
                ##########################################################
                ##
    def onKeyUp(self, key):
        """
        Eye-tracker calibration mode.
        """
        if key == ' ':
            self.launchKeyUp()

    def launchKeyDown(self):

        if (self.inProgress == True and
                    self.launchKeyIsCurrentlyDown == False and
                    self.currentTrial.ballInRoom == False): # There is not already a ball

            # Start timing trigger duration
            # At end of trigger, launch the ball.
            self.launchKeyIsCurrentlyDown = True
            self.timeLaunchKeyWasPressed = viz.tick()

            self.currentTrial.placeBall(self.room)

            self.room.standingBox.visible(viz.TOGGLE)

    def launchKeyUp(self):

        if( self.config.use_eyeTracking):

            if self.calibTools and self.calibTools.calibrationInProgress:
                return

        if self.launchKeyIsCurrentlyDown:

            self.launchKeyIsCurrentlyDown = False
            triggerDuration = viz.tick() - self.timeLaunchKeyWasPressed
            ballReadyToLaunch = False

            if ( self.currentTrial.ballInRoom == True and
                         self.currentTrial.ballInInitialState == True and
                         self.currentTrial.ballLaunched == False):

                # Ball is ready to launch
                if self.inProgress == False or triggerDuration <= self.minLaunchTriggerDuration:
                    # Trigger not held long enough for a launch
                    viz.playSound(soundBank.cowbell) # need more cowbell
                    self.room.standingBox.visible(viz.TOGGLE)
                    self.currentTrial.removeBall()
                    print('Launch aborted')

                if triggerDuration >= self.minLaunchTriggerDuration:
                    # Launch the ball


                    self.eventFlag.setStatus('trialStart')
                    self.inProgress = True
                    self.enableWritingToLog = True
                    print('Start Trial {%s}' % str(self.enableWritingToLog))

                    self.currentTrial.launchBall()

                    self.starttimer(self.maxFlightDurTimerID, self.currentTrial.ballFlightMaxDur)

                    self.starttimer(self.changeBallRadiusID,viz.FASTEST_EXPIRATION, self.currentTrial.timeToContact)

                    if self.currentTrial.useBlankDur:
                        self.starttimer(self.ballPreBlankDurTimerID, self.currentTrial.preBlankDur)

            else: # Why?
                return

    # TODO: Move this to logging/recording module
    def addDataToLog(self):

        """
        Writes a string (really a dictionary literal) describing current state of experiment to
        text file.

        Note: many variables defined in this function include in the variable name an underscore.
        The post-underscore suffix is currently used to break up the values of such variables, if
        they are not scalar quantities.

        Legend:
            ** for 1 var
            () for 2 vars
            [] for 3 vars
            <> for 4 vars
            @@ for 16 vars (view and projection matrices)

            ### Eventflag
            1 ball launched
            3 ball has hit floor
            4 ball has hit paddle
            5 ball has hit back wall
            6 ball has timed out
        """

        NaN = float('NaN') # Why? - is this for Pandas?
        # floating point NAN defined here this way due to use of Pandas later columns must contain
        # values of same type - most recorded data in here is floating point, thus, empty cells
        # must also have some representative value that is also a float.
        # (Why not 0.0? - probably cases where attribute is 0.0, not empty)


        # Only write data is the experiment is ongoing
        if self.enableWritingToLog is False or self.inProgress is False:
            return

        #print('Writing on frame: %1.0f',viz.getFrameNumber())

        # during calibration only 100 frame durations are recorded for each fixation.
        # TODO: the conditional governing whether to record should be outside the actual function
        self.calibrationFrameCounter += 1

        if( self.inCalibrateMode ):


            calibrationCounter = self.calibTools.calibrationCounter

            if self.calibTools.calibrationInProgress and self.calibrationFrameCounter > self.totalCalibrationFrames:
                self.enableWritingToLog = False
                print('Calibration Frames Recorded:', self.calibrationFrameCounter)
                self.calibTools.calibrationSphere.color(viz.PURPLE)
                self.calibrationFrameCounter = 0
                return
        else:
            calibrationCounter = NaN

        # Gather misc data
        frameNum = viz.getFrameNumber()
        viewPos_XYZ = viz.MainView.getPosition(viz.MASTER)

        noExpansionForLastXSeconds = self.currentTrial.noExpansionForLastXSeconds
        maxReach = self.config.expCfg['maxReach']

        if self.inCalibrateMode and self.calibTools.calibrationSphere:

            calibrationPoint_XYZ = self.calibTools.calibrationSphere.getPosition()
        else:
            calibrationPoint_XYZ = [NaN, NaN, NaN]

        if self.config.use_eyeTracking:
            # current state of experiment
            currentSample = self.config.eyeTracker.getLastSample()
        else:
            currentSample = False

        # Gather racquet data
        if self.room.paddle:
            paddlePos_XYZ = self.room.paddle.node3D.getPosition()
            paddleQuat_XYZW = self.room.paddle.node3D.getMatrix().getQuat()
            paddleMat_4x4 = self.room.paddle.node3D.getMatrix().data
        else:
            paddlePos_XYZ = [NaN, NaN, NaN]
            paddleQuat_XYZW = [NaN, NaN, NaN, NaN]
            paddleMat_4x4 = [NaN] * 16

        # Gather ball data
        theBall = self.currentTrial.ballObj
        if theBall:
            ballPos_XYZ = theBall.node3D.getPosition(viz.ABS_GLOBAL)
            ballVel_XYZ = theBall.getVelocity()
            ballVisible = self.currentTrial.ballObj.node3D.getVisible()
            ballMat_4x4 = theBall.node3D.getMatrix().data
            ballRadiusM = theBall.radius
        else:
            ballPos_XYZ = [NaN, NaN, NaN]
            ballVel_XYZ = [NaN, NaN, NaN]
            ballVisible = NaN
            ballMat_4x4 = [NaN] * 16
            ballRadiusM = NaN

        # SMI Data
        if currentSample:
            #smiServerTime = self.config.eyeTracker.getServerTime()

            cycEyeOnScreen_XY = [currentSample.por.x, currentSample.por.y]
            cycEyeInHead_XYZ = [currentSample.gazeDirection.x, currentSample.gazeDirection.y, currentSample.gazeDirection.z]
            cycEyeBasePoint_XYZ = [currentSample.gazeBasePoint.x, currentSample.gazeBasePoint.y, currentSample.gazeBasePoint.z]

            rightEyeOnScreen_XY = [currentSample.rightEye.por.x, currentSample.rightEye.por.y]
            rightEyeInHead_XYZ = [currentSample.rightEye.gazeDirection.x, currentSample.rightEye.gazeDirection.y, currentSample.rightEye.gazeDirection.z]
            rightEyeBasePoint_XYZ = [currentSample.rightEye.gazeBasePoint.x, currentSample.rightEye.gazeBasePoint.y, currentSample.rightEye.gazeBasePoint.z] # H or W?
            rightEyeScreenDistance = currentSample.rightEye.eyeScreenDistance
            rightEyeLensDistance = currentSample.rightEye.eyeLensDistance
            rightPupilRadius = currentSample.rightEye.pupilRadius
            rightPupilPos_XYZ = [currentSample.rightEye.pupilPosition.x, currentSample.rightEye.pupilPosition.y, currentSample.rightEye.pupilPosition.z] # Pixel values

            leftEyeOnScreen_XY = [currentSample.leftEye.por.x, currentSample.leftEye.por.y]
            leftEyeInHead_XYZ = [currentSample.leftEye.gazeDirection.x, currentSample.leftEye.gazeDirection.y, currentSample.leftEye.gazeDirection.z]
            leftEyeBasePoint_XYZ = [currentSample.leftEye.gazeBasePoint.x, currentSample.leftEye.gazeBasePoint.y, currentSample.leftEye.gazeBasePoint.z] # H or W?
            leftEyeScreenDistance = currentSample.leftEye.eyeScreenDistance
            leftEyeLensDistance = currentSample.leftEye.eyeLensDistance
            leftPupilRadius = currentSample.leftEye.pupilRadius
            leftPupilPos_XYZ = [currentSample.leftEye.pupilPosition.x, currentSample.leftEye.pupilPosition.y, currentSample.leftEye.pupilPosition.z] # Pixel values

            # TODO: Check SMI documentation to make sure forcing timestamp to int (instead of long)
            #  wont cause issues.
            # cast to int to avoid "L" suffix in dict literal str (Python 3 has no Long type)
            eyeTimeStamp = int(currentSample.timestamp)
            IOD = currentSample.iod
            IPD = currentSample.ipd

        else:
            #smiServerTime = [NaN]
            cycEyeOnScreen_XY = [NaN, NaN]
            cycEyeInHead_XYZ = [NaN, NaN, NaN]
            cycEyeBasePoint_XYZ = [NaN, NaN, NaN]

            rightEyeOnScreen_XY = [NaN, NaN]
            rightEyeInHead_XYZ = [NaN, NaN, NaN]
            rightEyeBasePoint_XYZ = [NaN, NaN, NaN]
            rightEyeScreenDistance = NaN
            rightEyeLensDistance = NaN
            rightPupilRadius = NaN
            rightPupilPos_XYZ = [NaN, NaN, NaN]

            leftEyeOnScreen_XY = [NaN, NaN]
            leftEyeInHead_XYZ = [NaN, NaN, NaN]
            leftEyeBasePoint_XYZ = [NaN, NaN, NaN]
            leftEyeScreenDistance = NaN
            leftEyeLensDistance = NaN
            leftPupilRadius = NaN
            leftPupilPos_XYZ = [NaN, NaN, NaN]

            eyeTimeStamp = NaN
            IOD = NaN
            IPD = NaN

        ##### Eye nodes
        if currentSample:

            cycEyeNodeInWorld_XYZ = viz.MainView.getPosition()
            rightEyeNodeInWorld_XYZ = self.gazeNodes.rightEyeBase.getPosition(viz.ABS_GLOBAL)
            leftEyeNodeInWorld_XYZ = self.gazeNodes.leftEyeBase.getPosition(viz.ABS_GLOBAL)

            rightEyeNodeInHead_XYZ = self.gazeNodes.rightEyeBase.getPosition(viz.ABS_PARENT)
            leftEyeNodeInHead_XYZ = self.gazeNodes.leftEyeBase.getPosition(viz.ABS_PARENT)

            cycMat_4x4 = viz.MainView.getMatrix(viz.ABS_GLOBAL).data
            rightEyeMat_4x4 = self.gazeNodes.rightEyeBase.getMatrix(viz.ABS_GLOBAL).data
            leftEyeMat_4x4 = self.gazeNodes.leftEyeBase.getMatrix(viz.ABS_GLOBAL).data

            cycInverseMat_4x4 = viz.MainView.getMatrix(viz.ABS_GLOBAL).inverse().data
            rightEyeInverseMat_4x4 = self.gazeNodes.rightEyeBase.getMatrix(viz.ABS_GLOBAL).inverse().data
            leftEyeInverseMat_4x4 = self.gazeNodes.leftEyeBase.getMatrix(viz.ABS_GLOBAL).inverse().data

            cycGazeNodeInWorld_XYZ = self.gazeNodes.cycGazePoint.getPosition(viz.ABS_GLOBAL)
            rightGazeNodeInWorld_XYZ = self.gazeNodes.rightEyeGazePoint.node3D.getPosition(viz.ABS_GLOBAL)
            leftGazeNodeInWorld_XYZ = self.gazeNodes.leftEyeGazePoint.node3D.getPosition(viz.ABS_GLOBAL)

            # cycGazeNodeInHead_XYZ = viz.MainView.getPosition(viz.ABS_PARENT)
            # rightGazeNodeInHead_XYZ = self.gazeNodes.rightEyeGazePoint.node3D.getPosition(viz.ABS_PARENT)
            # leftGazeNodeInHead_XYZ = self.gazeNodes.leftEyeGazePoint.node3D.getPosition(viz.ABS_PARENT)
        else:
            cycEyeNodeInWorld_XYZ = [NaN, NaN, NaN]
            rightEyeNodeInWorld_XYZ = [NaN, NaN, NaN]
            leftEyeNodeInWorld_XYZ = [NaN, NaN, NaN]

            rightEyeNodeInHead_XYZ = [NaN, NaN, NaN]
            leftEyeNodeInHead_XYZ = [NaN, NaN, NaN]

            cycMat_4x4 = [NaN] * 16
            rightEyeMat_4x4 = [NaN] * 16
            leftEyeMat_4x4 = [NaN] * 16

            cycInverseMat_4x4 = [NaN] * 16
            rightEyeInverseMat_4x4 = [NaN] * 16
            leftEyeInverseMat_4x4 = [NaN] * 16

            cycGazeNodeInWorld_XYZ = [NaN, NaN, NaN]
            rightGazeNodeInWorld_XYZ = [NaN, NaN, NaN]
            leftGazeNodeInWorld_XYZ = [NaN, NaN, NaN]

            #cycGazeNodeInHead_XYZ = [NaN, NaN, NaN]
            #rightGazeNodeInHead_XYZ = [NaN, NaN, NaN]
            #leftGazeNodeInHead_XYZ = [NaN, NaN, NaN]

        if self.config.use_eyeTracking and self.calibTools and self.calibTools.calibrationInProgress:
            tempVar = self.calibTools.calibrationBlockCounter + self.calibTools.calibrationCounter
        else:
            tempVar = self.trialNumber

        if self.currentTrial.useBlankDur:
            preBlankDur = self.currentTrial.preBlankDur
            blankDur = self.currentTrial.blankDur
            postBlankDur = self.currentTrial.postBlankDur
        else:
            preBlankDur = NaN
            blankDur  = NaN
            postBlankDur  = NaN

        # Actual data structuring happens here
        dataDict = dict(
            frameTime = viz.getFrameTime(),
            #smiNsSinceStart = smiServerTime,
            trialNumber = tempVar,
            blockNumber = self.blockNumber,
            eventFlag = self.eventFlag.status,
            trialType = self.currentTrial.trialType,

            # body related
            maxReach = maxReach,
            noExpansionForLastXSeconds = noExpansionForLastXSeconds,

            # mainView
            viewPos_XYZ = viewPos_XYZ,
            viewMat_4x4 = viz.MainView.getMatrix().data,
            viewQuat_XYZW = viz.MainView.getQuat(),

            # Calibration
            inCalibrationQ = self.inCalibrateMode, #calibTools.calibrationInProgress,
            isCalibratedSMIQ = self.calibrationDoneSMI,
            calibrationCounter = calibrationCounter, #calibTools.calibrationCounter,
            calibrationPos_XYZ = [calibrationPoint_XYZ[0], calibrationPoint_XYZ[1], calibrationPoint_XYZ[2]],

            # Paddle
            paddlePos_XYZ = [paddlePos_XYZ[0], paddlePos_XYZ[1], paddlePos_XYZ[2]],
            paddleQuat_XYZW = [paddleQuat_XYZW[0], paddleQuat_XYZW[1], paddleQuat_XYZW[2], paddleQuat_XYZW[3]],
            paddleMat_4x4 = paddleMat_4x4,

            # Ball
            ballPos_XYZ = [ballPos_XYZ[0], ballPos_XYZ[1], ballPos_XYZ[2]],
            ballVel_XYZ = [ballVel_XYZ[0], ballVel_XYZ[1], ballVel_XYZ[2]],
            ballMat_4x4 = ballMat_4x4,
            isBallVisibleQ = ballVisible,
            ballInitialPos_XYZ = [self.currentTrial.ballInitialPos_XYZ[0], self.currentTrial.ballInitialPos_XYZ[1], self.currentTrial.ballInitialPos_XYZ[2]],
            ballFinalPos_XYZ = [self.currentTrial.ballFinalPos_XYZ[0], self.currentTrial.ballFinalPos_XYZ[1], self.currentTrial.ballFinalPos_XYZ[2]],
            ballInitialVel_XYZ = [self.currentTrial.initialVelocity_XYZ[0], self.currentTrial.initialVelocity_XYZ[1], self.currentTrial.initialVelocity_XYZ[2]],
            ballTTC = self.currentTrial.timeToContact,
            ballRadiusM = ballRadiusM,
            #ballLaunch_AE = [self.currentTrial.beta,self.currentTrial.theta],

            # Trajectory

            preBlankDur = preBlankDur,
            blankDur = blankDur,
            postBlankDur = postBlankDur,

            # Eye geometry
            eyeTimeStamp = eyeTimeStamp,
            IOD = IOD,
            IPD = IPD,

            # Cyclopean gaze
            cycEyeOnScreen_XY = cycEyeOnScreen_XY,
            cycEyeInHead_XYZ = cycEyeInHead_XYZ,
            cycEyeBasePoint_XYZ = cycEyeBasePoint_XYZ,
            cycEyeNodeInWorld_XYZ = cycEyeNodeInWorld_XYZ,
            cycMat_4x4 = cycMat_4x4,
            cycInverseMat_4x4 = cycInverseMat_4x4,
            cycGazeNodeInWorld_XYZ = cycGazeNodeInWorld_XYZ,
            #cycGazeNodeInHead_XYZ = cycGazeNodeInHead_XYZ,

            # Right gaze
            rightPupilRadius = rightPupilRadius,
            rightEyeLensDistance = rightEyeLensDistance,
            rightEyeScreenDistance = rightEyeScreenDistance,
            rightEyeBasePoint_XYZ = rightEyeBasePoint_XYZ,
            rightEyeInHead_XYZ =  rightEyeInHead_XYZ,
            rightEyeOnScreen_XY = rightEyeOnScreen_XY,
            rightPupilPos_XYZ = rightPupilPos_XYZ,

            rightEyeNodeInWorld_XYZ = rightEyeNodeInWorld_XYZ,
            rightEyeNodeInHead_XYZ = rightEyeNodeInHead_XYZ,
            rightEyeMat_4x4 = rightEyeMat_4x4,
            rightEyeInverseMat_4x4 = rightEyeInverseMat_4x4,
            rightGazeNodeInWorld_XYZ = rightGazeNodeInWorld_XYZ,
            #rightGazeNodeInHead_XYZ = rightGazeNodeInHead_XYZ,

            # Left gaze
            leftPupilRadius = leftPupilRadius,
            leftEyeLensDistance = leftEyeLensDistance,
            leftEyeScreenDistance = leftEyeScreenDistance,
            leftEyeBasePoint_XYZ = leftEyeBasePoint_XYZ,
            leftEyeInHead_XYZ =  leftEyeInHead_XYZ,
            leftEyeOnScreen_XY = leftEyeOnScreen_XY,
            leftPupilPos_XYZ = leftPupilPos_XYZ,

            leftEyeNodeInWorld_XYZ = leftEyeNodeInWorld_XYZ,
            leftEyeNodeInHead_XYZ = leftEyeNodeInHead_XYZ,
            leftEyeMat_4x4 = leftEyeMat_4x4,
            leftEyeInverseMat_4x4 = leftEyeInverseMat_4x4,
            leftGazeNodeInWorld_XYZ = leftGazeNodeInWorld_XYZ,
            #leftGazeNodeInHead_XYZ = leftGazeNodeInHead_XYZ,
        )

        # seems redundant to cast as dict again
        logging.info(dict(dataDict))
        return

    def registerWiimoteActions(self):

        wii = viz.add('wiimote.dle')#Add wiimote extension

        vizact.onsensordown(self.config.wiimote, wii.BUTTON_B, self.launchKeyDown)
        vizact.onsensorup(self.config.wiimote, wii.BUTTON_B, self.launchKeyUp)
        vizact.onsensordown(self.config.wiimote, wii.BUTTON_DOWN, self.callSMICalibration)
        vizact.onsensordown(self.config.wiimote, wii.BUTTON_A, self.startPerForMCalibration)
        vizact.onsensordown(self.config.wiimote, wii.BUTTON_1, self.updateCalibrationPoint)
        vizact.onsensordown(self.config.wiimote, wii.BUTTON_2, self.recordCalibrationData)
        vizact.onsensordown(self.config.wiimote, wii.BUTTON_PLUS, self.config.eyeTracker.acceptCalibrationPoint)

        if self.config.use_phasespace:
            mocapSys = self.config.mocap

            #vizact.onsensorup(self.config.wiimote,wii.BUTTON_DOWN,mocapSyc.resetRigid,'hmd')
            #vizact.onsensorup(self.config.wiimote,wii.BUTTON_UP,mocapSys.saveRigid,'hmd')
            #vizact.onsensorup(self.config.wiimote,wii.BUTTON_LEFT,mocapSys.resetRigid,'paddle')
            #vizact.onsensorup(self.config.wiimote,wii.BUTTON_RIGHT,mocapSys.saveRigid,'paddle')

            def resetHelmetOrientation():

                mocapSys = self.config.mocap
                mocapSys.resetRigid('hmd')

                # Get diff between current heading and world X
                rt_YPR = vizconnect.getTracker('rift_tracker').getLink().getEuler()
                oriLink = vizconnect.getTracker('rift_tracker').getLink()
                oriLink.reset(viz.RESET_OPERATORS)
                #oriLink.preEuler([-rt_YPR[0], -rt_YPR[1], 0], target=viz.LINK_ORI_OP, priority=-20)
                #oriLink.preEuler([-rt_YPR[0], -rt_YPR[1], -rt_YPR[2]], target=viz.LINK_ORI_OP, priority=-20)

            vizact.onsensorup(self.config.wiimote,wii.BUTTON_UP,vizconnect.getTracker('rift_tracker').resetHeading)
            #vizact.onsensordown(self.config.wiimote,wii.BUTTON_UP,resetHelmetOrientation)


    def endExperiment(self):

        # If recording data, I recommend ending the experiment using:
        #vizact.ontimer2(.2,0,self.endExperiment)
        # This will end the experiment a few frame later, making sure to get the last frame or two of data
        # This could cause problems if, for example, you end the exp on the same that the ball dissapears
        # ...because the eventflag for the last trial would never be recorded

        viz.playSound(soundBank.gong)

        # shut 'er down
        self.logger.removeHandler(self.fhandler)
        self.fhandler.flush()
        self.fhandler.close()

        print('End of Experiment ==> TxT file Saved & Closed')

        self.inProgress = False
        self.enableWritingToLog = False


    def checkDVRStatus(self):

        dvrWriter = self.config.writer

        if dvrWriter.isPaused == 1:
            print('************************************ DVR IS PAUSED ************************************')

    def linkObjectsUsingMocap(self):
        return
        mocap = self.config.mocap
        mocap.start_thread()

        self.setupPaddle()

        trackerDict = vizconnect.getTrackerDict()

        if 'rift_tracker' in trackerDict.keys():
            mocap = self.config.mocap
            self.viewAct = vizact.onupdate(viz.PRIORITY_LINKS, self.updateHeadTracker)
    
    def updateHeadTracker(self):
        """
        A specailized per-frame function
        That updates an empty viznode with:
        - position info from mocap
        - orientation from rift
        """


        riftOriTracker = vizconnect.getTracker('rift_tracker').getNode3d()
        self.headTracker = vizconnect.getRawTracker('head_tracker')
        ori_xyz = riftOriTracker.getEuler()
        self.headTracker.setEuler( ori_xyz  )

        headRigidTracker = self.config.mocap.get_rigidTracker('hmd')
        newPos = headRigidTracker.get_position()
        self.headTracker.setPosition( newPos )

    def setupPaddle(self):

        mocap = self.config.mocap

        # Performs several functions
        # Creates either a fake paddle, a visual paddle, or a vis/phy/mocap paddle

        # FOr debugging. Creates a fake paddle in teh center of the room
        if self.config.expCfg['experiment']['useFakePaddle']:

            #				if(any("paddle" in idx for idx in self.room.visObjNames_idx)):
            #					print 'removed paddle'
            #					self.room.paddle.remove()

            # Put a fake stationary paddle in the room
            paddleSize = [0.03, 2.25]
            self.room.paddle = visEnv.visObj(self.room,'cylinder_Z',paddleSize)
            self.room.paddle.enablePhysNode()
            self.room.paddle.node3D.setPosition(self.currentTrial.passingPlanePosition) #([0,1.6,-1])
            self.room.paddle.node3D.color([0,1,0])
            self.room.paddle.node3D.alpha(0.5)

            #self.room.paddle.enablePhysNode()
            self.room.paddle.physNode.isLinked = 1
            paddleToPhysLink = viz.link( self.room.paddle.node3D, self.room.paddle.physNode.node3D)

            return

        # If there is a visObj paddle and a paddle rigid, link em up!
        if any("paddle" in idx for idx in self.room.visObjNames_idx):
            paddleRigid  = mocap.get_rigidTracker('paddle')
            if(paddleRigid ):

                print('Setup paddle')
                paddle = self.room.paddle

                self.room.paddle.node3D.alpha(0.5)

                #paddle.node3D.setPosition(self.currentTrial.passingPlanePosition) #([0,1.6,-1])

                paddleRigidTracker = mocap.get_rigidTracker('paddle')
                paddleRigidTracker.link_pose(paddle.node3D,'preEuler([90,0,0])')

                paddle.enablePhysNode()

                paddle.physNode.isLinked = 1
                #paddleToPhysLink = viz.link( self.room.paddle.node3D, self.room.paddle.physNode.node3D)
                paddleToPhysLink = viz.link( paddle.node3D, paddle.physNode.node3D)

                def printPaddlePos():
                    #print 'VIS ' + str(paddle.node3D.getPosition())
                    print('node ' + str(paddle.physNode.node3D.getPosition()))
                    print('geom ' + str(paddle.physNode.geom.getPosition()))
                    print('body' + str(paddle.physNode.body.getPosition()))

                    #vizact.ontimer2(0.25,viz.FOREVER,printPaddlePos)
        
    def setupPaddleVive(self):

        # If there is a visObj paddle and a paddle rigid, link em up!
        if any("paddle" in idx for idx in self.room.visObjNames_idx):
            
            #paddleRigid  = mocap.get_rigidTracker('paddle')
            import steamvr
            
            viveTracker = False
            
            if steamvr.getControllerList():
                viveTracker = steamvr.getControllerList()[0]
            else:
                print('No vive controller found')
                return 
            
            if(viveTracker ):

                paddleVisNode = self.room.paddle
                self.room.paddle.node3D.alpha(0.5)
                paddleVisNode.enablePhysNode()
                paddleVisNode.physNode.isLinked = 1
                
                #viveTracker.getPosition()
                
                
                #paddleRigidTracker = mocap.get_rigidTracker('paddle')
                #paddleRigidTracker.link_pose(paddle.node3D,'preEuler([90,0,0])')
                viveToPaddleLink = viz.link( viveTracker, paddleVisNode.node3D)
                viveToPaddleLink.preEuler([90,0,0])
                paddleToPhysLink = viz.link( paddleVisNode.node3D, self.room.paddle.physNode.node3D)

                def printPaddlePos():
                    #print 'VIS ' + str(paddle.node3D.getPosition())
                    print('node ' + str(paddle.physNode.node3D.getPosition()))
                    print('geom ' + str(paddle.physNode.geom.getPosition()))
                    print('body' + str(paddle.physNode.body.getPosition()))

                    #vizact.ontimer2(0.25,viz.FOREVER,printPaddlePos)
                        
    def labelDisplays(self):

        winList = viz.getWindowList()
        hmdWin = winList[0]
        expWin = winList[1]

        text1 = viz.addText('HMD',viz.SCREEN)
        text1.renderOnlyToWindows([hmdWin])
        text1.alignment(viz.ALIGN_RIGHT_BOTTOM)
        text1.setPosition([0.8,0.9,0])

        text2 = viz.addText('EXP',viz.SCREEN)
        text2.renderOnlyToWindows([viz.VizWindow(1)])
        text2.setPosition([0.8,0.9,0])

    def turnOnHangar(self):

        model = []

        #def replaceWalls():
        theRoom = self.room
        theRoom.ceiling.node3D.remove()
        theRoom.wall_PosZ.node3D.remove()
        theRoom.wall_NegZ.node3D.remove()
        theRoom.wall_PosX.node3D.remove()
        theRoom.wall_NegX.node3D.remove()
        theRoom.floor.node3D.setPosition(0,-.01,0,viz.RELATIVE)
        theRoom.floor.node3D.visible(viz.OFF)

        model = viz.addChild('hangar.osgb')
        model.setScale([2]*3)
        model.setPosition([0,0.45,30])
        model.emissive([0]*3)
        model.setEuler([-90,0,0])

        theRoom.hangar = model

    def endTrial(self):

        def stopLogging():
            self.enableWritingToLog = False
            self.stopLogAct.remove()

        self.stopLogAct = vizact.onupdate(viz.PRIORITY_FIRST_UPDATE,stopLogging)

        print('End Trial{', self.enableWritingToLog,'}')

        endOfTrialList = len(self.blocks_bl[self.blockNumber].trials_tr)

        if( self.trialNumber < endOfTrialList ):

            recalAfterTrial_idx = self.blocks_bl[self.blockNumber].recalAfterTrial_idx

            eyeTracker = experimentObject.config.eyeTracker

            if( recalAfterTrial_idx.count(self.trialNumber ) > 0):

                self.calibTools.calibrationInProgress = True
                vizact.ontimer2(0,0,eyeTracker.calibrate(type = smi.CALIBRATION_9_POINT ))

                self.calibTools.calibrationInProgress = False
                print('Static Calibration Method is Called after %d trials' %(recalAfterTrial_idx.count(self.trialNumber )))
                self.calibTools.staticCalibrationMethod()

            # Increment trial
            self.trialNumber += 1
            self.killtimer(self.maxFlightDurTimerID)

            if self.currentTrial.useBlankDur:
                self.killtimer(self.ballPreBlankDurTimerID)
                self.killtimer(self.ballBlankDurTimerID)

            #self.eventFlag.setStatus(6)
            self.eventFlag.setStatus('trialEnd')

        if( self.trialNumber == endOfTrialList ):


            self.eventFlag.setStatus('blockEnd')

            self.blockNumber += 1
            self.trialNumber = 0

            # Increment block or end experiment
            if( self.blockNumber == len(self.blocks_bl) ):

                # Run this once on the next frame
                # This maintains the ability to record one frame of data
                self.enableWritingToLog = False
                vizact.ontimer2(0,0,self.endExperiment)
                return

        if( self.inProgress ):

            print('Starting block: ' + str(self.blockNumber) + ' Trial: ' + str(self.trialNumber))
            self.currentTrial = self.blocks_bl[self.blockNumber].trials_tr[self.trialNumber]


    def turnOffWalls(self):

        model = []

        #def replaceWalls():
        theRoom = self.room
        theRoom.ceiling.node3D.remove()
        theRoom.wall_PosZ.node3D.remove()
        theRoom.wall_NegZ.node3D.remove()
        theRoom.wall_PosX.node3D.remove()
        theRoom.wall_NegX.node3D.remove()

        with viz.cluster.MaskedContext(viz.MASTER):
            viz.MainWindow.clearcolor([0.3]*3)

        with viz.cluster.MaskedContext(viz.CLIENT1):
            viz.MainWindow.clearcolor([0.3]*3)

        #theRoom.floor.node3D.setPosition(0,-.01,0,viz.RELATIVE)
        #theRoom.floor.node3D.visible(viz.OFF)


        theRoom.hangar = model

    def updateTextObject(self, textObject):

        if (experimentObject.config.use_eyeTracking):

            if self.config.sysCfg['eyetracker']['type'] == 'SMIVIVE':
                textObject.message('Tr# = %d \n B# = %d\n FT = %2.2f\n ET = %2.2f'%(self.trialNumber, self.blockNumber, viz.getFrameTime(), self.config.eyeTracker.getTimestamp()))
            else:
                # DK2
                currentSample = self.config.eyeTracker.getLastSample()
                
                if currentSample:
                    textObject.message('Tr# = %d \n B# = %d\n FT = %2.2f\n ET = %2.2f'%(self.trialNumber, self.blockNumber, viz.getFrameTime(), currentSample.getTimestamp()))
                else:
                    textObject.message('Tr# = %d \n B# = %d\n FT = %2.2f\n ET = Nan'%(self.trialNumber, self.blockNumber, viz.getFrameTime()))
                return

    def showEyeTrackVive(self):

        eyeTracker = self.config.eyeTracker
        headTracker = vizconnect.getRawTrackerDict()['head_tracker']
        dispDict = vizconnect.getRawDisplayDict()
        clientWindowID = dispDict['exp_display']

        self.gazeNodes = viz.addGroup()

        self.gazeNodes.cycEyeBase = gazeSphere(eyeTracker,viz.BOTH_EYE,headTracker,[clientWindowID],viz.GREEN)
        self.gazeNodes.cycEyeBase.toggleUpdate()
        self.gazeNodes.cycGazePoint = vizshape.addSphere(0.015, color = viz.GREEN)
        self.gazeNodes.cycGazePoint.setParent(headTracker)
        #cyclopEyeNode.visible(viz.OFF)
        self.gazeNodes.cycGazePoint.alpha(0.00)

        # TODO: Instead of passing both Eye node and sphere one should be enough (KAMRAN)
        #        self.calibTools = calibrationTools(self.gazeNodes.cycGazePoint, clientWindowID, self.gazeNodes.cycEyeBase, self.config, self.room)
        #        self.calibTools.create3DCalibrationPositions(self.calibTools.calibrationPositionRange_X, self.calibTools.calibrationPositionRange_Y, self.calibTools.calibrationPositionRange_Z, self.calibTools.numberOfCalibrationPoints)

        self.gazeNodes.IOD = IOD = self.config.sysCfg['eyetracker']['defaultIOD']

        # create a node3D self.gazeNodes.leftEyeBase
        self.gazeNodes.leftEyeBase = vizshape.addSphere(0.005, color = viz.BLUE)
        #self.gazeNodes.leftEyeBase.visible(viz.OFF)
        self.gazeNodes.leftEyeBase.setParent(headTracker)
        self.gazeNodes.leftEyeBase.setPosition(-IOD/2, 0, 0.0,viz.ABS_PARENT)
        self.gazeNodes.leftEyeGazePoint = gazeSphere(eyeTracker,viz.LEFT_EYE,self.gazeNodes.leftEyeBase,[clientWindowID],sphereColor=viz.YELLOW)
        self.gazeNodes.leftGazeVector = gazeVector(eyeTracker,viz.LEFT_EYE,self.gazeNodes.leftEyeBase,[clientWindowID],gazeVectorColor=viz.YELLOW)
        self.gazeNodes.leftEyeGazePoint.toggleUpdate()
        self.gazeNodes.leftGazeVector.toggleUpdate()
        self.gazeNodes.leftEyeGazePoint.node3D.alpha(0.7)
        self.gazeNodes.leftEyeBase.alpha(0.01)

        # create a node3D self.gazeNodes.rightEyeBase
        self.gazeNodes.rightEyeBase = vizshape.addSphere(0.005, color = viz.RED)
        #self.gazeNodes.rightEyeBase.visible(viz.OFF)
        self.gazeNodes.rightEyeBase.setParent(headTracker)
        self.gazeNodes.rightEyeBase.setPosition(IOD/2, 0, 0.0,viz.ABS_PARENT)
        self.gazeNodes.rightEyeGazePoint = gazeSphere(eyeTracker,viz.RIGHT_EYE,self.gazeNodes.rightEyeBase,[clientWindowID],sphereColor=viz.ORANGE)
        self.gazeNodes.rightEyeGazeVector = gazeVector(eyeTracker,viz.RIGHT_EYE,self.gazeNodes.rightEyeBase,[clientWindowID],gazeVectorColor=viz.ORANGE)
        self.gazeNodes.rightEyeGazePoint.toggleUpdate()
        self.gazeNodes.rightEyeGazeVector.toggleUpdate()
        self.gazeNodes.rightEyeGazePoint.node3D.alpha(0.7)
        self.gazeNodes.rightEyeBase.alpha(0.01)

    def timeStampOnScreen(self):
        clientWindowID = dispDict['exp_display']
        experimentTextObject = viz.addText('',viz.SCREEN)
        experimentTextObject.setBackdrop(1)
        experimentTextObject.color(viz.RED)
        experimentTextObject.setPosition([0.01,.99,0])
        experimentTextObject.alignment(viz.ALIGN_LEFT_TOP)
        textScale = 0.3
        experimentTextObject.setScale([textScale]*3)
        experimentTextObject.renderOnlyToWindows([clientWindowID])
        textUpdateAction = vizact.onupdate(viz.PRIORITY_INPUT+1,experimentObject.updateTextObject, experimentTextObject)#self.currentTrial.ballObj.node3D
        return experimentTextObject

############################################################################################################
############################################################################################################

class eventFlag(viz.EventClass):
    '''
    Create an event flag object
    This var is set to an int on every frame
    The int saves a record of what was happening on that frame
    It can be configured to signify the start of a trial, the bounce of a ball, or whatever
    '''

    def __init__(self):

        ################################################################
        ##  Eventflag

        # 1 ball launched
        # 2 * not used *
        # 3 ball has hit floor
        # 4 ball has hit paddle
        # 5 ball has hit back wall
        # 6 trial end
        # 7 block end
        # 8 ball invisible
        # 9 ball visible

        viz.EventClass.__init__(self)

        self.status = False
        self.lastFrameUpdated = viz.getFrameNumber()
        self.currentValue = False

        # On every frame, self.eventFlag should be set to 0
        # This should happen first, before any timer object has the chance to overwrite it!
        vizact.onupdate(viz.PRIORITY_FIRST_UPDATE,self._resetEventFlag)

    def setStatus(self,status,overWriteBool = False):

        if( self.lastFrameUpdated != viz.getFrameNumber() ):

            #print 'Setting status to' + str(status)

            self.status = status
            self.lastFrameUpdated = viz.getFrameNumber()

        elif( overWriteBool is True and self.lastFrameUpdated == viz.getFrameNumber() ):

            #print 'Overwrite from status ' + str(self.status) + ' to ' + str(status)

            self.status = status
            self.lastFrameUpdated = viz.getFrameNumber()


        elif( self.lastFrameUpdated == viz.getFrameNumber() ):

            #print 'Stopped attempt to overwrite status of ' + str(self.status) + ' with ' + str(status) + ' [overWriteBool=False]'
            pass

    def _resetEventFlag(self):

        #This should run before timers, eyeTrackingCal.  Called using <vizact>.onupdate
        if( self.lastFrameUpdated == viz.getFrameNumber() ):
            print('Did not reset! Status already set to ' + str(self.status))
        else:
            self.status = False # 0 Means nothing is happening


class block():
    def __init__(self,config = None, blockNum = 1, room = None):

        # Each block will have a block.trialTypeList
        # This list is a list of strings of each trial type
        # Types included and frequency of types are defined in the config
        # Currently, these trial types are automatically randomized
        # e.g. 't1,t2,t2,t2,t1'

        self.room = room
        self.blockName = config.expCfg['experiment']['blockList'][blockNum]

        #    Kinds of trial in this block

        # THe type of each trial
        # _tr indicates that the list is as long as the number of trials
        self.trialTypeList_tr = []
        self.trialTypesInBlock = []
        self.numOfEachTrialType_type = []

        # Note that this list may contain empty entires.  This is checked inside the for loop
        for typeIdx, trialType in enumerate(config.expCfg['blocks'][self.blockName]['trialTypesString'].split(',')):
            if trialType: # Will return false if trialType is an empty string
                self.numOfEachTrialType_type.append( int(config.expCfg['blocks'][self.blockName]['trialTypeCountString'].split(',')[typeIdx] ))
                self.trialTypesInBlock.extend( config.expCfg['blocks'][self.blockName]['trialTypesString'].split(',')[typeIdx] )
                self.trialTypeList_tr.extend( [trialType] * self.numOfEachTrialType_type[typeIdx] )

        # Randomize trial order
        from random import shuffle
        shuffle(self.trialTypeList_tr)

        self.numTrials = len(self.trialTypeList_tr)
        self.recalAfterTrial_idx = config.expCfg['blocks'][self.blockName]['recalAfterTrial']

        self.trials_tr = []

        for trialNumber in range(self.numTrials):

            ## Get trial info
            trialObj = trial(config, self.trialTypeList_tr[trialNumber], self.room)

            ##Add the body to the list
            self.trials_tr.append(trialObj)

            ## Create a generator this will loop through the balls
            #nextBall = viz.cycle(balls)

class trial(viz.EventClass):
    def __init__(self,config=None, trialType='t1', room = None):

        #viz.EventClass.__init__(self)

        self.trialType = trialType

        self.room = room
        self.config = config

        self.changeBallRadiusID = []

        ## State flags
        self.ballInRoom = False # Is ball in room?
        self.ballInInitialState = False # Is ball ready for launch?
        self.ballLaunched = False # Has a ball been launched?  Remains true after ball disappears.
        self.ballHasBouncedOnFloor = False
        self.ballHasHitPaddle = False
        self.ballHasHitPassingPlane = False

        self.isLeftHanded = config.expCfg['experiment']['isLeftHanded']

        ## Trial event data
        self.ballOnPaddlePos_XYZ = []
        self.ballOnPaddlePosLoc_XYZ = []

        ## Related to expansion
        self.noExpansionForLastXSeconds = float(config.expCfg['experiment']['noExpansionForLastXSeconds'])
        self.ballResizeAct = []

        self.myMarkersList = []
        ## Timer objects
        self.timeSinceLaunch = []

        self.ballObj = False

        ### Below this is all the code used to generate ball trajectories
        self.ballFlightMaxDur = float(config.expCfg['experiment']['ballFlightMaxDur'])

        #  Set ball color.
        try:
            self.ballColor_RGB = map(float,config.expCfg['trialTypes'][self.trialType]['ballColor_RGB'])
        except:
            print('Using def color')
            self.ballColor_RGB = map(float,config.expCfg['trialTypes']['default']['ballColor_RGB'])


        self.initialBallRadiusM = float(config.expCfg['trialTypes'][self.trialType]['initialBallRadiusM'])
        self.passingLocNormX = float(config.expCfg['trialTypes'][self.trialType]['passingLocNormX'])

        self.gravity_distType = []
        self.gravity_distParams = []
        self.gravity = []

        ballElasticity_distType = []
        ballElasticity_distParams = []
        ballElasticity = []

        #====================================================================
        #====== Launching and Passing Planes sizes are determined here ======
        #====================================================================

        self.passingPlaneSize = map(float, config.expCfg['room']['passingPlaneSize_WHL'])
        self.launchPlaneSize = map(float, config.expCfg['room']['launchPlaneSize_WH'])
        self.passingPlanePosition = map(float, config.expCfg['room']['passingPlanePos_XYZ'])
        self.launchPlanePosition = map(float, config.expCfg['room']['launchPlanePos_XYZ'])

        self.distanceAlongZ = self.launchPlanePosition[2] - self.passingPlanePosition[2]

        self.timeToContact = []
        self.presentationDuration = []
        self.blankDur = []
        self.postBlankDuration = []
        self.beta = []
        self.theta = []
        self.initialVelocity_XYZ = []

        self.passingLocNormY = []

        self.useBlankDur = float(config.expCfg['trialTypes'][self.trialType]['useBlankDur'])

        self.expansionGain = float(config.expCfg['trialTypes'][self.trialType]['expansionGain'])

        if self.useBlankDur :
            self.blankDur = float(config.expCfg['trialTypes']['default']['blankDur'])
            self.preBlankDur = float(config.expCfg['trialTypes'][self.trialType]['preBlankDur'])
            self.postBlankDur = float(config.expCfg['trialTypes'][self.trialType]['postBlankDur'])
            self.timeToContact = self.preBlankDur + self.blankDur + self.postBlankDur

        ## Initial position


        self.ballInitialPos_XYZ = [0,0,0]
        self.initialVelocity_XYZ = [0,0,0]
        self.ballFinalPos_XYZ = [0,0,0]

        self.flightDurationError = []

        ##########################################################################
        ##########################################################################
        # Go into config file and define values
        # When a distribution is specified, select a value from the distribution

        variablesInATrial = config.expCfg['trialTypes']['default'].keys()

        for varIdx in range(len(variablesInATrial)):
            if "_distType" in variablesInATrial[varIdx]:

                varName = variablesInATrial[varIdx][0:-9]


                try:
                    distType, distParams, value = self._setValueOrUseDefault(config,varName)
                except:
                    print('Error in main.trial.init.drawNumberFromDist()')
                    print('Variable name is: ' + varName)

                try:
                    exec( 'self.' + varName + '_distType = distType' )
                    exec( 'self.' + varName + '_distParams = distParams' )
                    exec( 'self.' + varName + '_distType = distType' )
                    # Draw value from a distribution
                    exec( 'self.' + varName + ' = drawNumberFromDist( distType , distParams);' )
                except:
                    print('Error in main.trial.init')
                    print('Variable name is: ' + varName)




    def removeBall(self):

        print('Removing ball')

        self.ballObj.remove()
        self.ballObj = False

        self.ballInRoom = False
        self.ballInInitialState = False
        self.ballLaunched = False

        if self.ballResizeAct:
            self.ballResizeAct.remove()

        print('Cleaned up ball')

    def _setValueOrUseDefault(self,config,paramPrefix):

        try:
            #print paramPrefix
            # Try to values from the subsection [[trialType]]
            distType = config.expCfg['trialTypes'][self.trialType][paramPrefix + '_distType']
            distParams = config.expCfg['trialTypes'][self.trialType][paramPrefix +'_distParams']

        except:
            # print 'Using default: **' + paramPrefix + '**'
            # Try to values from the subsection [['default']]
            distType = config.expCfg['trialTypes']['default'][paramPrefix + '_distType']
            distParams = config.expCfg['trialTypes']['default'][paramPrefix + '_distParams']


        value = drawNumberFromDist(distType,distParams)


        return distType,distParams,value


    def placeLaunchPlane(self):

        #adds a transparent plane that the ball is being launched from it
        self.room.launchPlane = vizshape.addPlane(size = self.launchPlaneSize , axis=-vizshape.AXIS_Z, cullFace = False)

        if( self.isLeftHanded == True):
            self.launchPlanePosition[0] *= -1

        #shifts the wall to match the edge of the floor
        self.room.launchPlane.setPosition(self.launchPlanePosition)

        #makes the wall appear white
        self.room.launchPlane.color(viz.CYAN)
        self.room.launchPlane.alpha(0.2)
        #self.room.launchPlane.collideBox()
        #self.room.launchPlane.disable(viz.DYNAMICS)
        self.room.launchPlane.visible(False)
        #print('Launch Plane Created!')


    def placePassingPlane(self):

        #adds a transparent plane that the ball ends up in this plane
        self.room.passingPlane = visEnv.visObj(self.room,'box',size = self.passingPlaneSize)#[0.02, planeSize[0], planeSize[0]]



        self.room.passingPlane.node3D.setPosition(self.passingPlanePosition)#[0, 1.5, 1.0]

        #makes the wall appear white
        self.room.passingPlane.node3D.color(viz.PURPLE)
        self.room.passingPlane.node3D.alpha(0.3)
        self.room.passingPlane.node3D.visible(False)

        #print('Passing Plane Created!')

    def placeBall(self, room):

        #        self.expansionGain = viz.input('Expansion gain?')
        #        print('Expansion gain: %1.2f' %self.expansionGain)

        if( self.config.expCfg['maxReach'] is False):
            print('***Must set max reach (shift-z)****')
            self.room.standingBox.visible(viz.TOGGLE)
            viz.playSound(soundBank.cowbell)
            return

        ##################################################################################################################
        ################### STARTING POSITION ############################################################################

        if( self.isLeftHanded == True):
            launchPlane_XYZ[0] *= -1
            self.passingPlanePosition[0] *= -1
            self.launchPlanePosition[0] *= -1

        self.placeLaunchPlane()
        self.placePassingPlane()

        # Put ball in center of launch plane
        launchPlane_XYZ = self.room.launchPlane.getPosition()
        self.ballInitialPos_XYZ = launchPlane_XYZ

        ### X VALUE
        xMinimumValue = launchPlane_XYZ[0]-self.launchPlaneSize[0]/2.0
        xMaximumValue = launchPlane_XYZ[0]+self.launchPlaneSize[0]/2.0
        self.ballInitialPos_XYZ[0] = xMinimumValue + np.random.random()*(xMaximumValue-xMinimumValue)

        ### Y VALUE
        yMinimumValue = launchPlane_XYZ[1]-self.launchPlaneSize[1]/2.0
        yMaximumValue = launchPlane_XYZ[1]+self.launchPlaneSize[1]/2.0
        self.ballInitialPos_XYZ[1] = yMinimumValue + np.random.random()*(yMaximumValue-yMinimumValue)

        # Move ball relative to center of launch plane
        #print('Initial max/min=[', xMinimumValue, xMaximumValue,']')

        # Sphere radius is initially 0.5, but it is scaled to the correct radius below
        self.ballObj = visEnv.visObj(room,'sphere',0.5,self.ballInitialPos_XYZ,self.ballColor_RGB)

        #########################################################
        ################### FINAL POSITION ###################

        ### X VALUE
        self.ballFinalPos_XYZ = [0,0,0]

        if( self.isLeftHanded ):
            self.ballFinalPos_XYZ[0] = self.room.standingBox.getPosition()[0] - self.config.expCfg['maxReach']*self.passingLocNormX
        else:
            self.ballFinalPos_XYZ[0] = self.room.standingBox.getPosition()[0] + self.config.expCfg['maxReach']*self.passingLocNormX

        self.ballFinalPos_XYZ[1] = self.passingLocNormY

        #########################################################
        ################### Initial Velocities ##################

        self.calculateTrajectory()

        #print('FIXME:  iNITIAL velocity set to 0,0,0')
        #self.initialVelocity_XYZ = [0,0,0]

        #print('PlaceBall ==> Vx=', self.initialVelocity_XYZ[0], ' TTC=', self.timeToContact)

        if self.useBlankDur:
            print('PD = ', self.presentationDuration, ' BD = ', self.blankDur, ' PBD = ', self.postBlankDuration)

        self.ballObj.node3D.setVelocity([0,0,0])

        ### Enable physics
        self.ballObj.enablePhysNode()
        self.ballObj.linkToPhysNode()
        self.ballObj.physNode.setBounciness(self.ballElasticity)
        self.ballObj.physNode.setStickUponContact( room.paddle.physNode.geom )
        self.ballObj.physNode.disableMovement()
        self.ballObj.radius = self.initialBallRadiusM

        ############################################
        ############################################
        ## Set ball radius
        self.ballObj.radius = self.ballObj.size = self.initialBallRadiusM
        self.setBallRadius(self.initialBallRadiusM)

        ###########################################
        ###########################################

        self.ballObj.initialDistance = np.sqrt(np.sum(np.power(np.subtract(self.ballInitialPos_XYZ,self.ballFinalPos_XYZ),2)))
        #self.ballObj.projectShadows(self.ballObj.parentRoom.floor.node3D) # Costly, in terms of computation

        # Setup state flags

        self.ballInRoom = True
        self.ballInInitialState = True
        self.ballLaunched = False
        self.ballPlacedOnThisFrame = True

    def calculateTrajectory(self):

        # X velocity
        self.lateralDistance = math.fabs(self.ballFinalPos_XYZ[0] - self.ballInitialPos_XYZ[0])
        self.initialVelocity_XYZ[0] = self.lateralDistance/self.timeToContact

        # Z velocity
        self.distanceAlongZ = math.fabs(self.ballFinalPos_XYZ[2] - self.ballInitialPos_XYZ[2])
        self.initialVelocity_XYZ[2] = -self.distanceAlongZ/self.timeToContact

        # Vertical component of velocity
        self.verticalDistance = self.ballFinalPos_XYZ[1] - self.ballInitialPos_XYZ[1]
        self.initialVelocity_XYZ[1] = ((-0.5 * -self.gravity * self.timeToContact * self.timeToContact) + self.verticalDistance ) / self.timeToContact

        self.totalDistance = math.sqrt(np.power(self.lateralDistance, 2) + np.power(self.distanceAlongZ, 2) + np.power(self.verticalDistance, 2))
        self.beta = math.atan((self.distanceAlongZ/self.lateralDistance))*(180.0/np.pi)
        self.theta = (180.0/np.pi)*math.atan((np.power(self.timeToContact,2) * self.gravity)/(2*self.totalDistance))

    #        print('\nMax reach %1.1f' %(self.config.expCfg['maxReach']) )
    #        print('Passing loc norm, %1.1f'%(self.passingLocNormX))
    #        print('Final position %1.1f, %1.1f, %1.1f \n' %(self.ballFinalPos_XYZ[0],self.ballFinalPos_XYZ[1],self.ballFinalPos_XYZ[2]))

    #print 'V_xyz=[',self.initialVelocity_XYZ,'] theta=',self.theta,' beta=', self.beta
    #print 'X=', self.lateralDistance, ' R=', self.totalDistance, ' g=', self.gravity, ' Vxz=', self.horizontalVelocity, ' D=', self.distanceAlongZ

    def launchBall(self):

        if( self.ballObj == False ):
            print('No ball present.')
            return

        self.ballObj.physNode.enableMovement()
        self.ballObj.setVelocity(self.initialVelocity_XYZ)

        self.myMarkersList
        self.ballInRoom = True
        self.ballInInitialState = False
        self.ballLaunched = True

        self.launchTime = viz.getFrameTime()

        # Set "previous" values of ball size, etc
        self.lastBallPos_XYZ = self.ballObj.node3D.getPosition()
        self.lastBallVel_XYZ = self.ballObj.physNode.body.getLinearVel()
        viewPos_xyz = viz.MainView.getPosition()
        curBallPos_XYZ = self.ballObj.node3D.getPosition()
        self.initialDistFromViewToBall = np.sqrt(np.sum(np.array([vXYZ - bXYZ for vXYZ, bXYZ in zip(viewPos_xyz,curBallPos_XYZ)])**2))


        self.lastUnmodifiedBallAngularRadiusRadians = self.lastBallAngularRadiusRadians = np.arctan(self.ballObj.radius / self.initialDistFromViewToBall )
        self.ballResizeAct = vizact.onupdate(viz.PRIORITY_SCENEGRAPH-1,self.scaleRadiusByGain)


    def setBallRadius(self,radius):

        self.ballObj.size = radius
        self.ballObj.radius = radius

        # Initial diameter of 1 meterr
        mat = self.ballObj.node3D.getMatrix()

        for idx in range(0,11,5):
            mat[idx] = radius*2.0

        self.ballObj.node3D.setMatrix(mat)
        self.ballObj.physNode.geom.setRadius(radius)

    #    def scaleRadiusByGain(self):
    #
    #        updatedDistFromViewToBall = np.sqrt(np.sum(np.array([vXYZ - bXYZ for vXYZ, bXYZ in zip(viz.MainView.getPosition(),self.ballObj.node3D.getPosition())])**2))
    #
    #        # r' = d'*tan(k*atan(r/d))
    #        adjustedChangeInAngularSize = updatedDistFromViewToBall * np.tan( self.expansionGain * np.arctan(self.initialBallRadiusM/self.initialDistFromViewToBall))
    #        newRadiusM = updatedDistFromViewToBall * np.tan(adjustedChangeInAngularSize)
    #
    #        ## Set the ball to this physical radius
    #        self.setBallRadius(newRadiusM)
    #        self.ballObj.physNode.geomMass.setSphereTotal(1, newRadiusM)
    #        self.ballObj.physNode.body.setMass(self.ballObj.physNode.geomMass)


    ##    def scaleRadiusByGain(self):
    ##        ### LINEAR METHOD
    ##
    ##        # self.initialBallRadiusM
    ##        ## Calculate current ball radius in degrees
    ##
    ##        updatedBallPos_XYZ = self.ballObj.physNode.body.getPosition()
    ##        updatedBallVel_XYZ = self.ballObj.physNode.body.getLinearVel()
    ##
    ##        updatedBallSpeed = np.sqrt(np.sum([np.array(XYZ)**2.0 for XYZ in updatedBallVel_XYZ]))
    ##        timeToArrival = np.divide(np.sqrt(np.sum(np.array([vXYZ - bXYZ for vXYZ, bXYZ in zip(self.ballFinalPos_XYZ,updatedBallPos_XYZ)])**2)),updatedBallSpeed )
    ##
    ###        if( timeToArrival <= self.noExpansionForLastXSeconds):
    ###            self.ballResizeAct.remove()
    ###            print('Halted resize')
    ###            return
    ##
    ##        updatedViewPos_xyz = self.config.mocap.get_rigidTracker('hmd').get_position()
    ##        updatedDistFromViewToBall = np.sqrt(np.sum(np.array([vXYZ - bXYZ for vXYZ, bXYZ in zip(updatedViewPos_xyz,updatedBallPos_XYZ)])**2.0))
    ##
    ##        # Get change in angular size for original sized ball
    ##        unmodifiedAngularRadiusRadians = np.arctan(self.initialBallRadiusM / updatedDistFromViewToBall)
    ##        unmodifiedDeltaRadians = unmodifiedAngularRadiusRadians - self.lastUnmodifiedBallAngularRadiusRadians
    ##
    ##        ##################################################################################
    ##        ##################################################################################
    ##        # ball size on previous frame + modified change in angular size
    ##        modifiedAngularSizeRads = self.lastBallAngularRadiusRadians  + unmodifiedDeltaRadians * self.expansionGain
    ##
    ##        ## What physical radius (m) would bring about this angular subtense?
    ##        newRadiusM = updatedDistFromViewToBall * np.tan(modifiedAngularSizeRads)
    ##
    ##        ## Set the ball to this physical radius
    ##        self.setBallRadius(newRadiusM)
    ##        self.ballObj.physNode.geomMass.setSphereTotal(1, newRadiusM)
    ##        self.ballObj.physNode.body.setMass(self.ballObj.physNode.geomMass)
    ##
    ##        #angSize = np.arctan(newRadiusM/updatedDistFromViewToBall)
    ##        #print('   Angular size: %1.5f' % np.rad2deg( angSize ) )
    ##
    ##        #print('   Previous size: %1.5f' % np.rad2deg( self.lastUnmodifiedBallAngularRadiusRadians) )
    ##        #print('      Delta degs: %1.5f' % np.rad2deg(unmodifiedDeltaRadians))
    ##        #print('  New metric rad: %1.5f\n' % newRadiusM)
    ##
    ##        self.lastBallAngularRadiusRadians = modifiedAngularSizeRads
    ##        self.lastUnmodifiedBallAngularRadiusRadians = unmodifiedAngularRadiusRadians



    def scaleRadiusByGain(self):

        ###################################
        ###  EXPONENTIAL METHOD


        ## Calculate current ball radius in degrees

        curBallPos_XYZ = self.ballObj.physNode.body.getPosition()
        curBallVel_XYZ = self.ballObj.physNode.body.getLinearVel()
        curBallVel = np.sqrt(np.sum([np.array(XYZ)**2 for XYZ in curBallVel_XYZ]))

        timeToArrival = np.divide(np.sqrt(np.sum(np.array([vXYZ - bXYZ for vXYZ, bXYZ in zip(self.ballFinalPos_XYZ,curBallPos_XYZ)])**2)),curBallVel )

        if( timeToArrival <= self.noExpansionForLastXSeconds):
            self.ballResizeAct.remove()
            print('Halted resize')
            return

        viewPos_xyz = viz.MainView.getPosition()
        curDistFromViewToBall = np.sqrt(np.sum(np.array([vXYZ - bXYZ for vXYZ, bXYZ in zip(viewPos_xyz,curBallPos_XYZ)])**2))
        curAngularRadiusRadians = np.arctan(self.ballObj.radius /curDistFromViewToBall)

        ## Calculate next ball radius in degrees

        frameRate = viz.getFrameElapsed() #math.floor(viz.getFrameElapsed()*10000) /10000
        deltaPos_XYZ = [frameRate * val for val in curBallVel_XYZ]

        nextBallPos_XYZ = [curBallPos_XYZ[0]+deltaPos_XYZ[0],curBallPos_XYZ[1]+deltaPos_XYZ[1],curBallPos_XYZ[2]+deltaPos_XYZ[2]]

        nextDistFromViewToBall = np.sqrt(np.sum(np.array([vXYZ - bXYZ for vXYZ, bXYZ in zip(viewPos_xyz,nextBallPos_XYZ)])**2))
        nextAngularRadiusRadians = np.arctan(self.ballObj.radius /nextDistFromViewToBall)

        ## What would the angular radius be on the next frame, if scaled by the gain term?
        desiredAngularRadiusRads =  curAngularRadiusRadians + (nextAngularRadiusRadians - curAngularRadiusRadians) * self.expansionGain

        ## What physical radius (m) would bring about this angular subtense?
        newRadiusM = nextDistFromViewToBall * np.tan(desiredAngularRadiusRads)

        ## Set the ball to this physical radius
        self.setBallRadius(newRadiusM)
        self.ballObj.physNode.geomMass.setSphereTotal(1, newRadiusM)
        self.ballObj.physNode.body.setMass(self.ballObj.physNode.geomMass)

        #physRad = self.ballObj.physNode.geom.getRadius()

    def scaleRadiusByDistance(self):

        currentDistance = np.sqrt(np.sum(np.power(np.subtract(self.ballObj.node3D.getPosition(),self.ballFinalPos_XYZ),2)))

        totalChangeInBallSize = (self.initialBallRadiusM * self.expansionGain) - self.initialBallRadiusM

        proportionOfFlightTravelled = (self.ballObj.initialDistance - currentDistance) / self.ballObj.initialDistance
        newRadius = self.initialBallRadiusM + (totalChangeInBallSize * proportionOfFlightTravelled )

        self.setBallRadius(newRadius)

        self.ballObj.physNode.geomMass.setSphereTotal(1, newRadius)
        self.ballObj.physNode.body.setMass(self.ballObj.physNode.geomMass)

        physRad = self.ballObj.physNode.geom.getRadius()

    #        print( 'Geom pos:  %1.2f , %1.2f, %1.2f' % (self.ballObj.physNode.geom.getPosition()[0],self.ballObj.physNode.geom.getPosition()[1],self.ballObj.physNode.geom.getPosition()[2]))
    #        print( 'Body pos:  %1.2f , %1.2f, %1.2f' % (self.ballObj.physNode.body.getPosition()[0],self.ballObj.physNode.body.getPosition()[1],self.ballObj.physNode.body.getPosition()[2]))
    #        print(' Viz pos: %1.2f, %1.2f, %1.2f\n' % (self.ballObj.node3D.getPosition()[0],self.ballObj.node3D.getPosition()[1],self.ballObj.node3D.getPosition()[2] ))
    #print( 'Phys Rad:  %1.2f Viz rad: %1.2f' % (physRad, newRadius ))
    #print( 'CurDist: %s New Radius: %s' % (str(currentDistance), str(newRadius) ))




################################################################################################################
################################################################################################################
################################################################################################################
##  Here's where the magic happens!

#experimentConfiguration = vrlabConfig.VRLabConfig(expConfigFileName)

## vrlabConfig uses config to setup hardware, motion tracking, frustum, eyeTrackingCal.
##  This draws upon the system config to setup the hardware / HMD

## The experiment class initialization draws the room, sets up physics,
## and populates itself with a list of blocks.  Each block contains a list of trials


experimentObject = Experiment(expConfigFileName)
experimentObject.start()


dispDict = vizconnect.getRawDisplayDict()
clientWindowID = dispDict['exp_display']
textObj = experimentObject.timeStampOnScreen()


#
#
## Setup SteamVR HMD
#import steamvr
#hmd = steamvr.HMD()
#if not hmd.getSensor():
#	sys.exit('SteamVR HMD not detected')
#
## Setup navigation node and link to main view
#navigationNode = viz.addGroup()
#viewLink = viz.link(navigationNode, viz.MainView)

    
#experimentObject.showEyeTrackVive()
gazeNodes = viz.addGroup()

import steamvr
hmd = steamvr.HMD()
gazeNodes.leftEyeBase = vizshape.addSphere(0.05, color = viz.BLUE)
vl = viz.link(hmd.getSensor(), gazeNodes.leftEyeBase)
vl.preTrans([-.06/2, 1, 0.0])


gazeNodes.leftEyeGazePoint = gazeSphere(experimentObject.config.eyeTracker,viz.LEFT_EYE,gazeNodes.leftEyeBase,[clientWindowID],sphereColor=viz.YELLOW)

#gazeNodes.leftGazeVector = gazeVector(eyeTracker,viz.LEFT_EYE,gazeNodes.leftEyeBase,[clientWindowID],gazeVectorColor=viz.YELLOW)
#gazeNodes.leftEyeGazePoint.toggleUpdate()
#gazeNodes.leftGazeVector.toggleUpdate()
#gazeNodes.leftEyeGazePoint.node3D.alpha(0.7)
#gazeNodes.leftEyeBase.alpha(0.01)
