from zmq_tools import *
import zmq, msgpack, time, threading, ctypes, math, viz

# 2D vector type
class _Vec2d(ctypes.Structure):
	_fields_ = [ ("x", ctypes.c_double)
				,("y", ctypes.c_double)
	]

# 3D vector type
class _Vec3d(ctypes.Structure):
	_fields_ = [ ("x", ctypes.c_double)
				,("y", ctypes.c_double)
				,("z", ctypes.c_double)
				]

# EyeDataHMDStruct
class _EyeDataHMDStruct(ctypes.Structure):
	_fields_ = [ ("gazeBasePoint", _Vec3d)
				,("gazeDirection", _Vec3d)
				#,("por", _Vec2d)
				,("pupilRadius", ctypes.c_double)
				,("pupilPosition", _Vec3d)
				#,("eyeLensDistance", ctypes.c_double)
				#,("eyeScreenDistance", ctypes.c_double)
				,("isValid", ctypes.c_bool)
	]

# Gaze sample structure
class _SampleHMDStruct(ctypes.Structure):
	_fields_ = [ ("timestamp", ctypes.c_double)
				,("iod", ctypes.c_double)
				,("ipd", ctypes.c_double)
				,("por", _Vec2d)
				,("gazeDirection", _Vec3d)
				,("gazeBasePoint", _Vec3d)
				,("leftEye", _EyeDataHMDStruct)
				,("rightEye", _EyeDataHMDStruct)
				,("isValid", ctypes.c_bool)
				,("gazePosition", _Vec3d)
	]
#avg function for 3 dimensional a,b
def vec_avg_3d(a,b):
	new_x = (a[0] + b[0])/2.0
	new_y = (a[1] + b[1])/2.0
	new_z = (a[2] + b[2])/2.0
	return _Vec3d(new_x,new_y,new_z)
	
#euclidean distance
def vec_dist_3d(a,b):
	return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2 )

