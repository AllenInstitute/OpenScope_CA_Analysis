"""
sess_gen_util.py

This module contains general functions for navigating data generated by 
the AIBS experiments for the Credit Assignment Project.

Authors: Colleen Gillon

Date: October, 2018

Note: this code uses python 3.7.

"""

import os

import numpy as np
import pandas as pd

from analysis import session
from sess_util import sess_str_util
from util import file_util, gen_util


#############################################
def depth_vals(layer, line):
    """
    depth_vals(layer, line)

    Returns depth values corresponding to a specified layer.

    Required args:
        - layer (str): layer (e.g., 'dend', 'soma', 'any')
        - line (str) : line (e.g., 'L23', 'L5', 'any')
    Returns:
        - depths (str or list): depths corresponding to layer and line or 'any'
    """

    if layer == 'any' and line == 'any':
        return 'any'
    
    depth_dict = {'L23_dend': [50, 75],
                  'L23_soma': [175],
                  'L5_dend' : [20],
                  'L5_soma' : [375]
                 }

    all_layers = ['dend', 'soma']
    if layer == 'any':
        layers = all_layers
    else:
        layers = gen_util.list_if_not(layer)
    
    all_lines = ['L23', 'L5']
    if line == 'any':
        lines = all_lines
    else:
        lines = gen_util.list_if_not(line)
    
    depths = []
    for layer in layers:
        if layer not in all_layers:
            gen_util.accepted_values_error('layer', layer, all_layers)
        for line in lines:
            if layer not in all_layers:
                gen_util.accepted_values_error('line', line, all_lines)
            depths.extend(depth_dict['{}_{}'.format(line, layer)])

    return depths


#############################################
def get_df_vals(mouse_df, returnlab, mouse_n, sessid, sess_n, runtype, depth, 
                pass_fail='P', all_files=1, any_files=1, min_rois=1, 
                unique=False, sort=False):
    """
    get_df_vals(mouse_df, returnlab, mouse_n, sessid, sess_n, runtype, depth)

    Returns values from mouse dataframe under a specified label that fit the 
    criteria.

    Required args:
        - mouse_df (pandas df)      : dataframe containing parameters for each 
                                      session.
        - returnlab (str)           : label from which to return values
        - mouse_n (int, str or list): mouse id value(s) of interest  
        - sessid (int or list)      : session id value(s) of interest
        - sess_n (int, str or list) : session number(s) of interest
        - runtype (str or list)     : runtype value(s) of interest       
        - depth (str or list)       : depth value(s) of interest (20, 50, 75,  
                                      175, 375)

    Optional args:
        - pass_fail (str or list)     : pass/fail values of interest ('P', 'F')
                                        default: 'P'
        - all_files (int, str or list): all_files values of interest (0, 1)
                                        default: 1
        - any_files (int, str or list): any_files values of interest (0, 1)
                                        default: 1
        - min_rois (int)              : min number of ROIs
                                        default: 1
        - unique (bool)               : whether to return a list of values 
                                        without duplicates
                                        default: False 
        - sort (bool)                 : whether to sort output values
                                        default: False
                                    
    Returns:
        - df_vals (list): list of values under the specified label that fit
                          the criteria
    """

    # make sure all of these labels are lists
    all_labs = [mouse_n, sessid, sess_n, runtype, depth, pass_fail, 
                all_files, any_files]
    for i in range(len(all_labs)):
        all_labs[i] = gen_util.list_if_not(all_labs[i])

    [mouse_n, sessid, sess_n, runtype, depth, 
              pass_fail, all_files, any_files] = all_labs

    df_vals = mouse_df.loc[(mouse_df['mouse_n'].isin(mouse_n)) & 
                           (mouse_df['sessid'].isin(sessid)) &
                           (mouse_df['sess_n'].isin(sess_n)) &
                           (mouse_df['runtype'].isin(runtype)) &
                           (mouse_df['depth'].isin(depth)) &
                           (mouse_df['pass_fail'].isin(pass_fail)) &
                           (mouse_df['all_files'].isin(all_files)) &
                           (mouse_df['any_files'].isin(any_files)) &
                           (mouse_df['nrois'].astype(int) >= min_rois)][returnlab].tolist()

    if unique:
        df_vals = list(set(df_vals))

    if sort:
        df_vals = sorted(df_vals)

    return df_vals


