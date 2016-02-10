"""
Runs an experiment.
"""

import viz
import viztask
#import vrlabConfig
import vizshape
import vizact
from drawNumberFromDist import *
import visEnv
import physEnv
import ode
import datetime
from ctypes import * # eyetrackka
import vizconnect
import random
import math
import smi
import numpy as np
import pandas as pd
#For hardware configuration
viz.res.addPath('resources')
sys.path.append('utils')
from configobj import ConfigObj
from configobj import flatten_errors
from validate import Validator
import platform
import os.path
import vizconnect
from gazeTools import calibrationTools
import logging

#expConfigFileName = 'badmintonTest.cfg'
expConfigFileName = 'gd_pilot.cfg'
print '**************** USING' + expConfigFileName + '****************'

ft = .3048
inch = 0.0254
m = 1
eps = .01
nan = float('NaN')

# Create a globally accessible soundbank.
# To access within a member function, 
# import the global variable with 'global soundbank'

#vizact.onkeydown( 'm', viz.window.screenCapture, 'image.bmp' )


# Pulled from vrlabConfig.py
# expCfg = ConfigObj(expCfgName, configspec='expCfgSpec.ini', raise_errors = True, file_error = True)
# 
class soundBank():
	def __init__(self):
		 
		################################################################
		################################################################
		
		## Register sounds.  It makes sense to do it once per experiment.
		self.bounce =  '/Resources/bounce.wav'
		self.buzzer =  '/Resources/BUZZER.wav'
		self.bubblePop =  '/Resources/bubblePop3.wav'
		self.highDrip =  '/Resources/highdrip.wav'
		self.cowbell =  '/Resources/cowbell.wav'
		self.gong =  '/Resources/gong.wav'
		
		viz.playSound(self.bounce,viz.SOUND_PRELOAD)
		viz.playSound(self.buzzer,viz.SOUND_PRELOAD)
		viz.playSound(self.bubblePop,viz.SOUND_PRELOAD)
		viz.playSound(self.highDrip,viz.SOUND_PRELOAD)
		viz.playSound(self.cowbell,viz.SOUND_PRELOAD)
		viz.playSound(self.cowbell,viz.SOUND_PRELOAD)
		
soundBank = soundBank()

class Configuration():
	
	def __init__(self, expCfgName = ""):
		"""
		Opens and interprets both the system config (as defined by the <platform>.cfg file) and the experiment config
		(as defined by the file in expCfgName). Both configurations MUST conform the specs given in sysCfgSpec.ini and
		expCfgSpec.ini respectively. It also initializes the system as specified in the sysCfg.
		"""
		self.eyeTracker = []
		

		#self.bodyCam = None

		self.writables = list()
		if expCfgName:
			self.__createExpCfg(expCfgName)
		else:
			self.expCfg = None
			
		self.__createSysCfg()
		
		for pathName in self.sysCfg['set_path']:
			viz.res.addPath(pathName)
			
		self.vizconnect = vizconnect.go( 'vizConnect/' + self.sysCfg['vizconfigFileName'])
		self.__postVizConnectSetup()
		
	def __postVizConnectSetup(self):
		''' 
		This is where one can run any system-specific code that vizconnect can't handle
		'''
		dispDict = vizconnect.getRawDisplayDict()
		
		self.clientWindow = dispDict['exp_display']
		self.riftWindow = dispDict['rift_display']
		
	

		if( self.sysCfg['use_wiimote']):
			# Create wiimote holder
			self.wiimote = 0
			self.__connectWiiMote()

		if self.sysCfg['use_hmd'] and self.sysCfg['hmd']['type'] == 'DK2':
			self.__setupOculusMon()
		
		if self.sysCfg['use_eyetracking']:
			self.use_eyeTracking = True
			self.__connectSMIDK2()
		else:
			self.use_eyeTracking = False
	
			
		self.writer = None #Will get initialized later when the system starts
		self.writables = list()
		
		#viz.callback(viz.EXIT_EVENT, self.stopDVR)
#		vizact.ontimer2(5,1,self.stopDVR)
		
		if self.sysCfg['use_phasespace']:
			
			from mocapInterface import phasespaceInterface			
			self.mocap = phasespaceInterface(self.sysCfg);
			
			self.use_phasespace = True
		else:
			self.use_phasespace = False
			
		
		#viz.setMultiSample(self.sysCfg['antiAliasPasses'])
		#viz.MainWindow.clip(0.01 ,200)
		
		#viz.vsync(1)
		#self.__setWinPriority(5)
		viz.setOption("viz.glfinish", 1)
		viz.setOption("viz.dwm_composition", 0)
		
	def __createExpCfg(self, expCfgName):

		"""

		Parses and validates a config obj
		Variables read in are stored in configObj
		
		"""
		
		print "Loading experiment config file: " + expCfgName
		
		# This is where the parser is called.
		expCfg = ConfigObj(expCfgName, configspec='expCfgSpec.ini', raise_errors = True, file_error = True)

		validator = Validator()
		expCfgOK = expCfg.validate(validator)
		if expCfgOK == True:
			print "Experiment config file parsed correctly"
		else:
			print 'Experiment config file validation failed!'
			res = expCfg.validate(validator, preserve_errors=True)
			for entry in flatten_errors(expCfg, res):
			# each entry is a tuple
				section_list, key, error = entry
				if key is not None:
					section_list.append(key)
				else:
					section_list.append('[missing section]')
				section_string = ', '.join(section_list)
				if error == False:
					error = 'Missing value or section.'
				print section_string, ' = ', error
			sys.exit(1)
		if expCfg.has_key('_LOAD_'):
			for ld in expCfg['_LOAD_']['loadList']:
				print 'Loading: ' + ld + ' as ' + expCfg['_LOAD_'][ld]['cfgFile']
				curCfg = ConfigObj(expCfg['_LOAD_'][ld]['cfgFile'], configspec = expCfg['_LOAD_'][ld]['cfgSpec'], raise_errors = True, file_error = True)
				validator = Validator()
				expCfgOK = curCfg.validate(validator)
				if expCfgOK == True:
					print "Experiment config file parsed correctly"
				else:
					print 'Experiment config file validation failed!'
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
						print section_string, ' = ', error
					sys.exit(1)
				expCfg.merge(curCfg)
		
		self.expCfg = expCfg

	
	def __setWinPriority(self,pid=None,priority=5):
		
		""" Set The Priority of a Windows Process.  Priority is a value between 0-5 where
			2 is normal priority.  Default sets the priority of the current
			python process but can take any valid process ID. """
			
		import win32api,win32process,win32con
		
		priorityclasses = [win32process.IDLE_PRIORITY_CLASS,
						   win32process.BELOW_NORMAL_PRIORITY_CLASS,
						   win32process.NORMAL_PRIORITY_CLASS,
						   win32process.ABOVE_NORMAL_PRIORITY_CLASS,
						   win32process.HIGH_PRIORITY_CLASS,
						   win32process.REALTIME_PRIORITY_CLASS]
		if pid == None:
			pid = win32api.GetCurrentProcessId()
		
		handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
		win32process.SetPriorityClass(handle, priorityclasses[priority])
		
	def __createSysCfg(self):
		"""
		Set up the system config section (sysCfg)
		"""
		
		# Get machine name
		sysCfgName = platform.node()+".cfg"
		
		if not(os.path.isfile(sysCfgName)):
			sysCfgName = "defaultSys.cfg"
			
		print "Loading system config file: " + sysCfgName
		
		# Parse system config file
		sysCfg = ConfigObj(sysCfgName, configspec='sysCfgSpec.ini', raise_errors = True)
		
		validator = Validator()
		sysCfgOK = sysCfg.validate(validator)
		
		if sysCfgOK == True:
			print "System config file parsed correctly"
		else:
			print 'System config file validation failed!'
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
				print section_string, ' = ', error
			sys.exit(1)
		self.sysCfg = sysCfg
	
		
	def __setupOculusMon(self):
		"""
		Setup for the oculus rift dk2
		Relies upon a cluster enabling a single client on the local machine
		THe client enables a mirrored desktop view of what's displays inside the oculus DK2
		Note that this does some juggling of monitor numbers for you.
		"""
		
		#viz.window.setFullscreenMonitor(self.sysCfg['displays'])
		#hmd = oculus.Rift(renderMode=oculus.RENDER_CLIENT)

		displayList = self.sysCfg['displays'];
		
		if len(displayList) < 2:
			print 'Display list is <1.  Need two displays.'
		else:
			print 'Using display number ' + str(displayList[0]) + ' for oculus display.'
			print 'Using display number ' + str(displayList[1]) + ' for mirrored display.'
		
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
			while( riftMon == expMon ):
				expMon = count
				
			viz.window.setFullscreenMonitor(expMon)
			viz.window.setFullscreen(1)

	def __connectWiiMote(self):
		
		wii = viz.add('wiimote.dle')#Add wiimote extension
		
		# Replace old wiimote
		if( self.wiimote ):
			print 'Wiimote removed.'
			self.wiimote.remove()
			
		self.wiimote = wii.addWiimote()# Connect to first available wiimote
		
		vizact.onexit(self.wiimote.remove) # Make sure it is disconnected on quit
		
		self.wiimote.led = wii.LED_1 | wii.LED_4 #Turn on leds to show connection
	
	def __connectSMIDK2(self):
		
		if self.sysCfg['sim_trackerData']:
			self.eyeTracker = smi.iViewHMD(simulate=True)
		else:
			self.eyeTracker = smi.iViewHMD()
	
	def __record_data__(self, e):
		
		if self.use_DVR and self.writer != None:
			#print "Writing..."
			self.writer.write(self.writables)
		

