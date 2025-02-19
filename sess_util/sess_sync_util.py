"""
sess_sync_util.py

This module contains functions for synchronizing the different data files 
generated by the Allen Institute OpenScope experiments for the Credit 
Assignment Project.

Authors: Allen Brain Institute, Joel Zylberberg, Blake Richards, Colleen Gillon

Date: August, 2018

Note: this code uses python 3.7.

"""

import logging
import warnings

import h5py
import numpy as np
import pandas as pd
import pynwb
from scipy import stats as scist
from allensdk.brain_observatory import sync_dataset, sync_utilities
from allensdk.brain_observatory.extract_running_speed import __main__ as running_main
from allensdk.internal.brain_observatory.eye_calibration import CM_PER_PIXEL

from util import file_util, gen_util, logger_util
from sess_util import Dataset2p, sess_file_util

logger = logging.getLogger(__name__)

SKIP_LAST_ELEMENT = -1
TAB = "    "

# from https://allensdk.readthedocs.io/en/latest/_modules/allensdk/brain_observatory/behavior/running_processing.html
WHEEL_RADIUS = 6.5 * 2.54 / 2 # diameter in inches to radius in cm
SUBJECT_POSITION = 2 / 3

# pupil in pixels
MM_PER_PIXEL = CM_PER_PIXEL * 10

# for some sessions, the second alignment is needed to adjust the first, as it 
# is robust to a 2p dropped frame bug that occurred before the stimulus started.
ADJUST_SECOND_ALIGNMENT = [833704570]


#### ALWAYS SET TO FALSE - CHANGE ONLY FOR TESTING PURPOSES
TEST_RUNNING_BLIPS = False


#############################################
def get_frame_timestamps_nwb(sess_files):
    """
    get_frame_timestamps_nwb(sess_files)

    Returns time stamps for stimulus and two-photon frames.

    Required args:
        - sess_files (Path): full path names of the session files

    Returns:
        - stim_timestamps (1D array): time stamp for each stimulus frame
        - twop_timestamps (1D array): time stamp for each two-photon frame
    """

    behav_file = sess_file_util.select_nwb_sess_path(sess_files, behav=True)

    use_ophys = False
    with pynwb.NWBHDF5IO(str(behav_file), "r") as f:
        nwbfile_in = f.read()
        behav_module = nwbfile_in.get_processing_module("behavior")
        main_field = "BehavioralTimeSeries"
        data_field = "running_velocity"
        try:
            run_time_series = behav_module.get_data_interface(
                main_field).get_timeseries(data_field)
        except KeyError as err:
            raise KeyError(
                "Could not find running velocity data in behavioral time "
                f"series for {behav_module} due to: {err}"
                )

        stim_timestamps = np.asarray(run_time_series.timestamps)

        main_field = "PupilTracking"
        data_field = "pupil_diameter"
        try:
            twop_timestamps = np.asarray(behav_module.get_data_interface(
                main_field).get_timeseries(data_field).timestamps)
        except KeyError as err:
            use_ophys = True            

    # if timestamps weren't found with pupil data, look for optical physiology 
    # data
    if use_ophys:
        ophys_file = sess_file_util.select_nwb_sess_path(sess_files, ophys=True)

        with pynwb.NWBHDF5IO(str(ophys_file), "r") as f:
            nwbfile_in = f.read()
            ophys_module = nwbfile_in.get_processing_module("ophys")
            main_field = "DfOverF"
            data_field = "RoiResponseSeries"
            try:
                roi_resp_series = ophys_module.get_data_interface(
                    main_field).get_roi_response_series(data_field
                    )
            except KeyError:
                file_str = f"{behav_file} or {ophys_file}"
                if behav_file == ophys_file:
                    file_str = behav_file
                raise OSError(
                    "Two-photon timestamps cannot be collected, as no "
                    f"pupil or ROI series data was found in {file_str}."
                    )
            twop_timestamps = roi_resp_series.timestamps
    

    return stim_timestamps, twop_timestamps