#############################################
def get_sess_vals(mouse_df, returnlab, mouse_n='any', sess_n='any', 
                  runtype='any', layer='any', line='any', pass_fail='P', 
                  all_files=1, any_files=1, min_rois=1, omit_sess=[], 
                  omit_mice=[], unique=True, sort=True):
    """
    get_sess_vals(mouse_df, returnlab)

    Returns list of values under the specified label that fit the specified
    criteria.

    Required args:
        - mouse_df (str) : path name of dataframe containing information 
                           on each session
        - returnlab (str): label from which to return values

    Optional args:
        - mouse_n (int, str or list)  : mouse number(s) of interest
                                        default: 'any'
        - sess_n (int, str or list)   : session number(s) of interest
                                        default: 'any'
        - runtype (str or list)       : runtype value(s) of interest
                                        ('pilot', 'prod')
                                        default: 'any'
        - layer (str or list)         : layer value(s) of interest
                                        ('soma', 'dend', 'any')
                                        default: 'any'
        - line (str or list)          : line value(s) of interest
                                        ('L5', 'L23', 'any')
                                        default: 'any'
        - pass_fail (str or list)     : pass/fail values of interest 
                                        ('P', 'F', 'any')
                                        default: 'P'
        - all_files (str, int or list): all_files values of interest (0, 1)
                                        default: 1
        - any_files (str, int or list): any_files values of interest (0, 1)
                                        default: 1
        - min_rois (int)              : min number of ROIs
                                        default: 1
        - omit_sess (list)            : sessions to omit
                                        default: []
        - omit_mice (list)            : mice to omit
                                        default: []
        - unique (bool)               : whether to return a list of values 
                                        without duplicates
                                        default: False 
        - sort (bool)                 : whether to sort output values
                                        default: False
     
    Returns:
        - sess_vals (list): values from dataframe that correspond to criteria
    """

    if isinstance(mouse_df, str):
        mouse_df = file_util.loadfile(mouse_df)

    # get depth values corresponding to the layer
    depth = depth_vals(layer, line)

    sessid      = 'any'
    params      = [mouse_n, sessid, sess_n, runtype, depth,  
                   pass_fail, all_files, any_files]
    param_names = ['mouse_n', 'sessid', 'sess_n', 'runtype', 'depth',
                   'pass_fail', 'all_files', 'any_files']
    
    # for each label, collect values in a list
    for i in range(len(params)):
        params[i] = gen_util.get_df_label_vals(mouse_df, param_names[i], 
                                               params[i])   
    [mouse_n, sessid, sess_n, runtype, depth,  
              pass_fail, all_files, any_files] = params

    # remove omitted sessions from the session id list
    sessid = gen_util.remove_if(sessid, omit_sess)
    
    # collect all mouse IDs and remove omitted mice
    mouse_n = gen_util.remove_if(mouse_n, omit_mice)

    sess_vals = get_df_vals(mouse_df, returnlab, mouse_n, sessid, sess_n, 
                            runtype, depth, pass_fail, all_files, 
                            any_files, min_rois, unique, sort)

    sess_vals = list(set(sess_vals)) # get unique

    return sess_vals