class Experiment(viz.EventClass):
	
	"""
	Experiment manages the basic operation of the experiment.
	"""
	
	def __init__(self, expConfigFileName):
		
		# Event classes can register their own callback functions
		# This makes it possible to register callback functions (e.g. activated by a timer event)
		# within the class (that accept the implied self argument)
		# eg self.callbackFunction(arg1) would receive args (self,arg1)
		# If this were not an eventclass, the self arg would not be passed = badness.
		
		viz.EventClass.__init__(self)
		
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
		self.totalCalibrationFrames = 100
		
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
		
		self.blockNumber = 0;
		self.trialNumber = 0;
		self.inProgress = True;

		self.enableWritingToLog = False
		self.calibrationDoneSMI = False
		
		self.gazeVector = []
		self.eyeBallVector = []
				
		self.blocks_bl = []
		
		for bIdx in range(len(self.config.expCfg['experiment']['blockList'])):
			self.blocks_bl.append(block(self.config,bIdx, self.room));
		
		self.currentTrial = self.blocks_bl[self.blockNumber].trials_tr[self.trialNumber]
		
#		################################################################
#		################################################################
#		##  Misc. Design specific items here.
		
		# Setup launch trigger
		self.launchKeyIsCurrentlyDown = False
		
		self.minLaunchTriggerDuration = self.config.expCfg['experiment']['minLaunchTriggerDuration']
		
		if self.config.sysCfg['use_phasespace']:
			self.linkObjectsUsingMocap()
			
		##############################################################
		##############################################################
		## Callbacks and timers
		
		vizact.onupdate(viz.PRIORITY_PHYSICS,self._checkForCollisions)
		self.callback(viz.KEYDOWN_EVENT,  self.onKeyDown)
		self.callback(viz.KEYUP_EVENT, self.onKeyUp)
		self.callback( viz.TIMER_EVENT,self._timerCallback )
		
		self.perFrameTimerID = viz.getEventID('perFrameTimerID') # Generates a unique ID. 
		self.starttimer( self.perFrameTimerID, viz.FASTEST_EXPIRATION, viz.FOREVER)
		
		# maxFlightDurTimerID times out balls a fixed dur after launch
		self.maxFlightDurTimerID = viz.getEventID('maxFlightDurTimerID') 
		self.ballPresDurTimerID = viz.getEventID('ballPresDurTimerID') 
		self.ballBlankDurTimerID = viz.getEventID('ballBlankDurTimerID')
		
		############################################################
		#############################################################
		# Setup per-frame data output
		self.setupFileIO()
		
		with viz.cluster.MaskedContext(viz.MASTER):
			vizact.onupdate(viz.PRIORITY_LAST_UPDATE,self.addDataToLog)
		
		self.eventFlag = eventFlag()
		
		
	def _timerCallback(self,timerID):
		
		if( timerID == self.maxFlightDurTimerID ):

			print 'Removing ball!'
			self.currentTrial.removeBall()
			self.room.standingBox.visible( viz.TOGGLE )
			self.endTrial()
			
		elif( timerID == self.ballPresDurTimerID ):
			
			# make ball invisible
			if( self.currentTrial.blankDur != 0.0 ):
				self.currentTrial.ballObj.node3D.visible( False )
				self.starttimer(self.ballBlankDurTimerID,self.currentTrial.blankDur);
				#self.eventFlag.setStatus(8)
				self.eventFlag.setStatus('ballRenderOff')
				
		elif( timerID == self.ballBlankDurTimerID ):
			
			self.currentTrial.ballObj.node3D.visible( True )
			#self.eventFlag.setStatus(9)
			self.eventFlag.setStatus('ballRenderOn')
			
	def _checkForCollisions(self):
		
		thePhysEnv = self.room.physEnv;
		
		if( thePhysEnv.collisionDetected == False ): 
			# No collisions this time!
			return
		
		theFloor = self.room.floor
		theBackWall = self.room.wall_NegZ
		theBall = self.currentTrial.ballObj				
		
		if(self.room.paddle):
			thePaddle = self.room.paddle
		if(self.room.passingPlane):
			thePassingPlane = self.room.passingPlane
		
		for idx in range(len(thePhysEnv.collisionList_idx_physNodes)):
			
			physNode1 = thePhysEnv.collisionList_idx_physNodes[idx][0]
			physNode2 = thePhysEnv.collisionList_idx_physNodes[idx][1]
			
			# BALL / FLOOR
			
			if( theBall ):
				if( self.currentTrial.ballHasBouncedOnFloor == False and
					(physNode1 == theFloor.physNode and physNode2 == theBall.physNode or 
					physNode1 == theBall.physNode and physNode2 == theFloor.physNode )):
						
					#self.eventFlag.setStatus(3)
					self.eventFlag.setStatus('ballOnFloor')
					
					self.currentTrial.ballHasBouncedOnFloor = True 
					 
					# This is an example of how to get contact information
					bouncePos_XYZ,normal,depth,geom1,geom2 = thePhysEnv.contactObjects_idx[0].getContactGeomParams()
					print 'Bounce Point', bouncePos_XYZ
					
					self.currentTrial.ballOnPaddlePos_XYZ = bouncePos_XYZ
					
					#print 'Ball has hit the ground.'
					viz.playSound(soundBank.bounce)
					
					# Compare pre-bounce flight dur with predicted pre-bounce flight dur
					#actualPreBounceFlightDur =  float(viz.getFrameTime()) - self.currentTrial.launchTime
					#durationError = self.currentTrial.predictedPreBounceFlightDur - actualPreBounceFlightDur
					#self.currentTrial.flightDurationError = durationError 
					
					#print 'Predicted: ' + str(self.currentTrial.predictedPreBounceFlightDur)
					#print 'Actual   : ' + str(actualPreBounceFlightDur)
					
					#print 'Flight duration error: ' + str(durationError)
					
				# BALL / PADDLE
				if( self.currentTrial.ballHasHitPaddle == False and
					(physNode1 == thePaddle.physNode and physNode2 == theBall.physNode or 
					physNode1 == theBall.physNode and physNode2 == thePaddle.physNode )):
						
					#self.eventFlag.setStatus(4)
					self.eventFlag.setStatus('ballOnPaddle')
					self.currentTrial.ballHasHitPaddle = True
					
					viz.playSound(soundBank.cowbell)
					
					# self.ballObj.physNode.setStickUponContact( room.paddle.physNode.geom )
					if( theBall.physNode.queryStickyState(thePaddle.physNode) ):
					
						theBall.updateAction.remove() # Could also be acheived by turning of physics via the physnode
						
						theBall.node3D.setParent(thePaddle.node3D)
						collPoint_XYZ = theBall.physNode.collisionPosLocal_XYZ
						theBall.node3D.setPosition(collPoint_XYZ, viz.ABS_PARENT)
						
						
						print 'Collision Location ', collPoint_XYZ
						self.currentTrial.ballOnPaddlePosLoc_XYZ = collPoint_XYZ
						
						# If you don't set position in this way (on the next frame using vizact.onupdate),
						# then it doesn't seem to update correctly.  
						# My guess is that this is because the ball's position is updated later on this frame using
						# visObj.applyPhysToVis()

						vizact.onupdate(viz.PRIORITY_LINKS,theBall.node3D.setPosition,collPoint_XYZ[0],collPoint_XYZ[1],collPoint_XYZ[2], viz.ABS_PARENT)