#############################################
def check_stim_drop_tolerance(n_drop_stim_fr, tot_stim_fr, drop_tol=0.0003, 
                              sessid=None, raise_exc=False):
    """
    check_stim_drop_tolerance(n_drop_stim_fr, tot_stim_fr)

    Logs a warning or raises an exception if dropped stimulus frames 
    tolerance is passed.

    Required args:
        - n_drop_stim_fr (int): number of dropped stimulus frames
        - tot_stim_fr (int)   : total number of stimulus frames

    Optional args:
        - drop_tol (float): threshold proportion of dropped stimulus frames at 
                            which to log warning or raise an exception.
                            default: 0.0003
        - sessid (int)    : session ID to include in the log or error
                            default: None 
        - raise_exc (bool): if True, an exception is raised if threshold is 
                            passed. Otherwise, a warning is logged.
                            default: False
    """

    sessstr = "" if sessid is None else f"Session {sessid}: "

    prop = np.float(n_drop_stim_fr) / tot_stim_fr
    if prop > drop_tol:
        warn_str = (f"{sessstr}{n_drop_stim_fr} dropped stimulus frames "
            f"(~{prop * 100:.1f}%).")
        if raise_exc:
            raise OSError(warn_str)
        else:    
            logger.warning(f"{warn_str}", extra={"spacing": TAB})


#############################################
def get_monitor_delay(stim_sync_h5):
    """
    get_monitor_delay(stim_sync_h5)

    Returns monitor delay lag.

    Required args:
        - stim_sync_h5 (Path): full path name of the experiment sync hdf5 
                               file
    """

    # check if exists
    file_util.checkfile(stim_sync_h5)

    # create Dataset2p object which allows delay to be calculated
    monitor_display_lag = Dataset2p.Dataset2p(str(stim_sync_h5)).display_lag

    return monitor_display_lag


#############################################
def get_vsync_falls(stim_sync_h5):
    """
    get_vsync_falls(stim_sync_h5)

    Calculates vsyncs for 2p and stimulus frames. 

    Required args:
        - stim_sync_h5 (Path): full path name of the experiment sync hdf5 
                               file

    Returns:
        - stim_vsync_fall_adj (1D array)  : vsyncs for each stimulus frame, 
                                            adjusted by monitor delay
        - valid_twop_vsync_fall (1D array): vsyncs for each 2p frame
    """

    # check that the sync file exists
    file_util.checkfile(stim_sync_h5)

    # create a Dataset object with the sync file 
    # (ignore deprecated keys warning)
    with gen_util.TempWarningFilter("The loaded sync file", UserWarning):
        sync_data = sync_dataset.Dataset(str(stim_sync_h5))
   
    sample_frequency = sync_data.meta_data["ni_daq"]["counter_output_freq"]
    
    # calculate the valid twop_vsync fall
    valid_twop_vsync_fall = Dataset2p.calculate_valid_twop_vsync_fall(
        sync_data, sample_frequency)

    # get the stim_vsync_fall
    stim_vsync_fall = Dataset2p.calculate_stim_vsync_fall(
        sync_data, sample_frequency)

    # find the delay
    # delay = calculate_delay(sync_data, stim_vsync_fall, sample_frequency)
    delay = get_monitor_delay(stim_sync_h5)

    # adjust stimulus time with monitor delay
    stim_vsync_fall_adj = stim_vsync_fall + delay

    return stim_vsync_fall_adj, valid_twop_vsync_fall


#############################################
def get_frame_rate(stim_sync_h5):
    """
    get_frame_rate(stim_sync_h5)

    Pulls out the ophys frame times stimulus sync file and returns stats for
    ophys frame rates.

    Required args:
        - stim_sync_h5 (Path): full path name of the experiment sync hdf5 
                               file

    Returns:
        - twop_rate_mean (num)  : mean ophys frame rate
        - twop_rate_med (num)   : median ophys frame rate
        - twop_rate_std (num)   : standard deviation of ophys frame rate
    """

    _, valid_twop_vsync_fall = get_vsync_falls(stim_sync_h5)

    twop_diff = np.diff(valid_twop_vsync_fall)
    
    twop_rate_mean = np.mean(1./twop_diff)
    twop_rate_med = np.median(1./twop_diff)
    twop_rate_std = np.std(1./twop_diff)
    
    return twop_rate_mean, twop_rate_med, twop_rate_std


