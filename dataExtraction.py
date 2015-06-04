import LoadParameters
import DataExtraction
import os
import numpy as np
import scipy.io as sio
from configobj import ConfigObj


subNum = 2

def ParseTextData( self, TextFileName ):

    #datapath = '/Users/kamranbinaee/Documents/Python-Programming/Matlab2PythonProject';
    
    #fname = os.path.join(datapath,'DataPoints0.txt')
    
    txtFile = open(TextFileName +'.txt',"r") # "exp_data-2014-5-9-13-9 copy.txt"
    values = np.array([],dtype = float);
    i = 0
    
    X_Matrix = np.array([], dtype = float);
    Y_Matrix = np.array([], dtype = float);
    Z_Matrix = np.array([], dtype = float);
    C_Matrix = np.array([], dtype = float);
    F_Matrix = np.array([], dtype = float);
    eyeTimeStamp = np.array([], dtype = float);
    inCalibrate = np.array([], dtype = float);
    EventFlag = np.array([], dtype = float);
    TrialType = np.array([], dtype = str);
    view_XYZ_Matrix = np.array([],  dtype = float);
    view_Quat_Matrix = np.array([], dtype = float);
    Paddle_XYZ_Matrix = np.array([],  dtype = float);
    Paddle_Quat_Matrix = np.array([], dtype = float);
    Ball_XYZ_Matrix = np.array([],  dtype = float);
    Ball_Vel_XYZ_Matrix = np.array([],  dtype = float);
    Inv_view_Matrix = np.array([],  dtype = float);
    Inv_Pro_Matrix = np.array([],  dtype = float);
    BallPix_XYDist = np.array([],  dtype = float);

    view_XYZ_Matrix.resize((1,3))
    view_Quat_Matrix.resize((1,4))
    Paddle_XYZ_Matrix.resize((1,3))
    Paddle_Quat_Matrix.resize((1,4))
    Ball_XYZ_Matrix.resize((1,3))
    Ball_Vel_XYZ_Matrix.resize((1,3))
    Inv_view_Matrix.resize((1,16))
    Inv_Pro_Matrix.resize((1,16))
    BallPix_XYDist.resize((1,3))

    print 'Parsing TextData in progress for',TextFileName,'.txt ....\n' 
    
    for aline in txtFile:
        Line = aline.split()
        for i in range(len(Line)):
            #print 'TextFile Parsing'
            if (Line[i] == 'frameTime'):
                F_Matrix = np.hstack((F_Matrix, Line[i+1]))
            elif (Line[i] == 'eyeTimeStamp'):
                eyeTimeStamp = np.hstack((eyeTimeStamp, Line[i+1]))
            elif (Line[i] == 'inCalibrateBool'):
                inCalibrate = np.hstack((inCalibrate, Line[i+1]))
            elif (Line[i] == 'eventFlag'):
                EventFlag = np.hstack((EventFlag,Line[i+1]));
            elif (Line[i] == 'trialType'):
                TrialType = np.hstack((TrialType, Line[i+1]));
            elif (Line[i] == 'viewPos_XYZ'):
                view_XYZ_Matrix = np.vstack((view_XYZ_Matrix, np.array([Line[i+1], Line[i+2], Line[i+3]]) ));
            elif (Line[i] == 'viewQUAT_WXYZ'):
                view_Quat_Matrix = np.vstack((view_Quat_Matrix, np.array([Line[i+1], Line[i+2], Line[i+3], Line[i+4]])))
            elif (Line[i] == 'paddlePos_XYZ'):
                Paddle_XYZ_Matrix = np.vstack((Paddle_XYZ_Matrix, np.array([Line[i+1], Line[i+2], Line[i+3]]) ));    
            elif (Line[i] == 'paddleQUAT_WXYZ'):
                Paddle_Quat_Matrix = np.vstack((Paddle_Quat_Matrix, np.array([Line[i+1], Line[i+2], Line[i+3], Line[i+4]])))
            elif (Line[i] == 'ballPos_XYZ'):
                Ball_XYZ_Matrix = np.vstack((Ball_XYZ_Matrix, np.array([Line[i+1], Line[i+2], Line[i+3]]) ));
            elif (Line[i] == 'ballVel_XYZ'):
                Ball_Vel_XYZ_Matrix = np.vstack((Ball_Vel_XYZ_Matrix, np.array([Line[i+1], Line[i+2], Line[i+3]]) ));
            elif (Line[i] == 'ballPix_XYDist'):
                BallPix_XYDist = np.vstack((BallPix_XYDist, np.array([Line[i+1], Line[i+2], Line[i+3]]) ));
            #elif (Line[i] == 'invViewMat'):
                #Inv_view_Matrix = np.vstack((Inv_view_Matrix, np.array([Line[i+1:i+16]]) ));
            #elif (Line[i] == 'invProMat'):
                #Inv_Pro_Matrix = np.vstack((Inv_Pro_Matrix, np.array([Line[i+1:i+16]]) ));
    txtFile.close()
    
    view_XYZ_Matrix = np.delete(view_XYZ_Matrix, 0, 0)
    view_Quat_Matrix = np.delete(view_Quat_Matrix, 0, 0)
    Paddle_XYZ_Matrix = np.delete(Paddle_XYZ_Matrix, 0, 0)
    Paddle_Quat_Matrix = np.delete(Paddle_Quat_Matrix, 0, 0)
    Ball_XYZ_Matrix = np.delete(Ball_XYZ_Matrix, 0, 0)
    Ball_Vel_XYZ_Matrix = np.delete(Ball_Vel_XYZ_Matrix, 0, 0)
    BallPix_XYDist = np.delete(BallPix_XYDist, 0, 0)

    #print 'Pos size=\n', XYZ_Matrix.shape
    #print 'F size=\n', F_Matrix.shape
    #print 'E size=\n', EventFlag.shape
    #print 'T size=\n', Inv_view_Matrix.shape
    #print 'Q size=\n', Inv_Pro_Matrix.shape

    print '...Text File Parsing Done!!'
    
    MatFile = {'FrameTime':F_Matrix,'inCalibrateBool':inCalibrate, 'EventFlag':EventFlag,'TrialType':TrialType, 
    'view_XYZ_Pos':view_XYZ_Matrix,'Quat_Matrix':view_Quat_Matrix, 'paddlePos_XYZ':Paddle_XYZ_Matrix,
    'paddleQUAT_WXYZ':Paddle_Quat_Matrix, 'ballPos_XYZ':Ball_XYZ_Matrix, 'ballVel_XYZ':Ball_Vel_XYZ_Matrix,
    'ballPix_XYDist': BallPix_XYDist, 'invViewMat': Inv_view_Matrix, 'invProMat':Inv_Pro_Matrix}
    
    MatFileName = 'RawMat_' + TextFileName 
    sio.savemat(MatFileName + '.mat', MatFile)
    
    print MatFileName,'.mat File Saved'

if __name__ == "__main__":
    
    textFileName = 'exp_data-2015-3-24-16-32'
    ParseTextData(textFileName)