#				# BALL / PassingPlane
#				if( type(self.room.passingPlane) is visEnv.visObj and 
#					self.currentTrial.ballHasHitPassingPlane == False 
#					and (physNode1 == thePassingPlane.physNode and physNode2 == theBall.physNode or 
#						 physNode1 == theBall.physNode and physNode2 == thePassingPlane.physNode )):
#						
#					self.eventFlag.setStatus(8)
#					self.currentTrial.ballHasHitPassingPlane = True
#					viz.playSound(soundBank.bubblePop)
#					
#					#self.currentTrial.myMarkersList.append(vizshape.addCircle(0.02))
#					#self.currentTrial.myMarkersList[-1].color([1,1,0])
#					#self.currentTrial.myMarkersList[-1].setPosition(theBall.node3D.getPosition())
#
#
#					# self.ballObj.physNode.setStickUponContact( room.paddle.physNode.geom )
#					if( theBall.physNode.queryStickyState(thePassingPlane.physNode) ):
#					
#						theBall.updateAction.remove()
#						theBall.node3D.setParent(thePassingPlane.node3D)
#						collPoint_XYZ = theBall.physNode.collisionPosLocal_XYZ
#						theBall.node3D.setPosition(collPoint_XYZ, viz.ABS_PARENT)
#						
#						self.currentTrial.ballOnPassingPlanePosLoc_XYZ = collPoint_XYZ
#						
#						# If you don't set position in this way (on the next frame using vizact.onupdate),
#						# then it doesn't seem to update correctly.  
#						# My guess is that this is because the ball's position is updated later on this frame using
#						# visObj.applyPhysToVis()
#						#print '===============> HI HOO', collPoint_XYZ
#						vizact.onupdate(viz.PRIORITY_LINKS,theBall.node3D.setPosition,collPoint_XYZ[0],collPoint_XYZ[1],collPoint_XYZ[2])

				if( physNode1 == theBackWall.physNode and physNode2 == theBall.physNode or 
					physNode1 == theBall.physNode and physNode2 == theBackWall.physNode):
					
					#self.eventFlag.setStatus(5)
					self.eventFlag.setStatus('ballOnBackWall')
					#print 'Ball has hit the back wall.'
					
					viz.playSound(soundBank.bounce)
	
	def setupFileIO(self):
		
		# set up a logger and add handlers
		self.logger = logging.getLogger()
		now = datetime.datetime.now()

		dateTimeStr = str(now.year) + '-' + str(now.month) + '-' + str(now.day) + '-' + str(now.hour) + '-' + str(now.minute)
		
		dataOutPutDir = self.config.sysCfg['writer']['outFileDir'] + '//' +str(dateTimeStr) + '//'
		
		if not os.path.exists(dataOutPutDir):
			os.makedirs(dataOutPutDir)
			
		self.fhandler = logging.FileHandler(filename= dataOutPutDir + 'exp_data-' + dateTimeStr + '.dict', mode='w')
		formatter = logging.Formatter('%(message)s')
		self.fhandler.setFormatter(formatter)
		self.logger.addHandler(self.fhandler)
		self.logger.setLevel(logging.DEBUG)
		
		from shutil import copyfile
		
		# Copy config files
		copyfile('.\\' + expConfigFileName, dataOutPutDir+expConfigFileName ) # exp config
		copyfile('.\\expCfgSpec.ini', dataOutPutDir + 'expCfgSpec.ini' )# exp config spec1
		
		copyfile('.\\'+os.environ['COMPUTERNAME'] + '.cfg', dataOutPutDir+os.environ['COMPUTERNAME'] + '.cfg')# system config 
		copyfile('.\\sysCfgSpec.ini', dataOutPutDir+ 'sysCfgSpec.ini') # system config spec
		
	def start(self):
		
		##This is called when the experiment should begin.
		self.setEnabled(True)
		
	def toggleEyeCalib(self):
		
		"""
		Toggles the calibration for eye tracking.
		Note, that for this to work, toggling 
		# self.config.camera must turn off your world model
		# This is setup in testRoom.init().
		
		# Example of what's needed in testRoom.init
		self.room = viz.addGroup()
		self.model = viz.add('pit.osgb',parent = self.room)
		"""
		
		if( self.config.sysCfg['use_eyetracking'] is False ):
			print 'Eyetracker not setup'
			return
			
		if not self.config.mocap:
			pass
		elif( self.hmdLinkedToView and self.viewAct.getEnabled() ):

			self.viewAct.setEnabled(viz.OFF)

		elif( self.hmdLinkedToView and self.viewAct.getEnabled() == False ):
			
			self.viewAct.setEnabled(viz.ON)
		
		viz.mouse.setOverride(viz.TOGGLE)

		self.config.eyeTrackingCal.toggleCalib()
		
		self.inCalibrateMode = not self.inCalibrateMode
		
		if self.inCalibrateMode:
			viz.clearcolor(.5, .5, .5)
			viz.MainView.setPosition(0,0,0)
			viz.MainView.setAxisAngle(0, 1, 0, 0)
			viz.MainView.velocity([0,0,0]);
			
		else:
			viz.clearcolor(0, 0, 0)
			
		if self.room:
			#self.room.visible(viz.disable)
			self.room.walls.visible(viz.TOGGLE)
			self.room.objects.visible(viz.TOGGLE)
		
		
		self.config.eyeTrackingCal.updateOffset('s')
		self.config.eyeTrackingCal.updateOffset('w')
			
	def createCamera(self):
		"""
		Head camera is generally initialized as part of the system calls. Additional changes should be added here.
		"""
		pass		

	def updateGazePoints(self):
		displayOffset = 0.15
		self.myDisplay.setPosition(viz.MainView.getPosition() - [0.0, 0.0, displayOffset])
		

	def callSMICalibration(self):
		self.calibrationDoneSMI = True
		eyeTracker = experimentObject.config.eyeTracker
		eyeTracker.calibrate()
		print 'calibrationDoneSMI ==> ', self.calibrationDoneSMI

	def callPerForMCalibration(self):
		print 'Static Calibration Method is Called'
		self.totalCalibrationFrames = 100
		calibTools.staticCalibrationMethod()
	
	def updateCalibrationPoint(self):
		calibTools.updateCalibrationPoint()
		
	def recordCalibrationData(self):
		print 'Data Recording Started for Calibration'
		calibTools.calibrationSphere.color(viz.YELLOW)
		self.enableWritingToLog = True
		self.calibrationFrameCounter = 0

	def onKeyDown(self, key):
		"""
		Interactive commands can be given via the keyboard. Some are provided here. You'll likely want to add more.
		"""
		
		
		if( self.config.use_phasespace == True ):
			mocapSys = self.config.mocap;
			hmdRigid = mocapSys.returnPointerToRigid('hmd')
			paddleRigid = mocapSys.returnPointerToRigid('paddle')
		else:
			mocapSys = []
			hmdRigid = []
			paddleRigid = []
		
		##########################################################
		##########################################################
		## Keys used in the default mode
		
		if  key == 'R':
			#riftOriTracker = vizconnect.getTracker('rift').getNode3d()
			pass

		if key == 'c' and self.config.eyeTracker:
			self.callSMICalibration()

		if key == 'q':
			self.updateCalibrationPoint()

		if key == 'k':
			self.recordCalibrationData()

		if key == 'e':
			self.callPerForMCalibration()

		if key == 'z':
			print 'Dynamic Calibration Method is Called'
			self.totalCalibrationFrames = 2000
			self.enableWritingToLog = True
			calibTools.dynamicCalibrationMethod()

			

		if ( self.inCalibrateMode is False ):
			
			if key == 'M':
				
				# Toggle the link between the HMD and Mainview
				if( self.hmdLinkedToView ):
					if( self.viewAct.getEnabled()):
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
				print 'save HMD Rigid Body'
				mocapSys.saveRigid('hmd')
			elif key == 'W':
				self.connectWiiMote()
			elif key == 'v':
				self.launchKeyDown()
				
			elif key == 'D':
				dvrWriter = self.config.writer;
				dvrWriter.toggleOnOff()
			
			elif key == 'r':
				
				vizconnect.getTracker('rift_tracker').resetHeading()
			
		##########################################################
		##########################################################
		## Eye-tracker calibration mode

	
	def onKeyUp(self,key):
				
		if( key == 'v'):
			self.launchKeyUp()

	def launchKeyDown(self):
		
		
		if( self.inProgress == True and   # Experiment ongoing
		 self.launchKeyIsCurrentlyDown == False and
		self.currentTrial.ballInRoom == False ): # There is not already a ball
					
			# Start timing trigger duration 
			# At end of trigger, launch the ball.
			self.launchKeyIsCurrentlyDown = True
			self.timeLaunchKeyWasPressed = viz.tick()
			self.room.standingBox.visible( viz.TOGGLE )
			
			self.currentTrial.placeLaunchPlane(self.currentTrial.launchPlaneSize)			
			self.currentTrial.placePassingPlane(self.currentTrial.passingPlaneSize)
			self.currentTrial.placeBall(self.room)
	
	def launchKeyUp(self):			
			
		if( self.launchKeyIsCurrentlyDown == True ):
			
			self.launchKeyIsCurrentlyDown = False
			triggerDuration = viz.tick() - self.timeLaunchKeyWasPressed
			ballReadyToLaunch = False
			
			if( self.currentTrial.ballInRoom == True and
				self.currentTrial.ballInInitialState == True and
				self.currentTrial.ballLaunched == False):
						
				# Ball is ready to launch
				
				if( triggerDuration <= self.minLaunchTriggerDuration ):
				
					# Trigger not held long enough for a launch

					viz.playSound(soundBank.cowbell)
					self.room.standingBox.visible( viz.TOGGLE )
					self.currentTrial.removeBall()
					#print 'Launch aborted'
			
				if( triggerDuration >= self.minLaunchTriggerDuration ):
					
					#self.eventFlag.setStatus(1)
					self.eventFlag.setStatus('trialStart')
					self.inProgress = True
					#print 'Ball launched'
					self.enableWritingToLog = True
					print 'Start Trial {', self.enableWritingToLog,'}'

					self.currentTrial.launchBall();
					
	
					self.starttimer(self.maxFlightDurTimerID,self.currentTrial.ballFlightMaxDur);
					self.starttimer(self.ballPresDurTimerID,self.currentTrial.preBlankDur);
	
			else:
				
				return
	
	def addDataToLog(self):
		"""
		Returns a string describing the current state of the experiment, useful for recording.
		"""
		
		# Legend:
		# ** for 1 var
		# () for 2 vars
		# [] for 3 vars
		# <> for 4 vars
		# @@ for 16 vars (view and projection matrices)
		
		#### Eventflag
		# 1 ball launched
		# 3 ball has hit floor 
		# 4 ball has hit paddle
		# 5 ball has hit back wall
		# 6 ball has timed out
		
		NaN = float('NaN')

		# Only write data is the experiment is ongoing
		if( self.enableWritingToLog is False or self.inProgress is False):
			return
	
		self.calibrationFrameCounter = self.calibrationFrameCounter + 1
		
		if ( calibTools.calibrationInProgress == True and self.calibrationFrameCounter > self.totalCalibrationFrames  ):
			self.enableWritingToLog = False
			print 'Calibration Frames Recorded:', self.calibrationFrameCounter 
			calibTools.calibrationSphere.color(viz.PURPLE)
			self.calibrationFrameCounter = 0
			return
			
		################################################
		## Gather misc data 
		
		frameNum = viz.getFrameNumber()
		
		viewPos_XYZ = viz.MainView.getPosition(viz.MASTER)
		
		if( calibTools.calibrationSphere ):
			calibrationPoint_XYZ = calibTools.calibrationSphere.getPosition()
		else:
			calibrationPoint_XYZ = [NaN,NaN,NaN]

		currentSample =  self.config.eyeTracker.getLastSample()

		################################################
		################################################
		#### Gather racquet data
		
		paddlePos_XYZ = []
		paddleQuat_XYZW = []
		#paddleAngVel_XYZ = []
		
		if( self.room.paddle ):
			
			paddlePos_XYZ = self.room.paddle.node3D.getPosition()
			paddleMat = self.room.paddle.node3D.getMatrix().data
			paddleQuat_XYZW = self.room.paddle.node3D.getMatrix().getQuat()
			
		else:
			paddlePos
			_XYZ = [NaN,NaN,NaN]
			paddleQuat_XYZW = [NaN,NaN,NaN,NaN]
			
		###############################################
		################################################
		#### Gather ball data

		theBall = self.currentTrial.ballObj;
		
		#if(theBall is not -1):
		if(theBall):
			
			ballPos_XYZ = theBall.node3D.getPosition(viz.ABS_GLOBAL)
			
			ballVel_XYZ = theBall.getVelocity()
			ballVisible = self.currentTrial.ballObj.node3D.getVisible()
			
		else:
			
			ballPos_XYZ = [NaN,NaN,NaN]
			ballVel_XYZ = [NaN,NaN,NaN]
			ballVisible = NaN
			
		# SMI Data
		if( currentSample ):
			
			smiServerTime = self.config.eyeTracker.getServerTime()
			
			cycEyeOnScreen_XY = [currentSample.por.x, currentSample.por.y]
			cycEyeInHead_XYZ = [currentSample.gazeDirection.x, currentSample.gazeDirection.y, currentSample.gazeDirection.z]
			cycEyeBasePoint_XYZ = [currentSample.gazeBasePoint.x, currentSample.gazeBasePoint.y, currentSample.gazeBasePoint.z]
			
			rightEyeOnScreen_XY = [currentSample.rightEye.por.x, currentSample.rightEye.por.y]
			rightEyeInHead_XYZ = [currentSample.rightEye.gazeDirection.x, currentSample.rightEye.gazeDirection.y, currentSample.rightEye.gazeDirection.z]
			rightEyeBasePoint_XYZ =[currentSample.rightEye.gazeBasePoint.x, currentSample.rightEye.gazeBasePoint.y, currentSample.rightEye.gazeBasePoint.z] # H or W?
			rightEyeScreenDistance = currentSample.rightEye.eyeScreenDistance
			rightEyeLensDistance  = currentSample.rightEye.eyeLensDistance
			rightPupilRadius = currentSample.rightEye.pupilRadius
			rightPupilPos_XYZ = [currentSample.rightEye.pupilPosition.x, currentSample.rightEye.pupilPosition.y, currentSample.rightEye.pupilPosition.z] # Pixel values
			
			leftEyeOnScreen_XY = [currentSample.leftEye.por_x, currentSample.leftEye.por_y]
			leftEyeInHead_XYZ = [currentSample.leftEye.gazeDirection.x, currentSample.leftEye.gazeDirection.y, currentSample.leftEye.gazeDirection.z]
			leftEyeBasePoint_XYZ=[currentSample.leftEye.gazeBasePoint.x, currentSample.leftEye.gazeBasePoint.y, currentSample.leftEye.gazeBasePoint.z] # H or W?
			leftEyeScreenDistance = currentSample.leftEye.eyeScreenDistance
			leftEyeLensDistance  = currentSample.leftEye.eyeLensDistance
			leftPupilRadius = currentSample.leftEye.pupilRadius
			leftPupilPos_XYZ = [currentSample.leftEye.pupilPosition.x, currentSample.leftEye.pupilPosition.y, currentSample.leftEye.pupilPosition.z] # Pixel values
			
			eyeTimeStamp = currentSample.timestamp
			IOD = currentSample.iod
			IPD = currentSample.ipd
			
		else:
		
			smiServerTime = [NaN]
			
			cycEyeOnScreen_XY = [NaN,NaN]
			cycEyeInHead_XYZ = [NaN,NaN,NaN]
			cycEyeBasePoint_XYZ= [NaN,NaN,NaN]
			
			rightEyeOnScreen_XY = [NaN,NaN]
			rightEyeInHead_XYZ = [NaN,NaN,NaN]
			rightEyeBasePoint_XYZ = [NaN,NaN,NaN]
			rightEyeScreenDistance = NaN
			rightEyeLensDistance = NaN
			rightPupilRadius = NaN
			rightPupilPos_XYZ = [NaN,NaN,NaN]
			
			leftEyeOnScreen_XY = [NaN,NaN]
			leftEyeInHead_XYZ = [NaN,NaN,NaN]
			leftEyeBasePoint_XYZ= [NaN,NaN,NaN]
			leftEyeScreenDistance = NaN
			leftEyeLensDistance = NaN
			leftPupilRadius = NaN
			leftPupilPos_XYZ = [NaN,NaN,NaN]
			
			eyeTimeStamp = NaN
			IOD = NaN
			IPD = NaN
			
		##### Eye nodes
		
		if( currentSample ):
			
			cycEyeNodeInWorld_XYZ = viz.MainView.getPosition()
			rightEyeNodeInWorld_XYZ = rightEyeNode.getPosition(viz.ABS_GLOBAL)
			leftEyeNodeInWorld_XYZ = leftEyeNode.getPosition(viz.ABS_GLOBAL)
			
			rightEyeNodeInHead_XYZ = rightEyeNode.getPosition(viz.ABS_PARENT)
			leftEyeNodeInHead_XYZ = leftEyeNode.getPosition(viz.ABS_PARENT)
			
			cycMat_4x4 = viz.MainView.getMatrix(viz.ABS_GLOBAL).data
			rightEyeMat_4x4 = rightEyeNode.getMatrix(viz.ABS_GLOBAL).data
			leftEyeMat_4x4 = leftEyeNode.getMatrix(viz.ABS_GLOBAL).data
			
			cycInverseMat_4x4 = viz.MainView.getMatrix(viz.ABS_GLOBAL).inverse().data
			rightEyeInverseMat_4x4 = rightEyeNode.getMatrix(viz.ABS_GLOBAL).inverse().data
			leftEyeInverseMat_4x4 = leftEyeNode.getMatrix(viz.ABS_GLOBAL).inverse().data
			
			cycGazeNodeInWorld_XYZ = cyclopEyeSphere.node3D.getPosition(viz.ABS_GLOBAL)
			rightGazeNodeInWorld_XYZ = right_sphere.node3D.getPosition(viz.ABS_GLOBAL)
			leftGazeNodeInWorld_XYZ = left_sphere.node3D.getPosition(viz.ABS_GLOBAL)
			
			cycGazeNodeInHead_XYZ = viz.MainView.getPosition(viz.ABS_PARENT)
			rightGazeNodeInHead_XYZ = right_sphere.node3D.getPosition(viz.ABS_PARENT)
			leftGazeNodeInHead_XYZ = left_sphere.node3D.getPosition(viz.ABS_PARENT)

		else:
							
			cycEyeNodeInWorld_XYZ = [NaN,NaN,NaN]
			rightEyeNodeInWorld_XYZ = [NaN,NaN,NaN]
			leftEyeNodeInWorld_XYZ = [NaN,NaN,NaN]
			
			rightEyeNodeInHead_XYZ = [NaN,NaN,NaN]
			leftEyeNodeInHead_XYZ = [NaN,NaN,NaN]
			
			cycMat_4x4 = [NaN] * 16
			rightEyeMat_4x4 = [NaN] * 16
			leftEyeMat_4x4 = [NaN] * 16
			
			cycInverseMat_4x4 = [NaN] * 16
			rightEyeInverseMat_4x4 = [NaN] * 16
			leftEyeInverseMat_4x4 = [NaN] * 16
			
			cycGazeNodeInWorld_XYZ = [NaN,NaN,NaN]
			rightGazeNodeInWorld_XYZ = [NaN,NaN,NaN]
			leftGazeNodeInWorld_XYZ = [NaN,NaN,NaN]
			
			cycGazeNodeInHead_XYZ = [NaN,NaN,NaN]
			rightGazeNodeInHead_XYZ = [NaN,NaN,NaN]
			leftGazeNodeInHead_XYZ = [NaN,NaN,NaN]
			
		
		if (calibTools.calibrationInProgress == True):
			tempVar = calibTools.calibrationBlockCounter + calibTools.calibrationCounter
		else:
			tempVar = self.trialNumber
		dataDict = dict( 
			
			frameTime = viz.getFrameTime(),
			smiNsSinceStart = smiServerTime,
			trialNumber = tempVar,
			blockNumber = self.blockNumber,
			eventFlag = self.eventFlag.status,
			trialType = self.currentTrial.trialType,
			
			# mainView
			viewPos_XYZ = viewPos_XYZ,
			viewMat_4x4 = viz.MainView.getMatrix().data,
			viewQuat_XYZW = viz.MainView.getQuat(),

			# Calibration
			inCalibrationQ = calibTools.calibrationInProgress,
			isCalibratedSMIQ = self.calibrationDoneSMI,
			calibrationCounter = calibTools.calibrationCounter,
			calibrationPos_XYZ = [ calibrationPoint_XYZ[0], calibrationPoint_XYZ[1], calibrationPoint_XYZ[2] ],
			
			# Paddle
			paddlePos_XYZ=[paddlePos_XYZ[0],paddlePos_XYZ[1],paddlePos_XYZ[2]],
			paddleQuat_XYZW =[paddleQuat_XYZW[0],paddleQuat_XYZW[1],paddleQuat_XYZW[2],paddleQuat_XYZW[3]],
			paddleMat_4x4 = paddleMat,
			
			# Ball
			ballPos_XYZ = [ballPos_XYZ [0],ballPos_XYZ[1],ballPos_XYZ [2]],
			ballVel_XYZ = [ballVel_XYZ[0],ballVel_XYZ[1],ballVel_XYZ[2]],
			isBallVisibleQ = ballVisible,
			ballInitialPos_XYZ = [self.currentTrial.ballInitialPos_XYZ[0],self.currentTrial.ballInitialPos_XYZ[1],self.currentTrial.ballInitialPos_XYZ[2]],
			ballFinalPos_XYZ = [self.currentTrial.ballFinalPos_XYZ[0],self.currentTrial.ballFinalPos_XYZ[1],self.currentTrial.ballFinalPos_XYZ[2]],
			ballInitialVel_XYZ = [self.currentTrial.initialVelocity_XYZ[0],self.currentTrial.initialVelocity_XYZ[1],self.currentTrial.initialVelocity_XYZ[2]],
			ballTTC = self.currentTrial.timeToContact,
			#ballLaunch_AE = [self.currentTrial.beta,self.currentTrial.theta],
			
			# Trajectory
			preBlankDur = self.currentTrial.preBlankDur,
			blankDur = self.currentTrial.blankDur,
			postBlankDur = self.currentTrial.postBlankDur,
			
			# Eye geometry
			eyeTimeStamp = eyeTimeStamp,
			IOD = IOD,
			IPD = IPD,
			
			# Cyclopean gaze
			cycEyeOnScreen_XY=cycEyeOnScreen_XY,
			cycEyeInHead_XYZ = cycEyeInHead_XYZ,
			cycEyeBasePoint_XYZ = cycEyeBasePoint_XYZ,
			
			cycEyeNodeInWorld_XYZ = cycEyeNodeInWorld_XYZ,
			cycMat_4x4 = cycMat_4x4,
			cycInverseMat_4x4 = cycInverseMat_4x4,
			cycGazeNodeInWorld_XYZ = cycGazeNodeInWorld_XYZ,
			cycGazeNodeInHead_XYZ = cycGazeNodeInHead_XYZ,
			
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
			rightGazeNodeInHead_XYZ = rightGazeNodeInHead_XYZ,
			
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
			leftGazeNodeInHead_XYZ = leftGazeNodeInHead_XYZ,
					
			)
		
		logging.info(dict(dataDict))
		return
		
	def registerWiimoteActions(self):
				
		wii = viz.add('wiimote.dle')#Add wiimote extension
		
		vizact.onsensordown(self.config.wiimote,wii.BUTTON_B,self.launchKeyDown) 
		vizact.onsensorup(self.config.wiimote,wii.BUTTON_B,self.launchKeyUp)
		vizact.onsensordown(self.config.wiimote,wii.BUTTON_DOWN,self.callSMICalibration)
		vizact.onsensordown(self.config.wiimote,wii.BUTTON_A,self.callPerForMCalibration)
		vizact.onsensordown(self.config.wiimote,wii.BUTTON_1,self.updateCalibrationPoint)
		vizact.onsensordown(self.config.wiimote,wii.BUTTON_2,self.recordCalibrationData)
		vizact.onsensordown(self.config.wiimote,wii.BUTTON_PLUS,self.config.eyeTracker.acceptCalibrationPoint)
		

		
		if( self.config.use_phasespace == True ):
			
			mocapSys = self.config.mocap;
		
			#vizact.onsensorup(self.config.wiimote,wii.BUTTON_DOWN,mocapSyc.resetRigid,'hmd') 
			#vizact.onsensorup(self.config.wiimote,wii.BUTTON_UP,mocapSys.saveRigid,'hmd') 
			
			#vizact.onsensorup(self.config.wiimote,wii.BUTTON_LEFT,mocapSys.resetRigid,'paddle') 
			#vizact.onsensorup(self.config.wiimote,wii.BUTTON_RIGHT,mocapSys.saveRigid,'paddle') 
			
			def resetHelmetOrientation():
				
				mocapSys = self.config.mocap;mocapSys.resetRigid('hmd')
				
				# Get diff between current heading and world X
				rt_YPR = vizconnect.getTracker('rift_tracker').getLink().getEuler()
				oriLink = vizconnect.getTracker('rift_tracker').getLink()
				oriLink.reset(viz.RESET_OPERATORS)
				#oriLink.preEuler([-rt_YPR[0], -rt_YPR[1], 0], target=viz.LINK_ORI_OP, priority=-20)
				#oriLink.preEuler([-rt_YPR[0], -rt_YPR[1], -rt_YPR[2]], target=viz.LINK_ORI_OP, priority=-20)
				
			# HACKED by KAMRAN	
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
		
		print 'End of Trial & Block ==> TxT file Saved & Closed'
		print 'end experiment'
		self.inProgress = False
		
		
	def checkDVRStatus(self):
	
		dvrWriter = self.config.writer;
		
		if( dvrWriter.isPaused == 1 ):
			print '************************************ DVR IS PAUSED ************************************'

	
	def linkObjectsUsingMocap(self):
		
		mocap = self.config.mocap
		mocap.start_thread()
		
		self.setupPaddle()
		
		trackerDict = vizconnect.getTrackerDict()
		
		if( 'rift_tracker' in trackerDict.keys() ):
			
			mocap = self.config.mocap
			self.viewAct = vizact.onupdate(viz.PRIORITY_LINKS, self.updateHeadTracker)
			
		else:
			print '*** Experiment:linkObjectsUsingMocap: Rift not enabled as a tracker'
			return
		
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
		self.headTracker.setPosition( headRigidTracker.get_position() )	
	
		
	def setupPaddle(self):

		mocap = self.config.mocap
		
		# Performs several functions
		# Creates either a fake paddle, a visual paddle, or a vis/phy/mocap paddle
		
		# FOr debugging. Creates a fake paddle in teh center of the room
		if( self.config.expCfg['experiment']['useFakePaddle'] ):
				
