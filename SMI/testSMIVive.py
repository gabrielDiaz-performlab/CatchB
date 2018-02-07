import ctypes


try:
	#ctypes.windll.libiViewNG-HMD-API64
	smi = viz.add('smi_vive.dle')
except:
	print('Nope')