#############################################
def get_stim_fr_timestamps(stim_sync_h5, time_sync_h5=None, stim_align=None):
    """
    get_stim_fr_timestamps(stim_sync_h5)

    Returns time stamps for stimulus frames, optionally adjusted to experiment 
    start, recorded in 2-photon imaging timestamps.

    Adapted from allensdk.brain_observatory.running_processing.__main__.main().

    Required args:
        - stim_sync_h5 (Path): full path name of the stimulus sync h5 file

    Optional args:
        - time_sync_h5 (Path)  : full path to the time synchronization hdf5 
                                 file, used to adjust stimulus frame timestamps 
                                 to experiment start
                                 default: None
        - stim_align (1D array): stimulus to 2p alignment array, used to adjust 
                                 stimulus frame timestamps to experiment start
                                 default: None

    Returns:
        - stim_fr_timestamps (1D array): time stamp for each stimulus frame 
                                         (seconds)
    """

    # check that the sync file exists
    file_util.checkfile(stim_sync_h5)

    dataset = sync_dataset.Dataset(str(stim_sync_h5))

    # Why the rising edge? See Sweepstim.update in camstim. This method does:
    # 1. updates the stimuli
    # 2. updates the "items", causing a running speed sample to be acquired
    # 3. sets the vsync line high
    # 4. flips the buffer
    stim_fr_timestamps = dataset.get_edges(
        "rising", sync_dataset.Dataset.FRAME_KEYS, units="seconds"
    )

    if time_sync_h5 is not None or stim_align is not None:
        if time_sync_h5 is None or stim_align is None:
            raise ValueError(
                "If providing time_sync_h5 or stim_align, must provide both."
                )
        stim_fr_timestamps = stim_fr_timestamps - stim_fr_timestamps[0]
        with h5py.File(time_sync_h5, "r") as f:
            twop_timestamps = f["twop_vsync_fall"][:]
        
        # Convert to the two photon reference frame
        offset = twop_timestamps[stim_align[0]]
        stim_fr_timestamps = offset + stim_fr_timestamps

    return stim_fr_timestamps