#				if(any("paddle" in idx for idx in self.room.visObjNames_idx)):
#					print 'removed paddle'
#					self.room.paddle.remove()
					
				# Put a fake stationary paddle in the room
				paddleSize = [4, 4]
				self.room.paddle = visEnv.visObj(self.room,'cylinder_Z',paddleSize)
				self.room.paddle.enablePhysNode()
				self.room.paddle.node3D.setPosition([0,1.6,-1])
				self.room.paddle.node3D.color([0,1,0])
				
				#self.room.paddle.physNode

				return
			
		# If there is a visObj paddle and a paddle rigid, link em up!
		if any("paddle" in idx for idx in self.room.visObjNames_idx): 
			paddleRigid  = mocap.get_rigidTracker('paddle')
			if(paddleRigid ):
				
				print 'Setup paddle'
				paddle = self.room.paddle
				
				self.room.paddle.node3D.alpha(0.5)
				
				paddleRigidTracker = mocap.get_rigidTracker('paddle')	
				paddleRigidTracker.link_pose(paddle.node3D,'preEuler([90,0,0])')
				
				paddle.enablePhysNode()
				paddle.physNode.isLinked = 1
				
				paddleToPhysLink = viz.link( paddle.node3D, paddle.physNode.node3D)
				
				def printPaddlePos():
					#print 'VIS ' + str(paddle.node3D.getPosition())
					print 'node ' + str(paddle.physNode.node3D.getPosition())
					print 'geom ' + str(paddle.physNode.geom.getPosition())
					print 'body' + str(paddle.physNode.body.getPosition())
					
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
		
		self.enableWritingToLog = False
		print 'End Trial{', self.enableWritingToLog,'}'

		endOfTrialList = len(self.blocks_bl[self.blockNumber].trials_tr)
		
		if( self.trialNumber < endOfTrialList ):
			
			recalAfterTrial_idx = self.blocks_bl[self.blockNumber].recalAfterTrial_idx
			
			eyeTracker = experimentObject.config.eyeTracker
			if( recalAfterTrial_idx.count(self.trialNumber ) > 0):
				vizact.ontimer2(0,0,eyeTracker.calibrate(type = smi.CALIBRATION_9_POINT ))
				print 'Static Calibration Method is Called after %d trials' %(recalAfterTrial_idx.count(self.trialNumber ))
				self.totalCalibrationFrames = 100
				calibTools.staticCalibrationMethod()


			# Increment trial 
			self.trialNumber += 1
			self.killtimer(self.maxFlightDurTimerID)
			self.killtimer(self.ballPresDurTimerID)
			self.killtimer(self.ballBlankDurTimerID)
			
			#self.eventFlag.setStatus(6)
			self.eventFlag.setStatus('trialEnd')
			
		if( self.trialNumber == endOfTrialList ):
			
			# Increment block
			
			# arg2 of 1 allows for overwriting eventFlag 6 (new trial)
			#self.eventFlag.setStatus(7,True) 
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
				
			print 'Starting block: ' + str(self.blockNumber) + ' Trial: ' + str(self.trialNumber)
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
		currentSample = self.config.eyeTracker.getLastSample()
		if (currentSample):
			textObject.message('Tr# = %d \n B# = %d\n FT = %2.2f\n ET = %2.2f'%(self.trialNumber, self.blockNumber, viz.getFrameTime(), currentSample.timestamp))
		else:
			textObject.message('Tr# = %d \n B# = %d\n FT = %2.2f\n ET = Nan'%(self.trialNumber, self.blockNumber, viz.getFrameTime()))
		return
				
		