def gaze_sample_to_struct(gaze):
	'''
	Function that takes python dict from eye tracker and turns into 
	a HMD sample struct that uses ctypes. Note: id 1 = left, for gaze info.
	This should hold for the models in base_data but have not confirmed
	'''
	timestamp = gaze['timestamp']
	#base_data is list of dicts, one for each eye
	base_data = gaze['base_data'] 
	
	base_data_l = {}
	base_data_r = {}
	
	#pick left and right
	for d in base_data:
		if d['id'] == 0:
			base_data_r = d
		elif d['id'] == 1:
			base_data_l = d
	
	#gaze normals/pos will be dict, with 0 = right eye 1 = left
	gaze_normals_3d = gaze['gaze_normals_3d']
	eye_centers_3d  = gaze['eye_centers_3d']

	isLeft  = 1 in gaze_normals_3d.keys()
	isRight = 0 in gaze_normals_3d.keys()
	
	leftEye  = _EyeDataHMDStruct()
	rightEye = _EyeDataHMDStruct()
	
	if isLeft:
		#direction and position for eye
		gaze_norm_l   = gaze_normals_3d[1]
		gaze_dir_l    = _Vec3d(float(gaze_norm_l[0]),float(gaze_norm_l[1]),float(gaze_norm_l[2]))
		gaze_pos_l    = eye_centers_3d[1]
		gaze_base_l   = _Vec3d(float(gaze_pos_l[0]),float(gaze_pos_l[1]),float(gaze_pos_l[2]))
		
		#pupil position and radius
		pupil_radius_l = max(base_data_l['ellipse']['axes'])/2.0
		pupil_pos_l    = base_data_l['circle_3d']['center']
		pupil_base_l   = _Vec3d(float(pupil_pos_l[0]),float(pupil_pos_l[1]),float(pupil_pos_l[2]))
		
		leftEye = _EyeDataHMDStruct(gaze_base_l,gaze_dir_l,pupil_radius_l,pupil_base_l,True)
		
	if isRight:
		#direction and position for eye
		gaze_norm_r   = gaze_normals_3d[0]
		gaze_dir_r    = _Vec3d(float(gaze_norm_r[0]),float(gaze_norm_r[1]),float(gaze_norm_r[2]))
		gaze_pos_r    = eye_centers_3d[0]
		gaze_base_r   = _Vec3d(float(gaze_pos_r[0]),float(gaze_pos_r[1]),float(gaze_pos_r[2]))
		
		#pupil position and radius
		pupil_radius_r   = max(base_data_r['ellipse']['axes'])/2.0
		pupil_pos_r      = base_data_r['circle_3d']['center']
		pupil_base_r     = _Vec3d(float(pupil_pos_r[0]),float(pupil_pos_r[1]),float(pupil_pos_r[2]))
		
		#print(pupil_radius_r)
		rightEye = _EyeDataHMDStruct(gaze_base_r,gaze_dir_r,pupil_radius_r,pupil_base_r,True)
		
	#compute IOD and IPD
	#average left and right base positions for cyclopian eye (if have both)
	#I think average normals for cyclopian gaze dir, TODO: ask Kamran
	#then set isValid to true?
	iod       = -1.0
	ipd       = -1.0
	gaze_base = _Vec3d()
	#TODO: can we cyclopian direction by just normalizing the gaze_point_3d val?
	gaze_dir  = _Vec3d()
	
	if isLeft and isRight:
		gaze_base = vec_avg_3d(gaze_pos_l,gaze_pos_r)
		iod       = vec_dist_3d(gaze_pos_l,gaze_pos_r)
		ipd       = vec_dist_3d(pupil_pos_l,pupil_pos_r)
		gaze_dir  = vec_avg_3d(gaze_norm_l,gaze_norm_r)
		
	elif isLeft and not isRight:	
		gaze_base = _Vec3d(gaze_pos_l[0],gaze_pos_l[1],gaze_pos_l[2])
		gaze_dir  = _Vec3d(gaze_norm_l[0],gaze_norm_l[1],gaze_norm_l[2])
	
	elif not isLeft and isRight:	
		gaze_base = _Vec3d(gaze_pos_r[0],gaze_pos_r[1],gaze_pos_r[2])
		gaze_dir  = _Vec3d(gaze_norm_r[0],gaze_norm_r[1],gaze_norm_r[2])
		
	#screen por
	norm_pos = gaze['norm_pos']
	por      = _Vec2d(norm_pos[0],norm_pos[1])
		
	#get current reported gaze position. I don't save this to file.
	gaze_in_world  = gaze['gaze_point_3d']
	gaze_world_pos = _Vec3d(gaze_in_world[0],gaze_in_world[1],gaze_in_world[2])
		
	#wrap into struct. Probably didn't need to do this ctypes stuff...
	ret = _SampleHMDStruct(timestamp,iod,ipd,por,gaze_dir,gaze_base,leftEye,rightEye,True,gaze_world_pos)
	
	return ret