#############################################
def get_stim_frames(pkl_file_name, stim_sync_h5, time_sync_h5, df_pkl_name, 
                    sessid, runtype="prod"):
    """
    get_stim_frames(pkl_file_name, stim_sync_h5, time_sync_h5, df_pkl_name, 
                    sessid)

    Pulls out the stimulus frame information from the stimulus pickle file, as
    well as synchronization information from the stimulus sync file, and stores
    synchronized stimulus frame information in the output pickle file along 
	with the stimulus alignment array.

    Required args:
        - pkl_file_name (Path): full path name of the experiment stim pickle 
                                file
        - stim_sync_h5 (Path): full path name of the experiment sync hdf5 file
        - time_sync_h5 (Path) : full path to the time synchronization hdf5 file
        - df_pkl_name (Path)  : full path name of the output pickle file to 
                                create
        - sessid (int)       : session ID, needed the check whether this session 
                               needs to be treated differently (e.g., for 
                               alignment bugs)

    Optional argument:
        - runtype (str)  : the type of run, either "pilot" or "prod"
                           default: "prod"
    """


    # read the pickle file and call it "pkl"
    if isinstance(pkl_file_name, dict):
        pkl = pkl_file_name
    else:
        # check that the pickle file exists
        file_util.checkfile(pkl_file_name)
        pkl = file_util.loadfile(pkl_file_name, filetype="pickle")

    if runtype == "pilot":
        num_stimtypes = 2 # visual flow (bricks) and Gabors
    elif runtype == "prod":
        num_stimtypes = 3 # 2 visual flow (bricks) and 1 set of Gabors
    if len(pkl["stimuli"]) != num_stimtypes:
        raise ValueError(
            f"{num_stimtypes} stimuli types expected, but "
            f"{len(pkl['stimuli'])} found.")
        
    # get dataset object, sample frequency and vsyncs
    stim_vsync_fall_adj, valid_twop_vsync_fall = get_vsync_falls(stim_sync_h5)

    # calculate the alignment
    stimulus_alignment = Dataset2p.calculate_stimulus_alignment(
        stim_vsync_fall_adj, valid_twop_vsync_fall)

    # get the second stimulus alignment
    from sess_util import sess_load_util
    second_stimulus_alignment = sess_load_util.load_beh_sync_h5_data(
        time_sync_h5)[2]
    
    if len(second_stimulus_alignment) == len(stimulus_alignment) + 1:
        second_stimulus_alignment = second_stimulus_alignment[:-1]

    if int(sessid) in ADJUST_SECOND_ALIGNMENT:
        diff = second_stimulus_alignment - stimulus_alignment
        adjustment = scist.mode(diff)[0][0] # most frequent difference
        stimulus_alignment += adjustment

    # compare alignments
    compare_alignments(stimulus_alignment, second_stimulus_alignment)

    offset = int(pkl["pre_blank_sec"] * pkl["fps"])
    
    logger.info("Creating the stim_df:")
    
    # get number of segments expected and actually recorded for each stimulus
    segs = []
    segs_exp = []
    frames_per_seg = []
    stim_types = []
    stim_type_names = []
    
    for i in range(num_stimtypes):
        # records the max num of segs in the frame list for each stimulus
        segs.extend([np.max(pkl["stimuli"][i]["frame_list"])+1])
        
        # calculates the expected number of segs based on fps, 
        # display duration (s) and seg length
        fps = pkl["stimuli"][i]["fps"]
        
        if runtype == "pilot":
            name = pkl["stimuli"][i]["stimParams"]["elemParams"]["name"]
        elif runtype == "prod":
            name = pkl["stimuli"][i]["stim_params"]["elemParams"]["name"]

        stim_type_names.extend([name])
        stim_types.extend([name[0]])
        if name == "bricks":
            frames_per_seg.extend([fps])
            segs_exp.extend([int(60.*np.sum(np.diff(
                pkl["stimuli"][i]["display_sequence"]))/frames_per_seg[i])])
        elif name == "gabors":
            frames_per_seg.extend([fps/1000.*300])
            # to exclude grey seg
            segs_exp.extend([int(60.*np.sum(np.diff(
                pkl["stimuli"][i]["display_sequence"])
                )/frames_per_seg[i]*4./5)]) 
        else:
            raise ValueError(f"{name} stimulus type not recognized.")
        
        # check whether the actual number of frames is within a small range of 
        # expected about two frames per sequence?
        n_seq = pkl["stimuli"][0]["display_sequence"].shape[0] * 2
        if np.abs(segs[i] - segs_exp[i]) > n_seq:
            raise ValueError(f"Expected {segs_exp[i]} frames for stimulus {i}, "
                f"but found {segs[i]}.")
    
    total_stimsegs = np.sum(segs)
    
    stim_df = pd.DataFrame(index=list(range(np.sum(total_stimsegs))), 
        columns=["stimType", "stimPar1", "stimPar2", "surp", "stimSeg", 
        "GABORFRAME", "start_frame", "end_frame", "num_frames"])
    
    zz = 0
    # For gray-screen pre_blank
    stim_df.loc[zz, "stimType"] = -1
    stim_df.loc[zz, "stimPar1"] = -1
    stim_df.loc[zz, "stimPar2"] = -1
    stim_df.loc[zz, "surp"] = -1
    stim_df.loc[zz, "stimSeg"] = -1
    stim_df.loc[zz, "GABORFRAME"] = -1
    stim_df.loc[zz, "start_frame"] = stimulus_alignment[0] # 2p start frame
    stim_df.loc[zz, "end_frame"] = stimulus_alignment[offset] # 2p end frame
    stim_df.loc[zz, "num_frames"] = \
        (stimulus_alignment[offset] - stimulus_alignment[0])
    zz += 1

    for stype_n in range(num_stimtypes):
        logger.info(f"Stimtype: {stim_type_names[stype_n]}", 
            extra={"spacing": TAB})
        movie_segs = pkl["stimuli"][stype_n]["frame_list"]

        for segment in range(segs[stype_n]):
            seg_inds = np.where(movie_segs == segment)[0]
            tup = (segment, int(stimulus_alignment[seg_inds[0] + offset]), \
                int(stimulus_alignment[seg_inds[-1] + 1 + offset]))

            stim_df.loc[zz, "stimType"] = stim_types[stype_n][0]
            stim_df.loc[zz, "stimSeg"] = segment
            stim_df.loc[zz, "start_frame"] = tup[1]
            stim_df.loc[zz, "end_frame"] = tup[2]
            stim_df.loc[zz, "num_frames"] = tup[2] - tup[1]

            get_seg_params(
                stim_types, stype_n, stim_df, zz, pkl, segment, runtype)

            zz += 1
            
    # check whether any 2P frames are in associated to 2 stimuli
    overlap = np.any((np.sort(stim_df["start_frame"])[1:] - 
                     np.sort(stim_df["end_frame"])[:-1]) < 0)
    if overlap:
        raise ValueError("Some 2P frames associated with two stimulus "
            "segments.")
	
    # create a dictionary for pickling
    stim_dict = {"stim_df": stim_df, "stim_align": stimulus_alignment}   
 
    # store in the pickle file
    try:
        file_util.saveinfo(stim_dict, df_pkl_name, overwrite=True)
    except:
        raise OSError(f"Could not save stimulus pickle file {df_pkl_name}")  