#	def placeTarget(self):
#		target = vizshape.addCylinder(0.2,0.5,axis=3,color=viz.GREEN)
#		target = 
#		pass
	
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
			print 'Did not reset! Status already set to ' + str(self.status)
		else:
			self.status = False; # 0 Means nothing is happening
			
		
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
			trialObj = trial(config,self.trialTypeList_tr[trialNumber], self.room)
				
			##Add the body to the list
			self.trials_tr.append(trialObj)

			## Create a generator this will loop through the balls
			#nextBall = viz.cycle(balls); 
		
class trial(viz.EventClass):
	def __init__(self,config=None,trialType='t1', room = None):
		
		#viz.EventClass.__init__(self)
		
		self.trialType = trialType

		self.room = room
		## State flags
		self.ballInRoom = False; # Is ball in room?
		self.ballInInitialState = False; # Is ball ready for launch?
		self.ballLaunched = False; # Has a ball been launched?  Remains true after ball disappears.
		self.ballHasBouncedOnFloor = False;
		self.ballHasHitPaddle = False;
		self.ballHasHitPassingPlane = False
		
		## Trial event data
		self.ballOnPaddlePos_XYZ = []
		self.ballOnPaddlePosLoc_XYZ = []
		self.ballOnPassingPlanePosLoc_XYZ = []
		
		self.myMarkersList = []
		## Timer objects
		self.timeSinceLaunch = [];
		
		self.ballObj = False;
		
		### Below this is all the code used to generate ball trajectories
		self.ballFlightMaxDur = float(config.expCfg['experiment']['ballFlightMaxDur'])
		
		#  Set ball color.
		try:
			self.ballColor_RGB = map(float,config.expCfg['trialTypes'][self.trialType]['ballColor_RGB'])
		except:
			print 'Using def color'
			self.ballColor_RGB = map(float,config.expCfg['trialTypes']['default']['ballColor_RGB'])
		
		# The rest of variables are set below, by drawing values from distributions
