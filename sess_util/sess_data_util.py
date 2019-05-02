

import numpy as np

from util import data_util, gen_util


#############################################
def get_stim_data(sess, stimtype, win_leng_s, gabfr=0, pre=0, post=1.5, 
                  surp='any', step_size=1, gabk=16, run=True, run_mean=None, 
                  run_std=None):

    """
    get_stim_data(sess, stimtype, win_leng_s)

    Returns stimulus data (x position, y position, size, orientation, each 
    scaled based on its maximal range), and optionally running for windows 
    taken for the each of the segments of interest.

    Required args:
        - sess (Session)    : session
        - stimtype (str)    : stimulus type ('gabors'or 'bricks')
        - win_leng_s (float): window length in seconds
    
    Optional args:
        - gabfr (int)            : gabor reference frame for determining the
                                   2p frames in each sequence
                                   default: 0 
        - pre (float)            : number of frames to include before reference
                                   gabor frame in each sequence (in sec)
                                   default: 0
        - post (float)           : number of frames to include after reference
                                   gabor frame in each sequence (in sec)
                                   default: 1.5
        - surp (str, list or int): surprise value criteria for including 
                                   reference gabor frames (0, 1, or 'any')
                                   default: 'any'
        - step_size (int)        : step size between windows
                                   default: 1
        - gabk (int or list)     : gabor kappa criteria for including reference
                                   gabor frames (4, 16 or 'any')
                                   default: 16
        - run (bool)             : if True, running data is appended to the
                                   end of the stimulus data
                                   default: True
        - run_mean (float)       : mean value with which to scale running 
                                   data, if running data is included. If 
                                   run_mean or run_std is None, both are 
                                   calculated from the running data retrieved 
                                   and returned as outputs.
                                   default: None
        - run_std (float)        : standard deviation value with which to 
                                   scale running data, if running data is 
                                   included. If run_mean or run_std is None, 
                                   both are calculated from the running data 
                                   retrieved and returned as outputs.
                                   default: None
    
    Returns:
        - stim_wins (3D array): array of stimulus data, structured as:
                                seq wins x frames x pars, where the pars are:
                                    - for each gabor: x_pos, y_pos, size, ori 
                                    - run speed
        if run and run_mean or run_std is None:
        - (list):
            - run_mean (float): mean of retrieved running values
            - run_std (float) : standard deviation of retrieved running values

    """

    if win_leng_s > (pre + post):
        raise ValueError('Windows cannot be longer than the sequences.')

    stim = sess.get_stim(stimtype)

    segs = stim.get_segs_by_criteria(gabfr=gabfr, gabk=gabk, surp=surp, 
                                     by='seg')
    twopfr = stim.get_twop_fr_per_seg(segs, first=True)

    # get stim params as seq x frame x gabor x par (x, y, ori, size)
    # each param scaled to between -1 and 1 based on known ranges
    # from which they were sampled
    pars = stim.get_stim_par_by_twopfr(twopfr, pre, post, scale=True)
    pars = np.stack(pars).transpose([1, 2, 3, 0])

    if run:
        twop_fr_seqs = sess.get_twop_fr_ran(twopfr, pre, post)[0]
        run_speed = sess.get_run_speed(twop_fr_seqs)
        
        # scale running array to mean 0 with std 1
        ret_run_stats = False
        if run_mean is None or run_std is None:
            ret_run_stats = True
            run_mean = np.mean(run_speed)
            run_std  = np.std(run_speed)
        run_speed = 2. * (run_speed - run_mean)/run_std - 1.

    # stim params: seq x frame x flat (gab x pars)
    all_pars = pars.reshape([pars.shape[0], pars.shape[1], -1])
    if run:
        all_pars = np.concatenate([all_pars, run_speed[:, :, np.newaxis]], 
                                   axis=2)
    
    win_leng = int(np.floor(win_leng_s * sess.twop_fps))

    stim_wins = []
    for seq_pars in all_pars:
        stim_wins.append(data_util.window_2d(seq_pars, win_leng, 
                                             step_size=step_size))

    stim_wins = np.concatenate(stim_wins, axis=0).transpose([0, 2, 1])

    if run and ret_run_stats:
        return stim_wins, [run_mean, run_std]
    else:
        return stim_wins