#############################################
def get_seg_params(stim_types, stype_n, stim_df, zz, pkl, segment, 
                   runtype="prod"):
    """
    get_seg_params(stim_types, stype_n, stim_df, zz, pkl, segment)

    Populates the parameter columns for a segment in stim_df depending on 
    whether the segment is from a visual flow or gabors stimulus block and 
    whether it is a pilot or production session.

    Required args:
        - stim_types (list): list of stimulus types for each stimulus, 
                             e.g., ["b", "g"]
        - stype_n (int)    : stimulus number
        - stim_df (pd df)  : dataframe 
        - zz (int)         : dataframe index
        - pkl (dict)       : experiment stim dictionary
        - segment (int)    : segment number
    
    Optional argument:
        - runtype (str): run type, i.e., "pilot" or "prod"
                         default: "prod"
    """

    if stim_types[stype_n] == "b":
        if runtype == "pilot":
            #big or small
            stim_df.loc[zz, "stimPar1"] = pkl["stimuli"][stype_n][
                "stimParams"]["subj_params"]["flipdirecarray"][segment][1]
            #left or right
            stim_df.loc[zz, "stimPar2"] = pkl["stimuli"][stype_n][
                "stimParams"]["subj_params"]["flipdirecarray"][segment][3] 
            #SURP
            stim_df.loc[zz, "surp"] = pkl["stimuli"][stype_n][
                "stimParams"]["subj_params"]["flipdirecarray"][segment][0] 
        elif runtype == "prod":
            # small
            stim_df.loc[zz, "stimPar1"] = pkl["stimuli"][stype_n][
                "stim_params"]["elemParams"]["sizes"]
            # L or R
            stim_df.loc[zz, "stimPar2"] = pkl["stimuli"][stype_n][
                "stim_params"]["direc"]
            #SURP
            stim_df.loc[zz, "surp"] = pkl["stimuli"][stype_n][
                "sweep_params"]["Flip"][0][segment]
        stim_df.loc[zz, "GABORFRAME"] = -1
    elif stim_types[stype_n] == "g":
        if runtype == "pilot":
            #angle
            stim_df.loc[zz, "stimPar1"] = pkl["stimuli"][stype_n][
                "stimParams"]["subj_params"]["oriparsurps"][
                    int(np.floor(segment/4.))][0] 
            #angular disp (kappa)
            stim_df.loc[zz, "stimPar2"] = pkl["stimuli"][stype_n][
                "stimParams"]["subj_params"]["oriparsurps"][
                    int(np.floor(segment/4.))][1] 
            #SURP
            stim_df.loc[zz, "surp"] = pkl["stimuli"][stype_n][
                "stimParams"]["subj_params"]["oriparsurps"][
                    int(np.floor(segment/4.))][2] 
        elif runtype == "prod":
            #angle
            stim_df.loc[zz, "stimPar1"] = pkl["stimuli"][stype_n][
                "sweep_params"]["OriSurp"][0][int(np.floor(segment/4.))][0] 
            #angular disp (kappa)
            stim_df.loc[zz, "stimPar2"] = (1./(pkl["stimuli"][stype_n][
                "stim_params"]["gabor_params"]["ori_std"]))**2 
            #SURP
            stim_df.loc[zz, "surp"] = pkl["stimuli"][stype_n][
                "sweep_params"]["OriSurp"][0][int(np.floor(segment/4.))][1] 
        stim_df.loc[zz, "GABORFRAME"] = np.mod(segment,4)