#############################################
def sess_per_mouse(mouse_df, mouse_n='any', sess_n=1, runtype='prod', 
                   layer='any', line='any', pass_fail='P', all_files=1, 
                   any_files=1, min_rois=1, closest=False, omit_sess=[], 
                   omit_mice=[]):
    """
    sess_per_mouse(mouse_df)
    
    Returns list of session IDs (up to 1 per mouse) that fit the specified
    criteria.

    Required args:
        - mouse_df (str): path name of dataframe containing information 
                          on each session
        
    Optional args:
        - mouse_n (int or str)   : mouse number(s) of interest
                                   default: 'any'
        - sess_n (int or str)    : session number(s) of interest
                                   (1, 2, 3, ... or 'last')
                                   default: 1
        - runtype (str or list)  : runtype value(s) of interest
                                   ('pilot', 'prod')
                                   default: 'prod'
        - layer (str or list)    : layer value(s) of interest
                                   ('soma', 'dend', 'any')
                                   default: 'any'
        - line (str or list)     : line value(s) of interest
                                   ('L5', 'L23', 'any')
                                   default: 'any'
        - pass_fail (str or list): pass/fail values of interest 
                                   ('P', 'F', 'any')
                                   default: 'P'
        - all_files (int or list): all_files values of interest (0, 1)
                                   default: 1
        - any_files (int or list): any_files values of interest (0, 1)
                                   default: 1
        - min_rois (int)         : min number of ROIs
                                   default: 1
        - closest (bool)         : if False, only exact session number is 
                                   retained, otherwise the closest
                                   default: False
        - omit_sess (list)       : sessions to omit
                                   default: []
        - omit_mice (list)       : mice to omit
                                   default: []
     
    Returns:
        - sessids (list): sessions to analyse (1 per mouse)
    """

    if closest or sess_n == 'last':
        sess_n = gen_util.get_df_label_vals(mouse_df, 'sess_n', 'any')
    
    if runtype == 'any':
        raise ValueError(('Must specify runtype (cannot be any), as there is '
                          'overlap in mouse numbers.'))

    # get list of mice that fit the criteria
    mouse_ns = get_sess_vals(mouse_df, 'mouse_n', mouse_n, sess_n, runtype,  
                             layer, line, pass_fail, all_files, any_files, 
                             min_rois, omit_sess, omit_mice, unique=True, 
                             sort=True)

    # get session ID each mouse based on criteria 
    sessids = []
    for i in sorted(mouse_ns):
        sess_ns = get_sess_vals(mouse_df, 'sess_n', i, sess_n, runtype, layer, 
                                line, pass_fail, all_files, any_files, 
                                min_rois, omit_sess, omit_mice, sort=True)
        # skip mouse if no sessions meet criteria
        if len(sess_ns) == 0:
            continue
        # if only exact sess n is accepted (not closest)
        elif sess_n == 'last' or not closest:
            sess_n = sess_ns[-1]
        # find closest sess number among possible sessions
        else:
            sess_n = sess_ns[np.argmin(np.absolute([x-sess_n 
                                                    for x in sess_ns]))]
        sessid = get_sess_vals(mouse_df, 'sessid', i, sess_n, runtype, layer, 
                               line, pass_fail, all_files, any_files, min_rois,
                               omit_sess, omit_mice)[0]
        sessids.append(sessid)
    
    if len(sessids) == 0:
        raise ValueError('No sessions meet the criteria.')

    return sessids


#############################################
def sess_comb_per_mouse(mouse_df, mouse_n='any', sess_n='1v2', runtype='prod', 
                        layer='any', line='any', pass_fail='P', all_files=1, 
                        any_files=1, min_rois=1, closest=False, omit_sess=[], 
                        omit_mice=[]):
    """
    sess_comb_per_mouse(mouse_df)
    
    Returns list of session ID combinations (2 per mouse) that fit the 
    specified criteria.

    Required args:
        - mouse_df (str): path name of dataframe containing information 
                          on each session
        
    Optional args:
        - mouse_n (int or str)   : mouse number(s) of interest
                                   default: 'any'
        - sess_n (int or str)    : session numbers of interest to compare
                                   default: '1v2'
        - runtype (str or list)  : runtype value(s) of interest
                                   ('pilot', 'prod')
                                   default: 'prod'
        - layer (str or list)    : layer value(s) of interest
                                   ('soma', 'dend', 'any')
                                   default: 'any'
        - line (str or list)     : line value(s) of interest
                                   ('L5', 'L23', 'any')
                                   default: 'any'
        - pass_fail (str or list): pass/fail values of interest 
                                   ('P', 'F', 'any')
                                   default: 'P'
        - all_files (int or list): all_files values of interest (0, 1)
                                   default: 1
        - any_files (int or list): any_files values of interest (0, 1)
                                   default: 1
        - min_rois (int)         : min number of ROIs
                                   default: 1
        - closest (bool)         : if False, only exact session number is 
                                   retained, otherwise the closest
                                   default: False
        - omit_sess (list)       : sessions to omit
                                   default: []
        - omit_mice (list)       : mice to omit
                                   default: []
     
    Returns:
        - sessids (list): session combinations to analyse, structured as 
                              mouse x sess
    """

    if closest:
        print(('Session comparisons not implemented using the `closest` '
               'parameter. Setting to False.'))
        closest = False

    if 'v' not in str(sess_n):
        raise ValueError('sess_n must be of a format like `1v3`.')

    sess_n = [int(n) for n in sess_n.split('v')]

    if runtype == 'any':
        raise ValueError(('Must specify runtype (cannot be any), as there is '
                          'overlap in mouse numbers.'))

    # get list of mice that fit the criteria
    mouse_ns = []
    for n in sess_n:
        ns = get_sess_vals(mouse_df, 'mouse_n', mouse_n, n, runtype,  
                           layer, line, pass_fail, all_files, any_files, 
                           min_rois, omit_sess, omit_mice, unique=True, 
                           sort=True)
        mouse_ns.append(ns)
    
    mouse_ns = set(mouse_ns[0]).intersection(set(mouse_ns[1]))

    # get session ID each mouse based on criteria 
    sessids = []
    for i in mouse_ns:
        mouse_sessids = []
        for n in sess_n:
            sessid = get_sess_vals(mouse_df, 'sessid', i, n, runtype, 
                                   layer, line, pass_fail, all_files, 
                                   any_files, min_rois, omit_sess, omit_mice)[0]
            mouse_sessids.append(sessid)
        sessids.append(mouse_sessids)
    
    if len(sessids) == 0:
        raise ValueError('No session combinations meet the criteria.')

    return sessids


