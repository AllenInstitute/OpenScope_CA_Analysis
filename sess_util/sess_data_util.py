"""
sess_data_util.py

This module contains functions for processing data generated by the Allen 
Institute OpenScope experiments for the Credit Assignment Project.

Authors: Colleen Gillon

Date: August, 2018

Note: this code uses python 3.7.

"""

import copy
import logging

import numpy as np

from util import data_util, gen_util, logger_util
from sess_util import sess_gen_util

logger = logging.getLogger(__name__)


#############################################
def get_stim_data(sess, stimtype, win_leng_s, gabfr=0, pre=0, post=1.5, 
                  unexp="any", step_size=1, gabk=16, run=True, run_mean=None, 
                  run_std=None):

    """
    get_stim_data(sess, stimtype, win_leng_s)

    Returns stimulus data (x position, y position, size, orientation, each 
    scaled based on its maximal range), and optionally running for windows 
    taken for the each of the segments of interest.

    Required args:
        - sess (Session)    : session
        - stimtype (str)    : stimulus type ("gabors"or "visflow")
        - win_leng_s (num)  : window length in seconds
    
    Optional args:
        - gabfr (int)             : gabor reference frame for determining the
                                    2p frames in each sequence
                                    default: 0 
        - pre (num)               : number of frames to include before reference
                                    gabor frame in each sequence (in sec)
                                    default: 0
        - post (num)              : number of frames to include after reference
                                    gabor frame in each sequence (in sec)
                                    default: 1.5
        - unexp (str, list or int): unexpected value criteria for including 
                                    reference gabor frames (0, 1, or "any")
                                    default: "any"
        - step_size (int)         : step size between windows
                                    default: 1
        - gabk (int or list)      : gabor kappa criteria for including reference
                                    gabor frames (4, 16 or "any")
                                    default: 16
        - run (bool)              : if True, running data is appended to the
                                    end of the stimulus data
                                    default: True
        - run_mean (num)          : mean value with which to scale running 
                                    data, if running data is included. If 
                                    run_mean or run_std is None, both are 
                                    calculated from the running data retrieved 
                                    and returned as outputs.
                                    default: None
        - run_std (num)           : standard deviation value with which to 
                                    scale running data, if running data is 
                                    included. If run_mean or run_std is None, 
                                    both are calculated from the running data 
                                    retrieved and returned as outputs.
                                    default: None
    
    Returns:
        - stim_wins (3D array): array of stimulus data, structured as:
                                seq wins x frames x pars, where the pars are:
                                    - for each gabor: x_pos, y_pos, size, ori 
                                    - run velocity
        if run and run_mean or run_std is None:
        - (list):
            - run_mean (num)  : mean of retrieved running values
            - run_std (num)   : standard deviation of retrieved running values

    """

    if win_leng_s > (pre + post):
        raise ValueError("Windows cannot be longer than the sequences.")

    stim = sess.get_stim(stimtype)

    segs = stim.get_segs_by_criteria(
        gabfr=gabfr, gabk=gabk, unexp=unexp, by="seg")
    twopfr = stim.get_fr_by_seg(segs, start=True, fr_type="twop")["start_frame_twop"]

    # get stim params in df with indices seg x frame x gabor x par 
    # (x, y, ori, size). Each param scaled to between -1 and 1 based on known 
    # ranges from which they were sampled
    pars_df = stim.get_stim_par_by_fr(twopfr, pre, post, scale=True, fr_type="twop")
    targ = [len(pars_df.index.unique(lev)) for lev in pars_df.index.names] + \
        [len(pars_df.columns.unique("parameters"))]
    targ[1] = -1 # 2p frame number is not repeated across sequences
    pars = pars_df.to_numpy().reshape(targ)

    if run:
        twop_fr_seqs = gen_util.reshape_df_data(
            sess.get_fr_ran(twopfr, pre, post, fr_type="twop"), 
            squeeze_cols=True)
        run_velocity = gen_util.reshape_df_data(
            sess.get_run_velocity_by_fr(
                twop_fr_seqs, remnans=True, scale=False), squeeze_cols=True)

        # scale running array to mean 0 with std 1
        ret_run_stats = False
        if run_mean is None or run_std is None:
            ret_run_stats = True
            run_mean = np.mean(run_velocity)
            run_std  = np.std(run_velocity)
        run_velocity = 2. * (run_velocity - run_mean)/run_std - 1.

    # stim params: seq x frame x flat (gab x pars)
    all_pars = pars.reshape([pars.shape[0], pars.shape[1], -1])
    if run:
        all_pars = np.concatenate(
            [all_pars, run_velocity[:, :, np.newaxis]], axis=2)
    
    win_leng = int(np.floor(win_leng_s * sess.twop_fps))

    stim_wins = []
    for seq_pars in all_pars:
        stim_wins.append(data_util.window_2d(
            seq_pars, win_leng, step_size=step_size))

    stim_wins = np.concatenate(stim_wins, axis=0).transpose([0, 2, 1])

    if run and ret_run_stats:
        return stim_wins, [run_mean, run_std]
    else:
        return stim_wins