#############################################
def calculate_running_velocity(stim_fr_timestamps, raw_running_deg, 
                               wheel_radius=WHEEL_RADIUS, 
                               subject_position=SUBJECT_POSITION, 
                               use_median_duration=False, filter_ks=5):
    """
    calculate_running_velocity(stim_fr_timestamps, raw_running_deg)

    Adapted from allensdk.brain_observatory.running_processing.__main__.extract_running_speeds().
    (Filtering of the linear velocity is added based on v1.8.0
    allensdk.brain_observatory.behavior.running_processing.get_running_df())
    Returns the linear running velocity at each frame, calculated from the raw 
    running distance at each frame.

    Required args:
        - stim_fr_timestamps (list): stimulus frame start timestamps
        - raw_running_deg (list)   : raw running data (change in wheel 
                                     orientation at each frame)

    Optional args:
        - wheel_radius (num)        : running wheel radius (cm)
                                      default: value of WHEEL_RADIUS module-wide 
                                      variable
        - subject_position (num)    : subject position relative from wheel 
                                      center, relative to wheel edge
                                      default: value of SUBJECT_POSITION 
                                      module-wide variable
        - use_median_duration (bool): if True, median frame duration is used 
                                      instead of each frame duration to 
                                      calculate angular velocity
                                      default: False
        - filter_ks (int)           : kernel size to use in median filtering 
                                      the linear running velocity 
                                      (0 to skip filtering).
                                      default: 5
    """

    # the first interval does not have a known start time, so we can't compute
    # an average velocity from raw_running_deg
    raw_running_rad = running_main.degrees_to_radians(raw_running_deg[1:])

    start_times = stim_fr_timestamps[:-1]
    end_times = stim_fr_timestamps[1:]

    durations = end_times - start_times
    if use_median_duration:
        angular_velocity = raw_running_rad / np.median(durations)
    else:
        angular_velocity = raw_running_rad / durations

    radius = wheel_radius * subject_position
    linear_velocity = running_main.angular_to_linear_velocity(
        angular_velocity, radius)

    # due to an acquisition bug, the raw orientations buffer may be read before 
    # it is updated, leading to values of 0 for the change in 
    # orientation (raw_running or raw_running_rad) over an interval. 
    linear_velocity[np.isclose(raw_running_rad, 0.0)] = np.nan

    if filter_ks != 0:
        # get rolling median, but for kernel windows where half or more values 
        # are NaNs, return NaNs
        min_vals_in_win = int(np.ceil((filter_ks + 1) / 2))
        linear_velocity = pd.Series(linear_velocity).rolling(
            window=filter_ks, min_periods=min_vals_in_win, center=True
            ).median().to_numpy()

    return linear_velocity


#############################################
def get_run_velocity(stim_sync_h5, stim_pkl="", stim_dict=None, filter_ks=5):
    """
    get_run_velocity(stim_sync_h5)

    Adapted from allensdk.brain_observatory.running_processing.__main__.main().
    Loads and calculates the linear running velocity from the raw running data.

    Required args:
        - stim_sync_h5 (Path): full path name of the stimulus sync h5 file

    Optional args:
        - stim_pkl (Path) : full path name of the experiment stim 
                            pickle file
                            default: ""
        - stim_dict (dict): stimulus dictionary, with keys "fps" and 
                            "items", from which running velocity is 
                            extracted.
                            If not None, overrides pkl_file_name.
                            default: None
        - filter_ks (int) : kernel size to use in median filtering the linear 
                            running velocity (0 to skip filtering).
                            default: 5

    Returns:
        - running_velocity (array): array of length equal to the number of 
                                    stimulus frames, each element corresponds 
                                    to the linear running velocity for that 
                                    stimulus frame
    """

    if stim_pkl == "" and stim_dict is None:
        raise ValueError("Must provide either the pickle file name or the "
                         "stimulus dictionary.")

    if stim_dict is None:
        # check that the pickle file exists
        file_util.checkfile(stim_pkl)

        # read the input pickle file and call it "pkl"
        stim_dict = file_util.loadfile(stim_pkl)

    stim_fr_timestamps = get_stim_fr_timestamps(stim_sync_h5)

    # occasionally an extra set of frame times are acquired after the rest of 
    # the signals. We detect and remove these
    stim_fr_timestamps = sync_utilities.trim_discontiguous_times(
        stim_fr_timestamps)
    num_raw_timestamps = len(stim_fr_timestamps)

    raw_running_deg = running_main.running_from_stim_file(
        stim_dict, "dx", num_raw_timestamps)

    if num_raw_timestamps != len(raw_running_deg):
        raise ValueError(
            f"found {num_raw_timestamps} rising edges on the vsync line, "
            f"but only {len(raw_running_deg)} rotation samples"
        )

    use_median_duration = False
    use_filter_ks = filter_ks

    # for running alignement test analyses
    if TEST_RUNNING_BLIPS:
        logger.warning("Pre-processing running data using median duration "
            "and no filter, for testing purposes.")
        use_median_duration = True
        use_filter_ks = 0

    running_velocity = calculate_running_velocity(
        stim_fr_timestamps=stim_fr_timestamps,
        raw_running_deg=raw_running_deg,
        wheel_radius=WHEEL_RADIUS,
        subject_position=SUBJECT_POSITION,
        use_median_duration=use_median_duration,
        filter_ks=use_filter_ks,
    )

    return running_velocity