#############################################
def init_sessions(sessids, datadir, mouse_df, runtype='prod', fulldict=True, 
                  dend='aibs', omit=False, pupil=False):
    """
    init_sessions(sessids, datadir)

    Creates list of Session objects for each session ID passed.

    Required args:
        - sessids (int or list): ID or list of IDs of sessions
        - datadir (str)        : directory where sessions are stored
        - mouse_df (str)       : path name of dataframe containing information 
                                 on each session

    Optional args:
        - runtype (str)  : the type of run, either 'pilot' or 'prod'
                           default: 'prod'
        - fulldict (bool): if True, the full stimulus dictionary is loaded 
                           (with all the brick positions).
                           default: True
        - dend (str)     : type of dendrites to use ('aibs' or 'extr')
                           default: 'aibs'
        - omit (bool)    : if True, dendritic sessions with the wrong type of 
                           dendrite are omitted
                           default: False
        - pupil (bool)   : if True, only sessions with pupil data are included
                           default: False

    Returns:
        - sessions (list): list of Session objects
    """

    sessions = []
    sessids = gen_util.list_if_not(sessids)
    for sessid in sessids:
        print('\nCreating session {}...'.format(sessid))
        # creates a session object to work with
        sess = session.Session(datadir, sessid, runtype=runtype) 
        # extracts necessary info for analysis
        sess.extract_sess_attribs(mouse_df)
        sess.extract_info(fulldict=fulldict, dend=dend)
        if omit and sess.layer == 'dend' and sess.dend != dend:
            print(('Omitting session {} ({} dendrites not '
                   'found).').format(sessid, dend))
        elif pupil and sess.pup_data_csv in ['none', 'several']:
            print(('Omitting session {} as {} pupil data csvs were '
                 'found.').format(sessid ,sess.pup_data_csv.replace('ne', '')))
        else:
            print('Finished session {}.'.format(sessid))
            sessions.append(sess)

    return sessions


#############################################
def get_nrois(nrois, n_nanrois=0, n_nanrois_dff=0, remnans=True, fluor='dff'):
    """
    get_nrois(nrois)

    Returns number of ROIs based on whether dF/F traces are used and ROIs with 
    NaN/Infs are removed from the data.

    Required args:
        - nrois (int)        : number of ROIs in the session
    
    Optional args:
        - n_nanrois (int)    : number of ROIs with NaN/Infs in the raw data
        - n_nanrois_dff (int): number of ROIs with NaN/Infs in the dF/F data
        - remnans (bool)     : if True, the number of ROIs with NaN/Infs is  
                               removed from the total
                               default: True
        - fluor (str)        : if 'raw', number of ROIs is calculated with 
                               n_nanrois. If 'dff', it is calculated with 
                               n_nanrois_dff  
                               default: 'dff'

    Returns:
        - nrois (int): resulting number of ROIs
    """

    if remnans:
        if fluor == 'dff':
            n_rem = n_nanrois_dff
        elif fluor == 'raw':
            n_rem = n_nanrois
        else:
            gen_util.accepted_values_error('fluor', fluor, ['raw', 'dff'])

        nrois = nrois - n_rem
    
    return nrois