#		
		self.ballDiameter_distType = []
		self.ballDiameter_distParams = []
		self.ballDiameter = []
		
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
		
		self.distanceInDepth = self.launchPlanePosition[2] - self.passingPlanePosition[2]

		self.xMinimumValue = []
		self.xMaximumValue = []
		self.timeToContact = []
		self.presentationDuration = []
		self.blankDur = []
		self.postBlankDuration = []
		self.beta = []
		self.theta = []
		self.initialVelocity_XYZ = []
	
		self.preBlankDur = float(config.expCfg['trialTypes'][self.trialType]['preBlankDur'])
		self.postBlankDur = float(config.expCfg['trialTypes'][self.trialType]['postBlankDur'])
		self.blankDur = float(config.expCfg['trialTypes']['default']['blankDur'])
		
		self.timeToContact = self.preBlankDur + self.blankDur + self.postBlankDur
		
		self.ballInitialPos_XYZ = [0,0,0]
		self.initialVelocity_XYZ = [0,0,0]
		self.ballSpeed = 0.0
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
					print 'Error in main.trial.init.drawNumberFromDist()'
					print 'Variable name is: ' + varName
					
				try:
					exec( 'self.' + varName + '_distType = distType' )
					exec( 'self.' + varName + '_distParams = distParams' )
					exec( 'self.' + varName + '_distType = distType' )
					# Draw value from a distribution
					exec( 'self.' + varName + ' = drawNumberFromDist( distType , distParams);' )
				except:
					print 'Error in main.trial.init'
					print 'Variable name is: ' + varName
				
	
	
	def calculatePhysicalParams(self):
			
		# X velocity
		self.lateralDistance = math.fabs(self.ballFinalPos_XYZ[0] - self.ballInitialPos_XYZ[0])
		self.initialVelocity_XYZ[0] = self.lateralDistance/self.timeToContact
		
		# Z velocity
		self.distanceInDepth = math.fabs(self.ballFinalPos_XYZ[2] - self.ballInitialPos_XYZ[2])
		self.initialVelocity_XYZ[2] = -self.distanceInDepth/self.timeToContact
			
		#self.horizontalVelocity = math.sqrt(np.power(self.initialVelocity_XYZ[0],2) + np.power(self.initialVelocity_XYZ[2],2))
		#self.ballSpeed = self.gravity * self.timeToContact/(2 * math.fabs(math.sin(self.theta)))
		
		# Vertical component of velocity
		self.verticalDistance = self.ballFinalPos_XYZ[1] - self.ballInitialPos_XYZ[1]
		self.initialVelocity_XYZ[1] = ((-0.5 * -self.gravity * self.timeToContact * self.timeToContact) + self.verticalDistance ) / self.timeToContact
		
		self.totalDistance = math.sqrt(np.power(self.lateralDistance, 2) + np.power(self.distanceInDepth, 2) + np.power(self.verticalDistance, 2))
		self.beta = math.atan((self.distanceInDepth/self.lateralDistance))*(180.0/np.pi)
		self.theta = (180.0/np.pi)*math.atan((np.power(self.timeToContact,2) * self.gravity)/(2*self.totalDistance))
		
		#print 'V_xyz=[',self.initialVelocity_XYZ,'] theta=',self.theta,' beta=', self.beta 
		#print 'X=', self.lateralDistance, ' R=', self.totalDistance, ' g=', self.gravity, ' Vxz=', self.horizontalVelocity, ' D=', self.distanceInDepth

	def removeBall(self):
		
		print 'Removing ball'
		
		self.ballObj.remove()
		self.ballObj = False
		
		self.ballInRoom = False
		self.ballInInitialState = False
		self.ballLaunched = False
		
		print 'Cleaned up ball'

	def _setValueOrUseDefault(self,config,paramPrefix):
		
		try:
			#print paramPrefix
			# Try to values from the subsection [[trialType]]
			distType = config.expCfg['trialTypes'][self.trialType][paramPrefix + '_distType']
			distParams = config.expCfg['trialTypes'][self.trialType][paramPrefix +'_distParams']
			
		except:
			# print 'Using default: **' + paramPrefix + '**'
			# Try to values from the subsection [['default']]
			distType = config.expCfg['trialTypes']['default'][paramPrefix + '_distType'];
			distParams = config.expCfg['trialTypes']['default'][paramPrefix + '_distParams'];
		
		
		value = drawNumberFromDist(distType,distParams)
	
		
		return distType,distParams,value


	def placeLaunchPlane(self, planeSize):

		#adds a transparent plane that the ball is being launched from it
		self.room.launchPlane = vizshape.addPlane(size = planeSize , axis=-vizshape.AXIS_Z, cullFace = False)
		#shifts the wall to match the edge of the floor
		self.room.launchPlane.setPosition(self.launchPlanePosition)#[-self.launchPlaneSize[0]/2, 1.5, 24.0]
		#makes the wall appear white
		self.room.launchPlane.color(viz.CYAN)
		self.room.launchPlane.alpha(0.2)
		#self.room.launchPlane.collideBox()
		#self.room.launchPlane.disable(viz.DYNAMICS)
		self.room.launchPlane.visible(False)
		print 'Launch Plane Created!'

	def placePassingPlane(self, planeSize):
		
		#adds a transparent plane that the ball ends up in this plane
		self.room.passingPlane = visEnv.visObj(self.room,'box',size = self.passingPlaneSize)#[0.02, planeSize[0], planeSize[0]]
		
		#self.room.passingPlane.enablePhysNode()
		#self.room.passingPlane.linkPhysToVis()
		
		self.room.passingPlane.node3D.setPosition(self.passingPlanePosition)#[0, 1.5, 1.0]
		
		#makes the wall appear white
		self.room.passingPlane.node3D.color(viz.PURPLE)
		self.room.passingPlane.node3D.alpha(0.3)
		self.room.passingPlane.node3D.visible(False)
		
		print 'Passing Plane Created!'
			
	def placeBall(self,room):
	
		
		#=========================================================================
		#================== Changed for New Ball Catching Experiment =============
		#=========================================================================
		
		#########################################################
		################### STARTING POSITION ###################
		
		# Put ball in center of launch plane		
		self.ballInitialPos_XYZ = self.room.launchPlane.getPosition()
		
		launchPlane_XYZ = self.room.launchPlane.getPosition()
		
		### X VALUE
		xMinimumValue = launchPlane_XYZ[0]-self.launchPlaneSize[0]/2.0
		xMaximumValue = launchPlane_XYZ[0]+self.launchPlaneSize[0]/2.0
		self.ballInitialPos_XYZ[0] = xMinimumValue + np.random.random()*(xMaximumValue-xMinimumValue)
		
		### Y VALUE
		yMinimumValue = launchPlane_XYZ[1]-self.launchPlaneSize[1]/2.0
		yMaximumValue = launchPlane_XYZ[1]+self.launchPlaneSize[1]/2.0
		self.ballInitialPos_XYZ[1] = yMinimumValue + np.random.random()*(yMaximumValue-yMinimumValue)
		
		# Move ball relative to center of launch plane
		print 'Initial max/min=[', xMinimumValue, xMaximumValue,']'
		
		self.ballObj = visEnv.visObj(room,'sphere',self.ballDiameter/2,self.ballInitialPos_XYZ,self.ballColor_RGB)
		
		#########################################################
		################### FINAL POSITION ###################

		self.ballFinalPos_XYZ = self.room.passingPlane.node3D.getPosition()
		self.passingPlane_XYZ = self.room.passingPlane.node3D.getPosition()
		
		### X VALUE
		xMinimumValue = self.passingPlane_XYZ[0] - self.passingPlaneSize[0]/2.0
		xMaximumValue = self.passingPlane_XYZ[0] + self.passingPlaneSize[0]/2.0
		self.ballFinalPos_XYZ[0] = xMinimumValue + np.random.random()*(xMaximumValue-xMinimumValue)
				
		### Y VALUE
		yMinimumValue = self.passingPlane_XYZ[1] - self.passingPlaneSize[1]/2.0
		yMaximumValue = self.passingPlane_XYZ[1] + self.passingPlaneSize[1]/2.0
		self.ballFinalPos_XYZ[1] = yMinimumValue + np.random.random()*(yMaximumValue-yMinimumValue)
		
		#########################################################
		################### Initial Velocities ##################
		
		self.calculatePhysicalParams()
		print 'PlaceBall ==> Vx=', self.initialVelocity_XYZ[0], ' TTC=', self.timeToContact
		print 'PD = ', self.presentationDuration, ' BD = ', self.blankDur, ' PBD = ', self.postBlankDuration
		
		# Setup physics and collision
		
		self.ballObj.enablePhysNode()
		self.ballObj.linkToPhysNode()
		self.ballObj.physNode.setBounciness(self.ballElasticity)
		self.ballObj.physNode.setStickUponContact( room.paddle.physNode.geom )
					
		self.ballObj.projectShadows(self.ballObj.parentRoom.floor.node3D) # Costly, in terms of computation
		
		# Setup state flags 
		
		self.ballInRoom = True
		self.ballInInitialState = True
		self.ballLaunched = False 
		self.ballPlacedOnThisFrame = True

	def launchBall(self):
		
		if( self.ballObj == False ):
			print 'No ball present.'
			return

		self.ballObj.physNode.enableMovement()
		self.ballObj.setVelocity(self.initialVelocity_XYZ)
		self.myMarkersList
		self.ballInRoom = True
		self.ballInInitialState = False
		self.ballLaunched = True
		
		self.launchTime = viz.getFrameTime()
			
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