#############################################
def get_twop2stimfr(stim2twopfr, n_twop_fr, sessid=None):
    """
    get_twop2stimfr(stim2twopfr, n_twop_fr)

    Old function.
    Returns the stimulus frame alignment for each 2p frame.
        
    Required args:
        - stim2twopfr (1D array): 2p frame numbers for each stimulus frame, 
                                    as well as the flanking
                                    blank screen frames 
        - n_twop_fr (int)       : total number of 2p frames

    Optional args:
        - sessid (int): session ID to include in the log or error
                        default: None 

    Returns:
        - twop2stimfr (1D array): Stimulus frame numbers for the beginning
                                  of each 2p frame (np.nan when no stimulus
                                  appears)
    """

    stim2twopfr_diff = np.append(1, np.diff(stim2twopfr))
    stim_idx = np.where(stim2twopfr_diff)[0]

    sessstr = "" if sessid is None else f"Session {sessid}: "

    dropped = np.where(stim2twopfr_diff > 1)[0]
    if len(dropped) > 0:
        logger.warning(f"{sessstr}{len(dropped)} dropped stimulus frames "
            "(2nd alignment).", extra={"spacing": TAB})
        # repeat stim idx when frame is dropped
        for drop in dropped[-1:]:
            loc = np.where(stim_idx == drop)[0][0]
            add = [stim_idx[loc-1]] * (stim2twopfr_diff[drop] - 1)
            stim_idx = np.insert(stim_idx, loc, add)
    
    twop2stimfr = np.full(n_twop_fr, np.nan) 
    start = int(stim2twopfr[0])
    end = int(stim2twopfr[-1]) + 1
    try:
        twop2stimfr[start:end] = stim_idx
    except:
        warnings.warn(f"{sessstr}get_twop2stimfr() not working for this "
            "session. twop2stimfr set to all NaNs.", category=RuntimeWarning, 
            stacklevel=1)

    return twop2stimfr


#############################################
def compare_alignments(alignment1, alignment2, tolerance=1, 
                       alignment_type="stim2twop"):
    """
    compare_alignments(alignment1, alignment2)

    Compares alignments and checks for differences above a tolerance threshold.

    Required args:
        - alignment1 (1D array): first alignment array 
        - alignment2 (1D array): second alignment array (same length) 

    Optional args:
        - tolerance (int)     : largest (absolute) disalignment to tolerate
                                default: 1
        - alignment_type (str): type of alignment being compared
                                default: "stim2twop"

    Returns:
        - twop2stimfr (1D array): Stimulus frame numbers for the beginning
                                  of each 2p frame (np.nan when no stimulus
                                  appears)
    """

    if len(alignment1) != len(alignment2):
        raise ValueError("'alignment1' and 'alignment2' must be of the same "
            "length.")

    alignment_diffs = alignment2 - alignment1

    alignment_diff_abs_max = np.max(np.absolute(alignment_diffs))
    n_alignment_diffs = \
        len(np.where(np.absolute(alignment_diffs) > tolerance)[0])

    if n_alignment_diffs:
        logger.warning(f"Comparing {alignment_type} alignments: "
            f"{n_alignment_diffs} frames show alignment differences "
            f"(> {tolerance}). The largest (absolute) misalignment "
            f"is a {alignment_diff_abs_max} frame difference.", 
            extra={"spacing": TAB})