#############################################
def get_sess_info(sessions, fluor='dff'):
    """
    get_sess_info(sessions)

    Puts information from all sessions into a dictionary.

    Required args:
        - sessions (list): ordered list of Session objects
    
    Optional args:
        - fluor (str)        : if 'dff', an error is thrown if the list of ROIs 
                               with NaNs/Infs in dF/F traces cannot be 
                               extracted
                               default: 'dff'

    Returns:
        - sess_info (dict): dictionary containing information from each
                            session 
                ['mouse_ns'] (list)   : mouse numbers
                ['mouseids'] (list)   : mouse ids
                ['sess_ns'] (list)    : session numbers
                ['sessids'] (list)    : session ids  
                ['lines'] (list)      : mouse lines
                ['layers'] (list)     : imaging layers
                ['nrois'] (list)      : number of ROIs in session
                ['twop_fps'] (list)   : 2p frames per second
                ['nanrois'] (list)    : list of ROIs with NaNs/Infs in raw
                                        trace
                ['nanrois_dff'] (list): list of ROIs with NaNs/Infs in dF/F
                                        traces, for sessions for which this 
                                        attribute exists
    """

    sess_info = dict()
    keys = ['mouse_ns', 'mouseids', 'sess_ns', 'sessids', 'lines', 'layers', 
            'nrois', 'twop_fps', 'nanrois', 'nanrois_dff']

    for key in keys:
        sess_info[key] = []

    sessions = gen_util.list_if_not(sessions)

    for _, sess in enumerate(sessions):
        sess_info['mouse_ns'].append(sess.mouse_n)
        sess_info['mouseids'].append(sess.mouseid)
        sess_info['sess_ns'].append(sess.sess_n)
        sess_info['sessids'].append(sess.sessid)
        sess_info['lines'].append(sess.line)
        sess_info['layers'].append(sess.layer)
        sess_info['nrois'].append(sess.nrois)
        sess_info['twop_fps'].append(sess.twop_fps)
        sess_info['nanrois'].append(sess.nanrois)

        if hasattr(sess, 'nanrois_dff'):
            sess_info['nanrois_dff'].append(sess.nanrois_dff)
        elif fluor == 'dff':
            raise ValueError(('dF/F nanrois cannot be added to sess_info, as '
                              'dF/F traces have not been loaded for '
                              'session {}'.format(sess.sessid)))
        else:
            sess_info['nanrois_dff'].append(None)
            
    return sess_info


#############################################
def get_params(stimtype='both', bri_dir='both', bri_size=128, gabfr=0, 
               gabk=16, gab_ori='all'):
    """
    get_params()

    Gets and formats full parameters. For example, replaces 'both' with a 
    list of parameter values, and sets parameters irrelevant to the stimulus
    of interest to 'none'.

    Required args:
        - stimtype  (str)            : stimulus to analyse 
                                       ('bricks', 'gabors', 'both')
        - bri_dir (str or list)      : brick direction values 
                                       ('right', 'left', 'both')
        - bri_size (int, str or list): brick size values (128, 256, 'both')
        - gabfr (int, list or str)   : gabor frame value (0, 1, 2, 3, '0_3', 
                                                          [0, 3])
        - gabk (int, str or list)    : gabor kappa values (4, 16, 'both')
        - gab_ori (int, str or list) : gabor orientation values 
                                       (0, 45, 90, 135 or 'all')

    Returns:
        - bri_dir (str or list) : brick direction values
        - bri_size (int or list): brick size values
        - gabfr (int)           : gabor frame values
        - gabk (int or list)    : gabor kappa values
        - gab_ori (int or list) : gabor orientation values

    """

    # get all the parameters
    if gabk == 'both':
        gabk = [4, 16]
    else:
        gabk = int(gabk)

    if gab_ori == 'all':
        gab_ori = [0, 45, 90, 135]
    else:
        gab_ori = int(gab_ori)

    if bri_size == 'both':
        bri_size = [128, 256]
    else:
        bri_size = int(bri_size)

    if bri_dir == 'both':
        bri_dir = ['right', 'left']

    # set to 'none' any parameters that are irrelevant
    if stimtype == 'gabors':
        bri_size = 'none'
        bri_dir = 'none'
    elif stimtype == 'bricks':
        gabfr = 'none'
        gabk = 'none'
        gab_ori = 'none'
    elif stimtype != 'both':
        gen_util.accepted_values_error('stim argument', stimtype, 
                                       ['gabors', 'bricks'])

    return bri_dir, bri_size, gabfr, gabk, gab_ori


