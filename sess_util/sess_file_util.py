"""
sess_file_util.py

This module contains functions for dealing with reading and writing of data 
files generated by the AIBS experiments for the Credit Assignment Project.

Authors: Blake Richards

Date: August, 2018

Note: this code uses python 2.7.

"""

import exceptions
import os.path

import json
import pandas as pd
import pickle

from util import file_util


###############################################################################
def get_file_names(masterdir, sessid, expid, date, mouseid, runtype='prod',
                   mouse_dir=True):
    """
    get_file_names(masterdir, sessionid, expid, date, mouseid)

    Returns the full path names of all of the expected data files in the 
    main_directory for the specified session and experiment on the given date 
    that can be used for the Credit Assignment analysis.
 
    Required arguments:
        - masterdir (str): name of the master data directory
        - sessid (int)   : session ID (9 digits), e.g. '712483302'
        - expid (str)    : experiment ID (9 digits), e.g. '715925563'
        - date (str)     : date for the session in YYYYMMDD
                           e.g. '20160802'
        - mouseid (str)  : mouse 6-digit ID string used for session files
                           e.g. '389778' 

    Optional arguments
        - runtype (str)   : 'prod' (production) or 'pilot' data
                            default: 'prod'
        - mouse_dir (bool): if True, session information is in a 'mouse_*'
                            subdirectory
                            default: True

    Returns:
        - expdir (str)            : full path name of the experiment directory
        - procdir (str)           : full path name of the processed 
                                    data directory
        - stim_pkl_file  (str)    : full path name of the stimulus
                                    pickle file
        - stim_sync_file (str)    : full path name of the stimulus
                                    synchronization hdf5 file
        - align_pkl_file (str)    : full path name of the stimulus
                                    alignment pickle file
        - corrected_data (str)    : full path name of the motion
                                    corrected 2p data hdf5 file
        - roi_trace_data (str)    : full path name of the ROI raw fluorescence 
                                    trace hdf5 file
        - roi_trace_data_dff (str): full path name of the ROI dF/F trace 
                                    hdf5 file
        - zstack (str)            : full path name of the zstack 2p hdf5 file
    """
    
    # get the name of the session and experiment data directories
    if mouse_dir:
        sessdir = os.path.join(masterdir, runtype, 'mouse_{}'.format(mouseid), 
                               'ophys_session_{}'.format(sessid))
    else:
        sessdir = os.path.join(masterdir, runtype, 
                               'ophys_session_{}'.format(sessid))

    expdir = os.path.join(sessdir, 'ophys_experiment_{}'.format(expid))
    procdir = os.path.join(expdir, 'processed')

    # check that directory exists 
    try:
        file_util.checkdir(sessdir)
    except OSError:
        raise exceptions.UserWarning(('{} does not conform to expected AIBS '
                                      'structure').format(sessdir))

    # set the file names
    sess_m_d = '{}_{}_{}'.format(sessid, mouseid, date) 
    stim_pkl_file  = os.path.join(sessdir, '{}_stim.pkl'.format(sess_m_d))
    stim_sync_file = os.path.join(sessdir, '{}_sync.h5'.format(sess_m_d))
    align_pkl_file = os.path.join(sessdir, '{}_df.pkl'.format(sess_m_d))
    corrected_data = os.path.join(procdir, 'concat_31Hz_0.h5')
    roi_trace_data = os.path.join(procdir, 'roi_traces.h5')
    roi_trace_dff  = os.path.join(procdir, 'roi_traces_dff.h5')
    zstack         = os.path.join(sessdir, '{}_zstack_column.h5'.format(sessid))

    # double check that the files actually exist
    if not os.path.isfile(stim_pkl_file):
        raise OSError('{} does not exist'.format(stim_pkl_file))
    if not os.path.isfile(stim_sync_file):
        raise OSError('{} does not exist'.format(stim_sync_file))
    #if not os.path.isfile(corrected_data): ADD THIS BACK LATER...
    #    raise OSError('{} does not exist'.format(corrected_data))
    if not os.path.isfile(roi_trace_data):
        raise OSError('{} does not exist'.format(roi_trace_data))
    #if not os.path.isfile(zstack): ADD THIS BACK LATER...
    #    raise OSError('{} does not exist'.format(zstack))

    # TO-DO: ADD OTHER KEY FILES

    return [expdir, procdir, stim_pkl_file, stim_sync_file, align_pkl_file, 
            corrected_data, roi_trace_data, roi_trace_dff, zstack]


