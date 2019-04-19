import os
import viz
import math
import ctypes

# Module is only supported with Vizard 5.1
#cv = viz.compareVersion('5.1')
#if cv < 0:
#	raise EnvironmentError('SMI module is incompatible with Vizard {}. Please contact support@worldviz.com for latest version.'.format(viz.version()))
#elif cv > 0:
#	raise EnvironmentError('SMI module requires Vizard 5.1')

# Ensure we are not 64-bit
if viz.getOption('platform.bit','32') != '32':
	raise EnvironmentError('SMI module does not support 64-bit versions of Vizard')

# Callback result structure
class _CallbackDataStruct(ctypes.Structure):
	_fields_ = [ ("type", ctypes.c_uint)
				,("result", ctypes.c_void_p)
	]

_CallbackDataStructPointer = ctypes.POINTER(_CallbackDataStruct)

# Callback type
_smiCallback = ctypes.WINFUNCTYPE(None, _CallbackDataStructPointer)

# EyeDataHMDStruct
class _EyeDataHMDStruct(ctypes.Structure):
	_fields_ = [ ("gazePoint_x", ctypes.c_double)
				,("gazePoint_y", ctypes.c_double)
				,("gazePoint_z", ctypes.c_double)
				,("gazeDir_x", ctypes.c_double)
				,("gazeDir_y", ctypes.c_double)
				,("gazeDir_z", ctypes.c_double)
				,("por_x", ctypes.c_double)
				,("por_y", ctypes.c_double)
				,("pupilRadius", ctypes.c_double)
				,("pupilPos_x", ctypes.c_double)
				,("pupilPos_y", ctypes.c_double)
				,("pupilPos_z", ctypes.c_double)
				,("eyeLensDistance", ctypes.c_double)
				,("eyeScreenDistance", ctypes.c_double)
	]

# Gaze sample structure
class _SampleHMDStruct(ctypes.Structure):
	_fields_ = [ ("size", ctypes.c_size_t)
				,("timestamp", ctypes.c_ulonglong)
				,("iod", ctypes.c_double)
				,("ipd", ctypes.c_double)
				,("por_x", ctypes.c_double)
				,("por_y", ctypes.c_double)
				,("gazeDir_x", ctypes.c_double)
				,("gazeDir_y", ctypes.c_double)
				,("gazeDir_z", ctypes.c_double)
				,("gazePoint_x", ctypes.c_double)
				,("gazePoint_y", ctypes.c_double)
				,("gazePoint_z", ctypes.c_double)
				,("leftEye", _EyeDataHMDStruct)
				,("rightEye", _EyeDataHMDStruct)
	]

_SampleHMDStructPointer = ctypes.POINTER(_SampleHMDStruct)


# Tracking parameter structure
class _TrackingParameterStruct(ctypes.Structure):
	_fields_ = [ ("mappingDistance", ctypes.c_double)
	]

# Calibration types
SMI_NONE					= 0
SMI_ONE_POINT_CALIBRATION 	= 1
SMI_THREE_POINT_CALIBRATION = 2

# Stream type
_SIMPLE_GAZE_SAMPLE 	= 0

# Distance from eye to physical screen (meters)
SCREEN_DISTANCE			= 1.5

# Complete Horizontal and Vertical field of view (degrees)
FIELD_OF_VIEW			= 87.0

# Screen resolution
SCREEN_HRES				= 1920.0
SCREEN_VRES				= 1080.0

def _loadLibrary():
	"""Load iViewHMDAPI DLL"""

	try:
		return ctypes.windll.iViewHMD_HTC_CPP
		#return ctypes.windll.iViewHMDAPI
	except:

		# Try searching for it in program files
		install_path = os.path.join(os.environ['PROGRAMFILES'], r'SMI\iViewNG-HMD\HMD C++ Example\bin')
		if os.path.isdir(install_path):
			os.environ['PATH'] = ';'.join([os.environ['PATH'], install_path])
			try:
				return ctypes.windll.iViewHMDAPI
			except:
				pass

	raise RuntimeError('Could not load iView HMD library')