#############################################
def pilot_gab_omit(gabk):
    """
    pilot_gab_omit(gabk)

    Returns IDs of pilot mice to omit based on gabor kappa values to include.

    Required args:
        - gabk (int or list): gabor kappa values (4, 16, [4, 16])
                                    
    Returns:
        - omit_mice (list): list IDs of mice to omit
    """
    gabk = gen_util.list_if_not(gabk)
    if 4 not in gabk:
        omit_mice = [1] # mouse 1 only got K=4
    elif 16 not in gabk:
        omit_mice = [3] # mouse 3 only got K=16
    else: 
        omit_mice = []
    return omit_mice


#############################################
def pilot_bri_omit(bri_dir, bri_size):
    """
    pilot_bri_omit(bri_dir, bri_size)

    Returns IDs of pilot mice to omit based on brick direction and size values 
    to include.

    Required args:
        - bri_dir (str or list) : brick direction values ('right', 'left')
        - bri_size (int or list): brick size values (128, 256, [128, 256])
                                    
    Returns:
        - omit_mice (list): list IDs of mice to omit
    """

    bri_dir = gen_util.list_if_not(bri_dir)
    bri_size = gen_util.list_if_not(bri_size)
    omit_mice = []

    if 'right' not in bri_dir:
        omit_mice.extend([3]) # mouse 3 only got bri_dir='right'
        if 128 not in bri_size:
            omit_mice.extend([1]) # mouse 1 only got bri_dir='left' with bri_size=128
    elif 'left' not in bri_dir and 256 not in bri_size:
        omit_mice.extend([1]) # mouse 1 only got bri_dir='right' with bri_size=256
    return omit_mice

    
#############################################
def all_omit(stimtype='gabors', runtype='prod', bri_dir='both', bri_size=128, 
             gabk=16):
    """
    all_omit()

    Returns list of mice and sessions to omit, based on analysis parameters 
    (runtype, gabk, bri_dir and bri_size) and throws an error if the parameter 
    combination requested does not occur in the dataset.

    Required args:
        - stimtype  (str)       : stimulus to analyse ('bricks', 'gabors')
        - runtype (str)         : runtype ('pilot', 'prod')
        - bri_dir (str or list) : brick direction values ('right', 'left')
        - bri_size (int or list): brick size values to include
                                  (128, 256, [128, 256])
        - gabk (int or list)    : gabor kappa values to include 
                                  (4, 16 or [4, 16])

    Returns:
        - omit_sess (list): sessions to omit
        - omit_mice (list): mice to omit
    """

    omit_sess = []
    omit_mice = []

    if runtype == 'pilot':
        omit_sess = [721038464] # alignment didn't work
        if stimtype == 'gabors':
            omit_mice = pilot_gab_omit(gabk)
        elif stimtype == 'bricks':
            omit_mice = pilot_bri_omit(bri_dir, bri_size)

    elif runtype == 'prod':
        omit_sess = [828754259] # stim pickle not saved correctly
        if stimtype == 'gabors': 
            if 16 not in gen_util.list_if_not(gabk):
                print(('The production data only includes gabor '
                       'stimuli with kappa=16'))
                omit_mice = list(range(1, 9)) # all
        elif stimtype == 'bricks':
            if 128 not in gen_util.list_if_not(bri_size):
                print(('The production data only includes bricks stimuli with '
                       'size=128'))
                omit_mice = list(range(1, 9)) # all

    return omit_sess, omit_mice