#############################################
def get_roi_data(sess, stimtype, win_leng_s, gabfr=0, pre=0, post=1.5, 
                 unexp="any", step_size=1, gabk=16, roi_means=None, 
                 roi_stds=None):
    """
    get_roi_data(sess, stimtype, win_leng_s)

    Returns stimulus data (x position, y position, size, orientation, each 
    scaled based on its maximal range), and optionally running for windows 
    taken for the each of the segments of interest.

    Required args:
        - sess (Session)    : session
        - stimtype (str)    : stimulus type ("gabors"or "visflow")
        - win_leng_s (num)  : window length in seconds
    
    Optional args:
        - gabfr (int)             : gabor reference frame for determining the
                                    2p frames in each sequence
                                    default: 0 
        - pre (num)               : number of frames to include before reference
                                    gabor frame in each sequence (in sec)
                                    default: 0
        - post (num)              : number of frames to include after reference
                                    gabor frame in each sequence (in sec)
                                    default: 1.5
        - unexp (str, list or int): unexpected value criteria for including 
                                    reference gabor frames (0, 1, or "any")
                                    default: "any"
        - step_size (int)         : step size between windows
                                    default: 1
        - gabk (int or list)      : gabor kappa criteria for including reference
                                    gabor frames (4, 16 or "any")
                                    default: 16
        - roi_means (1D array)    : mean values for each ROI with which to 
                                    scale trace data. If roi_means or 
                                    roi_stds is None, both are calculated from 
                                    the trace data retrieved and returned as 
                                    outputs.
                                    default: None
        - roi_stds (1D array)     : standard deviation values for each ROI with 
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
        raise ValueError("Windows cannot be longer than the sequences.")

    stim = sess.get_stim(stimtype)

    segs = stim.get_segs_by_criteria(
        gabfr=gabfr, gabk=gabk, unexp=unexp, by="seg")
    twopfr = stim.get_fr_by_seg(segs, start=True, fr_type="twop")["start_frame_twop"]
    
    roi_data_df = stim.get_roi_data(twopfr, pre, post, remnans=True, 
        scale=False)
    ret_roi_stats = False
    xran = roi_data_df.index.unique("time_values").to_numpy()
    traces = gen_util.reshape_df_data(roi_data_df, squeeze_cols=True)

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
        trace_wins.append(data_util.window_2d(
            seq_traces, win_leng, step_size=step_size))
    # concatenate windows
    trace_wins = np.concatenate(trace_wins, axis=0).transpose([0, 2, 1])

    if ret_roi_stats:
        return xran, trace_wins, [roi_means, roi_stds]
    else:
        return xran, trace_wins


#############################################
def convert_to_binary_cols(df, col, vals, targ_vals):
    """
    convert_to_binary_cols(df, col, vals, targ_vals)

    Returns the input dataframe with the column values converted to categorical
    binary columns. The original column is dropped.

    Required args:
        - df (pd DataFrame): dataframe
        - col (str)        : column name
        - vals (list)      : ordered list of target values
        - targ_vals (list) : ordered list of target value names

    Returns:
        - df (pd DataFrame): dataframe with column values converted to 
                             categorical binary columns
    """

    uniq_vals = df[col].unique().tolist()    
    if not set(uniq_vals).issubset(set(vals)):
        raise ValueError(f"Unexpected values for {col}.")
    
    mapping = dict()
    for val in vals:
        mapping[val] = 0
    for val, targ in zip(vals, targ_vals):    
        col_name = f"{col}${targ}"
        this_mapping = copy.deepcopy(mapping)
        this_mapping[val] = 1
        df[col_name] = df[col].copy().replace(this_mapping)
    df = df.drop(columns=col)

    return df


#############################################
def get_mapping(par, act_vals=None):
    """
    get_mapping(par, act_vals)

    Returns a dictionary to map stimulus values to binary values.

    Required args:
        - par (str): stimulus parameter
        
    Optional args:
        - act_vals (list): actual list of values to double check against 
                           expected possible parameter values. If None, this
                           is not checked.
                           default: None

    Returns:
        - mapping (dict): value (between 0 and 1) for each parameter value
    """

    if par == "gabk":
        vals = [4, 16]
    elif par == "visflow_size":
        vals = [128, 256]
    elif par == "visflow_dir":
        vals = [sess_gen_util.get_visflow_screen_mouse_direc(direc) 
            for direc in ["right", "left"]]
    elif par == "line":
        vals = ["L23-Cux2", "L5-Rbp4"]
    elif par == "plane":
        vals = ["soma", "dend"]
    else:
        gen_util.accepted_values_error(
            "par", par, ["gabk", "visflow_size", "visflow_dir", "line", "plane"])
    
    if act_vals is not None:
        if not set(act_vals).issubset(set(vals)):
            vals_str = ", ".join(list(set(act_vals) - set(vals)))
            raise ValueError(f"Unexpected value(s) for {par}: {vals_str}")

    mapping = dict()
    for i, val in enumerate(vals):
        if val != i:
            mapping[val] = i

    return mapping


#############################################
def scale_data_df(data_df, datatype, interpolated="no", other_vals=[]):
    """
    scale_data_df(data_df, datatype)

    Returns data frame with specific column scaled using the factors
    found in the dataframe.

    Required args:
        - data_df (pd DataFrame): dataframe containing data for each frame, 
                                  organized by:
            hierarchical columns:
                - datatype    : type of data
                - interpolated: whether data is interpolated ("yes", "no")
                - scaled      : whether data is scaled ("yes", "no")
            hierarchical rows:
                - "info"      : type of information contained 
                                ("frames": values for each frame, 
                                "factors": scaling values for 
                                each factor)
                - "specific"  : specific type of information contained 
                                (frame number, scaling factor name)
        - datatype (str)        : datatype to be scaled

    Optional args:
        - interpolated (str): whether to scale interpolated data ("yes") 
                              or not ("no")
                              default: "no"
        - other_vals (list) : other values in the hierarchical dataframe to
                              copy to new column
                              default: []
    
    Returns:
        - data_df (pd DataFrame): same dataframe, but with scaled 
                                  data added
    """

    datatypes = data_df.columns.unique(level="datatype").tolist()

    if datatype not in datatypes:
        gen_util.accepted_values_error("datatype", datatype, datatypes)

    other_vals = gen_util.list_if_not(other_vals)

    if "yes" in data_df[datatype].columns.get_level_values(
        level="scaled"):
        logger.info("Data already scaled.")

    factor_names = data_df.loc["factors"].index.unique(
        level="specific").tolist()
    sub_names =  list(filter(lambda x: "sub" in x, factor_names))
    if len(sub_names) != 1:
        raise RuntimeError("Only one factor should contain 'sub'.")
    div_names =  list(filter(lambda x: "div" in x, factor_names))
    if len(div_names) != 1:
        raise RuntimeError("Only one row should contain 'div'.")

    sub = data_df.loc[("factors", sub_names[0])].values[0]
    div = data_df.loc[("factors", div_names[0])].values[0]

    data_df = data_df.copy(deep=True)

    data_df.loc[("frames",), (datatype, interpolated, "yes", *other_vals)] = \
        (data_df.loc[("frames",), 
        (datatype, interpolated, "no", *other_vals)].values - sub)/div

    return data_df


#############################################
def add_categ_stim_cols(df):
    """
    add_categ_stim_cols(df)

    Returns dataframe with categorical stimulus information split into binary 
    columns.

    Required args:
        - df (pd DataFrame): stimulus dataframe

    Returns:
        - df (pd DataFrame): stimulus dataframe with categorical stimulus 
                             information split into binary columns
    """

    for col in df.columns:
        if col == "gab_ori":
            vals = sess_gen_util.filter_gab_oris("ABCDUG")
            df = convert_to_binary_cols(df, col, vals, vals)
        elif col == "gabfr":
            vals = ["G", 0, 1, 2, 3]
            targ_vals = ["G", "A", "B", "C", "D"]
            df = convert_to_binary_cols(df, col, vals, targ_vals)
        elif col in ["gabk", "visflow_size", "visflow_dir", "plane", "line"]:
            uniq_vals = df[col].unique().tolist()
            mapping = get_mapping(col, uniq_vals)
            df = df.replace({col: mapping})
        elif col == "sessid":
            vals = df["sessid"].unique().tolist()
            df = convert_to_binary_cols(df, col, vals, vals)
        else:
            continue

    return df


#############################################
def format_stim_criteria(stim_df, stimtype="gabors", unexp="any", 
                         stim_seg="any", gabfr="any", gabk=None, gab_ori=None, 
                         visflow_size=None, visflow_dir=None, start2pfr="any", 
                         end2pfr="any", num2pfr="any"):
    """
    format_stim_criteria()

    Returns a list of stimulus parameters formatted correctly to use
    as criteria when searching through the stim dataframe. 

    Will strip any criteria not related to the relevant stimulus type.

    Required args:
        - stim_df (pd DataFrame)       : stimulus dataframe

    Optional args:
        - stimtype (str)               : stimulus type
                                            default: "gabors"
        - unexp (str, int or list)     : unexpected value(s) of interest (0, 1)
                                            default: "any"
        - stim_seg (str, int or list)  : stimulus segment value(s) of interest
                                            default: "any"
        - gabfr (str, int or list)     : gaborframe value(s) of interest 
                                            (0, 1, 2, 3, 4 or letters)
                                            default: "any"
        - gabk (int or list)           : if not None, will overwrite 
                                            stimPar2 (4, 16, or "any")
                                            default: None
        - gab_ori (int or list)        : if not None, will overwrite 
                                            stimPar1 (0, 45, 90, 135, 180, 225, 
                                            or "any")
                                            default: None
        - visflow_size (int or list)   : if not None, will overwrite 
                                            stimPar1 (128, 256, or "any")
                                            default: None
        - visflow_dir (str or list)    : if not None, will overwrite 
                                            stimPar2 ("right", "left", "temp", 
                                             "nasal", or "any")
                                            default: None
        - start2pfr (str or list)      : 2p start frames range of interest
                                            [min, max (excl)] 
                                            default: "any"
        - end2pfr (str or list)        : 2p excluded end frames range of 
                                            interest [min, max (excl)]
                                            default: "any"
        - num2pfr (str or list)        : 2p num frames range of interest
                                            [min, max (excl)]
                                            default: "any"
    
    Returns:
        - unexp (list)       : unexpected value(s) of interest (0, 1)
        - stim_seg (list)    : stim_seg value(s) of interest
        - gabfr (list)       : gaborframe value(s) of interest 
        - gabk (list)        : gabor kappa value(s) of interest 
        - gab_ori (list)     : gabor mean orientation value(s) of interest 
        - visflow_size (list): visual flow square size value(s) of interest 
        - visflow_dir (list) : visual flow direction value(s) of interest 
        - start2pfr_min (int): minimum of 2p start2pfr range of interest 
        - start2pfr_max (int): maximum of 2p start2pfr range of interest 
                                (excl)
        - end2pfr_min (int)  : minimum of 2p end2pfr range of interest
        - end2pfr_max (int)  : maximum of 2p end2pfr range of interest 
                                (excl)
        - num2pfr_min (int)  : minimum of num2pfr range of interest
        - num2pfr_max (int)  : maximum of num2pfr range of interest 
                                (excl)
    """

    # remove visual flow criteria for gabors and vv
    if stimtype == "gabors":
        visflow_size = None
        visflow_dir = None
    elif stimtype == "visflow":
        gabfr = None
        gabk = None
        gab_ori = None
    else:
        gen_util.accepted_values_error(
            "stimtype", stimtype, ["gabors", "visflow"])

    # converts values to lists or gets all possible values, if "any"
    unexp    = gen_util.get_df_label_vals(stim_df, "unexpected", unexp)    
    gabk     = gen_util.get_df_label_vals(stim_df, "gabor_kappa", gabk)
    gabfr    = gen_util.get_df_label_vals(stim_df, "gabor_frame", gabfr)
    gab_ori  = gen_util.get_df_label_vals(
        stim_df, "gabor_mean_orientation", gab_ori
        )
    visflow_dir = gen_util.get_df_label_vals(
        stim_df, "main_flow_direction", visflow_dir
        )
    visflow_size = gen_util.get_df_label_vals(
        stim_df, "square_size", visflow_size
        )

    if stim_seg in ["any", "all"]:
        stim_seg = stim_df.index
    else:
        stim_seg = gen_util.list_if_not(stim_seg)

    for fr in gabfr:
        if str(fr) == "0":
            gabfr.append("A")
        elif str(fr) == "1":
            gabfr.append("B")
        elif str(fr) == "2":
            gabfr.append("C")
        elif str(fr) == "3":
            gabfr.extend(["D", "U"])
        elif str(fr) == "4":
            gabfr.append("G")

    for i in range(len(visflow_dir)):
        if visflow_dir[i] in ["right", "left", "temp", "nasal"]:
            visflow_dir[i] = \
                sess_gen_util.get_visflow_screen_mouse_direc(
                    visflow_dir[i
                    ])

    if start2pfr in ["any", None]:
        start2pfr_min = int(stim_df["start_frame_twop"].min())
        start2pfr_max = int(stim_df["start_frame_twop"].max()+1)

    elif len(start2pfr) == 2:
        start2pfr_min, start2pfr_max = start2pfr
    else:
        raise ValueError("'start2pfr' must be of length 2 if passed.")

    if end2pfr in ["any", None]:
        end2pfr_min = int(stim_df["stop_frame_twop"].min())
        end2pfr_max = int(stim_df["stop_frame_twop"].max() + 1)
    elif len(start2pfr) == 2:
        end2pfr_min, end2pfr_max = end2pfr
    else:
        raise ValueError("'end2pfr' must be of length 2 if passed.")

    if num2pfr in ["any", None]:
        num2pfr_min = int(stim_df["num_frames_twop"].min())
        num2pfr_max = int(stim_df["num_frames_twop"].max() + 1)
    elif len(start2pfr) == 2:
        num2pfr_min, num2pfr_max = num2pfr
    else:
        raise ValueError("'num2pfr' must be of length 2 if passed.")

    return [unexp, stim_seg, gabfr, gabk, gab_ori, visflow_size, visflow_dir, 
        start2pfr_min, start2pfr_max, end2pfr_min, end2pfr_max, num2pfr_min, 
        num2pfr_max] 