#experimentObject.room.lightSource.disable()
#vizfx.addDirectionalLight(euler=(0,45,0))

####

from gazeTools import gazeSphere
from gazeTools import gazeVector

eyeTracker = experimentObject.config.eyeTracker
headTracker = vizconnect.getRawTrackerDict()['head_tracker']
#headTracker.setPosition(0,1,0)

dispDict = vizconnect.getRawDisplayDict()
clientWindowID = dispDict['exp_display']

cyclopEyeSphere = gazeSphere(eyeTracker,viz.BOTH_EYE,headTracker,[clientWindowID],viz.GREEN)
#both_sphere = gazeSphere(eyeTracker,viz.BOTH_EYE,headTracker,sphereColor=viz.GREEN)
cyclopEyeSphere.toggleUpdate()

cyclopEyeNode = vizshape.addSphere(0.015, color = viz.GREEN)
cyclopEyeNode.setParent(headTracker)
cyclopEyeNode.alpha(0.01)

calibTools = calibrationTools(cyclopEyeNode, clientWindowID, cyclopEyeSphere, experimentObject.config, experimentObject.room) # TODO: Instead of passing both Eye node and sphere one should be enough (KAMRAN)
calibTools.create3DCalibrationPositions(calibTools.calibrationPositionRange_X, calibTools.calibrationPositionRange_Y, calibTools.calibrationPositionRange_Z, calibTools.numberOfCalibrationPoints)
if experimentObject.config.sysCfg['use_wiimote']:
	experimentObject.registerWiimoteActions()