#############################################
def create_sess_dicts(mouse_df, datadir, runtype='prod', output='.'):
    """
    create_sess_dicts(mouse_df, datadir)

    Creates and saves dictionary containing information allowing basic session
    analysis without a sessions object, e.g. for logistic regression on 
    different gabor frames or surprise vs regular frames.

    Currently set to use only specific gabfr=0, gabk=16 and bri_size=128 
    values.

    Required args:
        - mouse_df (str): path name of dataframe containing information 
                          on each session
        - datadir (str) : directory where sessions are stored
                        
    Optional args:
        - runtype (str): the type of run, either 'pilot' or 'prod'
                         default: 'prod' 
        - output (str) : output directory
                         default: '.'
    """

    bri_size = 128
    gabk = 16
    gabfr = 0
    gabfr_let = sess_str_util.gabfr_letters(gabfr)
    
    # list of sessions that fit the parameter criteria for each stim type
    stimtypes = ['gabors', 'bricks', 'bricks']
    direcs    = ['', 'right', 'left']
    sessids   = [[], [], []]

    for stim, sublist, direc in zip(stimtypes, sessids, direcs):
        omit_sess, omit_mice = all_omit(stim, runtype, direc, bri_size, gabk)
        sublist.extend(get_sess_vals(mouse_df, 'sessid', runtype=runtype, 
                                     omit_mice=omit_mice, omit_sess=omit_sess))

    all_sessids = sorted(set([sessid for subl in sessids for sessid in subl]))
    
    sessions = init_sessions(all_sessids, datadir, mouse_df, runtype, 
                             fulldict=False)
    for sess in sessions:
        name = 'sess_dict_m{}_s{}_{}'.format(sess.mouse_n, sess.sess_n, 
                                             sess.layer)
        print('\nCreating stimulus dictionary: {}'.format(name))

        # get ROI traces path
        full_trs = [sess.roi_traces, sess.roi_traces_dff]
        for i in range(len(full_trs)):
            if 'mouse' in full_trs[i]:
                full_trs[i] = full_trs[i][full_trs[i].find('mouse'):]
            else:
                full_trs[i] = full_trs[i][full_trs[i].find('ophys_s'):]
        roi_tr_dir, roi_dff_dir = full_trs

        sess_dict = {'mouse_n'       : sess.mouse_n,
                     'mouseid'       : sess.mouseid,
                     'sess_n'        : sess.sess_n,
                     'sessid'        : sess.sessid,
                     'line'          : sess.line,
                     'layer'         : sess.layer,
                     'nrois'         : sess.nrois,
                     'twop_fps'      : sess.twop_fps,
                     'nanrois'       : sess.nanrois,
                     'nanrois_dff'   : sess.nanrois_dff,
                     'traces_dir'    : roi_tr_dir,
                     'dff_traces_dir': roi_dff_dir,
                     'gabk'          : gabk,
                     'gab_fr'        : [gabfr, gabfr_let], # e.g., [0, A]
                     'bri_size'      : bri_size
                    }

        for stimtype, direc, stim_sessids in zip(stimtypes, direcs, sessids):
            if stimtype == 'gabors':
                key  = 'gab'
                sep  = ''
            elif stimtype == 'bricks':
                key = 'bri_{}'.format(direc)
                sep = ' '
            if sess.sessid not in stim_sessids:
                print(('    {}{}{} surprise indices and frames '
                       'omitted.').format(stimtype, sep, direc))
                continue
            
            stim = sess.get_stim(stimtype)
            segs = stim.get_segs_by_criteria(gabk=gabk, gabfr=gabfr, 
                                             bri_dir=direc, bri_size=bri_size, 
                                             by='seg')
            frames = stim.get_twop_fr_by_seg(segs, first=True)

            surp_segs = stim.get_segs_by_criteria(gabk=gabk, gabfr=gabfr, 
                                                  bri_dir=direc, 
                                                  bri_size=bri_size, surp=1, 
                                                  by='seg')
            surp_idx = [segs.index(surp_seg) for surp_seg in surp_segs]

            frames_key   = '{}_frames'.format(key)
            surp_idx_key = '{}_surp_idx'.format(key)
            sess_dict[frames_key]   = frames.tolist()
            sess_dict[surp_idx_key] = surp_idx

        stim_dict_dir = os.path.join(output, 'session_dicts', runtype)
        file_util.saveinfo(sess_dict, name, stim_dict_dir, 'json')