#############################################
def get_roi_data(sess, stimtype, win_leng_s, gabfr=0, pre=0, post=1.5, 
                 surp='any', step_size=1, gabk=16, roi_means=None, 
                 roi_stds=None):
    """
    get_stim_data(sess, stimtype, win_leng_s)

    Returns stimulus data (x position, y position, size, orientation, each 
    scaled based on its maximal range), and optionally running for windows 
    taken for the each of the segments of interest.

    Required args:
        - sess (Session)    : session
        - stimtype (str)    : stimulus type ('gabors'or 'bricks')
        - win_leng_s (float): window length in seconds
    
    Optional args:
        - gabfr (int)            : gabor reference frame for determining the
                                   2p frames in each sequence
                                   default: 0 
        - pre (float)            : number of frames to include before reference
                                   gabor frame in each sequence (in sec)
                                   default: 0
        - post (float)           : number of frames to include after reference
                                   gabor frame in each sequence (in sec)
                                   default: 1.5
        - surp (str, list or int): surprise value criteria for including 
                                   reference gabor frames (0, 1, or 'any')
                                   default: 'any'
        - step_size (int)        : step size between windows
                                   default: 1
        - gabk (int or list)     : gabor kappa criteria for including reference
                                   gabor frames (4, 16 or 'any')
                                   default: 16
        - roi_means (1D array)   : mean values for each ROI with which to 
                                   scale trace data. If roi_means or 
                                   roi_stds is None, both are calculated from 
                                   the trace data retrieved and returned as 
                                   outputs.
                                   default: None
        - roi_stds (1D array)    : standard deviation values for each ROI with 
                                   which to scale trace data. If roi_means 
                                   or roi_stds is None, both are calculated 
                                   from the trace data retrieved and returned  
                                   as outputs.
                                   default: None
    
    Returns:
        - xran (1D array)      : time values for the 2p frames
        - trace_wins (3D array): array of ROI data, structured as:
                                 seq wins x frames x ROI
        if roi_means or roi_stds is None:
        - (list):
            - roi_means (1D array): trace means for each ROI
            - roi_stds (1D array) : trace standard deviations for each ROI

    """


    if win_leng_s > (pre + post):
        raise ValueError('Windows cannot be longer than the sequences.')

    stim = sess.get_stim(stimtype)

    segs = stim.get_segs_by_criteria(gabfr=gabfr, gabk=gabk, surp=surp, 
                                     by='seg')
    twopfr = stim.get_twop_fr_per_seg(segs, first=True)
    
    xran, traces = stim.get_roi_trace_array(twopfr, pre, post)
    ret_roi_stats = False

    # scale each ROI to mean 0, std 1
    if roi_means is None or roi_stds is None:
        ret_roi_stats = True
        roi_means = np.mean(traces.reshape(traces.shape[0], -1), axis=1)
        roi_stds  = np.std(traces.reshape(traces.shape[0], -1), axis=1)
    traces = 2. * (traces - roi_means.reshape([-1, 1, 1]))/ \
                  roi_stds.reshape([-1, 1, 1]) - 1.
    # traces: seq x frames x ROI
    traces = traces.transpose(1, 2, 0)

    trace_wins = []
    win_leng = int(np.floor(sess.twop_fps * win_leng_s))
    for seq_traces in traces:
        # n_wins x n_ROIs x win_leng
        trace_wins.append(data_util.window_2d(seq_traces, win_leng, 
                                              step_size=step_size))
    # concatenate windows
    trace_wins = np.concatenate(trace_wins, axis=0).transpose([0, 2, 1])

    if ret_roi_stats:
        return xran, trace_wins, [roi_means, roi_stds]
    else:
        return xran, trace_wins