class iViewHMD(viz.EventClass):

	def __init__(self, simulate=False):

		viz.EventClass.__init__(self)

		# List of samples
		self.current_sample = None
		self.last_sample = None

		# Load DLL
		self.iview = _loadLibrary()

		# Get path of DLL
		GetModuleFileName = ctypes.WinDLL("kernel32.dll").GetModuleFileNameW
		path = ctypes.create_unicode_buffer(260)
		if GetModuleFileName(self.iview._handle, path, 260):
			folder = os.path.dirname(path.value)
		else:
			folder = ''

		# Temporarily change working directory to iView DLL location
		prev_cwd = os.getcwd()
		if folder:
			os.chdir(folder)
		try:

			def _smi_callback(result):
				self._handle_result(result)

			# Need to hold reference to callback function wrapper
			self._callback_wrapper = _smiCallback(_smi_callback)

			# Register callback function
			getattr(self.iview, '_smi_setCallback@4')(self._callback_wrapper)

			# Start streaming
			params = _TrackingParameterStruct()
			params.mappingDistance = 1500.0
			result = getattr(self.iview, '_smi_startStreaming@8')(ctypes.c_bool(simulate), ctypes.pointer(params))
			if result != 1:
				raise RuntimeError('Failed to connect to SMI eye tracker')

		finally:

			# Restore previous working directory
			os.chdir(prev_cwd)

		# Register update callback for processing samples
		self.callback(viz.UPDATE_EVENT, self._update, priority=viz.PRIORITY_INPUT)
		self.callback(viz.EXIT_EVENT, self._onExit)

	def _handle_result(self, result):
		data = result.contents
		if data.type == _SIMPLE_GAZE_SAMPLE:
			s = ctypes.cast(data.result, _SampleHMDStructPointer).contents
			if not math.isnan(s.gazeDir_x):
				new_sample = _SampleHMDStruct()
				ctypes.pointer(new_sample)[0] = s
				self.current_sample = new_sample

	def _update(self, e):
		self.last_sample = self.current_sample

	def _eventClassRemoved(self):
		if self.iview:
			getattr(self.iview, '_smi_quit@0')()
			self._callback_wrapper = None
			self.iview = None

	def _onExit(self):
		self.unregister()

	def remove(self):
		"""Disconnect  from eye tracker"""
		self.unregister()

	def getLastSample(self):
		"""Return the last received sample"""
		return self.last_sample

	def getLastGazeMatrix(self, eye=viz.BOTH_EYE):
		"""Returns the last received gaze matrix in HMD coordinate system"""
		m = viz.Matrix()
		s = self.getLastSample()
		if s:
			if eye == viz.LEFT_EYE:
				s = s.leftEye
			elif eye == viz.RIGHT_EYE:
				s = s.rightEye

			xoff = SCREEN_DISTANCE * math.tan(math.radians(FIELD_OF_VIEW / 2.0))
			yoff = SCREEN_DISTANCE * math.tan(math.radians(FIELD_OF_VIEW / 2.0))
			zoff = SCREEN_DISTANCE

			gx =  ((s.por_x * 2.0 * xoff) / SCREEN_HRES - xoff)
			gy =  -((s.por_y * 2.0 * yoff) / SCREEN_VRES - yoff)
			gz = zoff

			m.makeVecRotVec([0,0,1], viz.Vector(gx, gy, gz, normalize=True))
			
			#print 'Time: ' + str(s.timestamp)
			#print 'Time: ' + str(viz.getFrameElapsed())
		return m

	def calibrate(self):
		if self.iview:
			getattr(self.iview, '_smi_calibrate@0')()

	def resetCalibration(self):
		if self.iview:
			getattr(self.iview, '_smi_resetCalibration@0')()

	def cancelCalibration(self):
		if self.iview:
			getattr(self.iview, '_smi_abortCalibration@0')()

	def validate(self):
		if self.iview:
			getattr(self.iview, '_smi_validate@0')()

#	def gd_drawGaze(self):
#		
#		self.getGazePoint()
		
	
if __name__ == '__main__':
	viz.go()
	g = iViewHMD(simulate=True)
	viz.addChild('gallery.osgb')