#############################################
def get_analysdir(mouse_n, sess_n, layer, fluor='dff', scale=True, 
                  stimtype='gabors', bri_dir='right', bri_size=128, gabk=16, 
                  comp='surp', shuffle=False):
    """
    get_analysdir(mouse_n, sess_n, layer)

    Generates the name of the general directory in which an analysis type is
    saved, based on analysis parameters.
    
    Required arguments:
        - mouse_n (int): mouse number
        - sess_n (int) : session number
        - layer (str)  : layer name

    Optional arguments:
        - fluor (str)           : fluorescence trace type
                                  default: 'dff'
        - scale (str or bool)   : if scaling is used or type of scaling used 
                                  (e.g., 'roi', 'all', 'none')
                                  default: None
        - stimtype (str)        : stimulus type
                                  default: 'gabors'
        - bri_dir (str)         : brick direction
                                  default: 'right'
        - bri_size (int or list): brick size values to include
                                  (128, 256, [128, 256])
        - gabk (int or list)    : gabor kappa values to include 
                                  (4, 16 or [4, 16])        
        - comp (str)            : type of comparison
                                  default: 'surp'
        - shuffle (bool)        : whether analysis is on shuffled data
                                  default: False

    Returns:
        - analysdir (str): name of directory to save analysis in, of the form:
                           'm{}_s{}_layer_stimtype_fluor_scaled_comp_shuffled'
    """

    stim_str = sess_str_util.stim_par_str(stimtype, bri_dir, bri_size, gabk, 
                                          'file')

    scale_str = sess_str_util.scale_par_str(scale)
    shuff_str = sess_str_util.shuff_par_str(shuffle)
    if comp is None:
        comp_str = ''
    else:
        comp_str = '_{}'.format(comp)

    analysdir = 'm{}_s{}_{}_{}_{}{}{}{}'.format(mouse_n, sess_n, layer, 
                                                stim_str, fluor, scale_str, 
                                                comp_str, shuff_str)

    return analysdir


#############################################
def get_params_from_str(param_str):
    """
    get_params_from_str(param_str)

    Returns parameter information extracted from the parameter string.

    Required args:
        - param_str (str): String containing parameter information, of the form
                           'm{}_s{}_layer_stimtype_fluor_scaled_comp_shuffled',
                           though the order can be different as of layer
    
    Returns:
        - params (dict): parameter dictionary
            - bri_dir (str or list) : Bricks direction parameter ('right', 
                                      'left', ['right', 'left'] or 'none') 
            - bri_size (int or list): Bricks size parameter (128, 256, 
                                      [128, 256] or 'none')
            - comp (str)            : comparison parameter ('surp', 'AvB',
                                      'AvC', 'BvC' or 'DvE', None)
            - fluor (str)           : fluorescence parameter ('raw' or 'dff')
            - gabk (int or list)    : Gabor kappa parameter (4, 16, [4, 16] or 
                                      'none')
            - layer (str)           : layer ('soma' or 'dend')
            - mouse_n (int)         : mouse number
            - sess_n (int)          : session number
            - scale (bool)          : scaling parameter
            - shuffle (bool)        : shuffle parameter
            - stimtype (str)        : stimulus type ('gabors' or 'bricks')
    """

    params = dict()

    params['mouse_n'] = int(param_str.split('_')[0][1:])
    params['sess_n']  = int(param_str.split('_')[1][1:])

    [params['bri_dir'], params['bri_size'], 
                             params['gabk']] = 'none', 'none', 'none'
    if 'gab' in param_str:
        params['stimtype'] = 'gabors'
        params['gabk'] = 16
        if 'both' in param_str:
            params['gabk'] = [4, 16]
        elif 'gab4' in param_str:
            params['gabk'] = 4
    elif 'bri' in param_str:
        params['stimtype'] = 'bricks'
        params['bri_size'] = 128
        if 'both' in param_str:
            params['bri_size'] = [128, 256]
        elif 'bri256' in param_str:
            params['bri_size'] = 256
        params['bri_dir'] = ['right', 'left']
        if 'right' in param_str:
            params['bri_dir'] = 'right'
        elif 'left' in param_str:
            params['bri_dir'] = 'left'
    else:
        raise ValueError('Stimtype not identified.')

    if 'soma' in param_str:
        params['layer'] = 'soma'
    elif 'dend' in param_str:
        params['layer'] = 'dend'
    else:
        raise ValueError('Layer not identified.')

    if 'dff' in param_str:
        params['fluor'] = 'dff'
    elif 'raw' in param_str:
        params['fluor'] = 'raw'
    else:
        raise ValueError('Fluorescence type not identified.')

    params['scale'] = False
    if 'scale' in param_str:
        params['scale'] = True

    params['comp'] = None
    for comptype in ['surp', 'AvB', 'AvC', 'BvC', 'DvE']:
        if comptype in param_str:
            params['comp'] = comptype

    if 'shuffled' in param_str:
        params['shuffle'] = True
    else:
        params['shuffle'] = False

    return params