IOD = 0.06
# create a node3D leftEyeNode
leftEyeNode = vizshape.addSphere(0.005, color = viz.BLUE)
#leftEyeNode.visible(viz.OFF)
leftEyeNode.setParent(headTracker)
leftEyeNode.setPosition(-IOD/2, 0, 0.0,viz.ABS_PARENT)
left_sphere = gazeSphere(eyeTracker,viz.LEFT_EYE,leftEyeNode,[clientWindowID],sphereColor=viz.YELLOW)
leftGazeVector = gazeVector(eyeTracker,viz.LEFT_EYE,leftEyeNode,[clientWindowID],gazeVectorColor=viz.YELLOW)
left_sphere.toggleUpdate()
leftGazeVector.toggleUpdate()
left_sphere.node3D.alpha(0.7)
leftEyeNode.alpha(0.01)

# create a node3D rightEyeNode
rightEyeNode = vizshape.addSphere(0.005, color = viz.RED)
#rightEyeNode.visible(viz.OFF)
rightEyeNode.setParent(headTracker)
rightEyeNode.setPosition(IOD/2, 0, 0.0,viz.ABS_PARENT)
right_sphere = gazeSphere(eyeTracker,viz.RIGHT_EYE,rightEyeNode,[clientWindowID],sphereColor=viz.ORANGE)
rightGazeVector = gazeVector(eyeTracker,viz.RIGHT_EYE,rightEyeNode,[clientWindowID],gazeVectorColor=viz.ORANGE)
right_sphere.toggleUpdate()
rightGazeVector.toggleUpdate()
right_sphere.node3D.alpha(0.7)
rightEyeNode.alpha(0.01)


###
def labelDisplay():
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

def timeStampOnScreen():

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

textObj = timeStampOnScreen()

###

hmd = experimentObject.config.mocap.get_rigidTracker('hmd')


oT = vizconnect.getRawTracker('rift_tracker')





#with viz.cluster.MaskedContext(1L):#viz.ALLCLIENTS&~viz.MASTER):
#	myMatrix = viz.Transform()
#	myMatrix = viz.Transform()
#	myMatrix.setEuler(0, 45, 0)
#	myMatrix.setTrans(0, 1, -.2)
###headTracker.setMatrix( myMatrix )
#	viz.MainWindow.setViewOffset( myMatrix )






##  Heres how to put a ball in head-centered coordinates
#newBall = vizshape.addSphere(0.25,color = viz.GREEN)
#newBall.setParent(headTracker)
#newBall.setPosition(0,0,3,viz.ABS_PARENT)
#newBall.renderOnlyToWindows([viz.VizWindow(viz.MASTER)])

#newBall.renderOnlyToWindows([clientWindowID])
#
#rt = vizconnect.getTracker('rift_tracker')
#rtLink = rt.getLink()
#
#link

rd = vizconnect.getDisplay('rift_display')

vp = rd.getViewpoint()

#rdb = vizconnect.getDisplayBase('rift_display')