class HMD(viz.EventClass):

	def __init__(self,simulate=False):
		viz.EventClass.__init__(self)

		# List of samples
		self.current_sample = None
		self.last_sample = None
		
		if simulate:
			#set a default front facing value for simulated data
			self.last_sample = self.fake_sample()
			
			
		else:
			#connect and set up zmq socket
			#TODO: this isn't good, but assumes the capture program is running
			#or else it will block trying to connect. The eye processes should be started 
			#to ensure data is streaming
			#Ideally calibration is done. Need to use 3d model for proper fields
			ctx = zmq.Context()
			
			#create a zmq REQ socket to talk to Pupil Service/Capture
			req = ctx.socket(zmq.REQ)
			req.connect('tcp://localhost:50776')
			
			req.send_string('SUB_PORT')
			ipc_sub_port = req.recv_string()
			monitor = Msg_Receiver(ctx,'tcp://localhost:%s'%ipc_sub_port,topics=('gaze',))
			
			self.ctx     = ctx
			self.monitor = monitor
			self.isRunning = True
			
			#use a thread for data
			#daemon lets thread keep running and kil itself with isRunning flag
			thread = threading.Thread(target=self.worker_gaze)
			thread.daemon  = True
			thread.start()
			
			# Register update callback for processing samples
			self.callback(viz.UPDATE_EVENT, self._update, priority=viz.PRIORITY_INPUT)
			self.callback(viz.EXIT_EVENT, self._onExit)
		
	def fake_sample(self):
		"""
		"fields needed: timestamp, base_data, gaze_normals_3d, eye_centers_3d, norm_pos
		"Function generates a dictionary that looks like pupil data for testing.
		"Currently it has por of middle of screen, and vectors that point there.
		"Other values are random ones drawn from previous data!!
		"""
		fake_sample = {}
		fake_sample['timestamp'] = 42
		fake_sample['norm_pos']  = [0.5,0.5]
		fake_sample['base_data'] = [{u'model_id': 4,
			u'confidence': 1.0,
			u'projected_sphere': {u'axes': [569.5938179502424, 569.5938179502424], u'angle': 90.0, u'center': [326.10692036226584, 172.52169978498236]}, 
			u'theta': 2.051412518461851, 
			u'diameter': 86.17463846429456, 
			u'timestamp': 32127.940532872253, 
			u'topic': u'pupil', 
			u'model_confidence': 0.8620186604689439, 
			u'ellipse': {u'axes': [64.49092984200377, 86.17463846429456], 
				u'angle': 62.42276128242774, 
				u'center': [423.84274460265607, 345.37151681360695]}, 
			u'phi': -1.3441180793012093, 
			u'sphere': {u'radius': 12.0, u'center': [0.25731685294938317, -2.8432176651571295, 26.12387903637652]}, 
			u'diameter_3d': 2.1838271861052205, 
			u'norm_pos': [0.6622542884416501, 0.28047600663831884], 
			u'model_birth_timestamp': 32101.076832098905, 
			u'method': u'3d c++', 
			u'circle_3d': {u'radius': 1.0919135930526103, u'center': [2.6486890898118403, 2.7046900954825928, 15.755559099945303], u'normal': [0.19928101973853812, 0.46232564671997683, -0.8640266613692679]}, 
			u'id': 0},
			
			{u'model_id': 3, 
			u'confidence': 1.0, 
			u'projected_sphere': {u'axes': [601.3759735355978, 601.3759735355978], u'angle': 90.0, u'center': [325.7584159333456, 338.06023849151165]}, 
			u'topic': u'pupil', 
			u'timestamp': 32127.93536995835, 
			u'diameter': 84.09255143774365, 
			u'norm_pos': [0.4328912048265856, 0.7566546172047827], 
			u'model_confidence': 0.8497364290066534, 
			u'id': 1, 
			u'phi': -1.7012963223357482, 
			u'sphere': {u'radius': 12.0, u'center': [0.2298096174141764, 3.9134349015640724, 24.74325655632332]}, 
			u'diameter_3d': 2.0359624942650045, 
			u'ellipse': {u'axes': [57.73462802162427, 84.09255143774365], 
				u'angle': 78.16578588707786, 
				u'center': [277.0503710890148, 116.80578374170433]}, 
			u'theta': 0.9554435830606223, 
			u'model_birth_timestamp': 32098.45600709769, 
			u'circle_3d': {u'radius': 1.0179812471325023, u'center': [-1.0453122893625364, -3.0135242756383245, 15.027738007103746], u'normal': [-0.1062601588980594, -0.5772465981001997, -0.8096265457682978]}, 
			u'method': u'3d c++'}]
			
		fake_sample['eye_centers_3d'] = {0: [30.48326101118493, -3.130420013921086, -8.098577694529986], 1: [-39.397736175620004, -1.8927187399314593, 9.37360038366472]}
		fake_sample['gaze_normals_3d'] = {0 : [0.04746206531000101, -0.057599780997435845, 0.9972109193072224], 1 : [0.32310359766817387, 0.13014961901050148, 0.9373714001639393]}
		fake_sample['gaze_position_3d'] = [0.0,0.0,1.0]
		fake_sample['gaze_point_3d'] = [0.0,0.0,1]
		
		return fake_sample
	
	def getLastSample(self):
		if self.last_sample:
			return gaze_sample_to_struct(self.last_sample)
		else:
			return None
		
	def worker_gaze(self):
		while self.isRunning:
			topic,g = self.monitor.recv()
			self.current_sample = g
			#print (g)
		self.ctx.destroy()

	def stop(self):
		self.isRunning = False
		
	def _update(self,e):
		self.last_sample = self.current_sample
		
	def _onExit(self):
		self.isRunning = False
		