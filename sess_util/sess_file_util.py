"""
sess_file_util.py

This module contains functions for loading and reading from data 
files generated by the Allen Institute OpenScope experiments for the Credit 
Assignment Project.

Authors: Colleen Gillon, Blake Richards

Date: August, 2018

Note: this code uses python 3.7.

"""

import glob
from pathlib import Path
import warnings

from util import file_util, gen_util, logger_util


#############################################
def get_nwb_sess_paths(maindir, dandi_id, mouseid=None):
    """
    get_nwb_sess_paths(maindir, dandi_id)

    Returns a list of NWB session data path names for the DANDI Credit 
    Assignment session requested.

    Several files may be found if they contain different types of information 
    (e.g., behavior, image, ophys).
 
    Required arguments:
        - maindir (str) : path of the main data directory
        - dandi_id (str): DANDI ID (yyyymmddThhmmss digits)

    Optional arguments
        - mouseid (str) : mouse 6-digit ID string optionally used to check 
                          whether files are for the expected mouse number
                          e.g. "389778"

    Returns:
        - sess_files (list): full path names of the session files
    """

    if dandi_id is None:
        raise ValueError(
            "Dandi ID is None. Session may not exist in NWB version."
            )
    
    dandi_form = f"*ses-{dandi_id}*.nwb"
    if mouseid is not None:
        dandi_form = f"sub-{mouseid}_{dandi_form}"
    dandi_glob_path = Path(maindir, "**", dandi_form)
    sess_files = glob.glob(str(dandi_glob_path), recursive=True)

    if len(sess_files) == 0:
        raise RuntimeError(
            "Found no NWB sessions of the expected form "
            f"{dandi_form} under {maindir}."
            )

    else:
        sess_files = [Path(sess_file) for sess_file in sess_files]
        return sess_files


#############################################
def select_nwb_sess_path(sess_files, ophys=False, behav=False, stim=False, 
                         warn_multiple=False):
    """
    select_nwb_sess_path(sess_files)

    Returns an NWB session data path name, selected from a list according to 
    the specified criteria.
 
    Required arguments:
        - sess_files (list): full path names of the session files

    Optional arguments
        - ophys (bool)        : if True, only session files with optical 
                                physiology data are retained
                                default: False
        - behav (bool)        : if True, only session files with behaviour 
                                data are retained
                                default: False
        - stim (bool)         : if True, only session files with stimulus 
                                images are retained
                                default: False
        - warn_multiple (bool): if True, a warning if thrown if multiple 
                                matching session files are found
                                default: False

    Returns:
        - sess_file (Path): full path name of the selected session file
    """

    sess_files = gen_util.list_if_not(sess_files)
    
    criterion_dict = {
        "ophys"   : [ophys, "optical physiology"],
        "behavior": [behav, "behavioral"],
        "image"   : [stim, "stimulus"],        
        }

    data_names = []
    for data_str, [data_bool, data_name] in criterion_dict.items():
        if data_bool:
            sess_files = [
                sess_file for sess_file in sess_files 
                if data_str in str(sess_file)
            ]
            data_names.append(data_name)
    
    tog_str = "" if len(data_names) < 2 else " together"
    data_names = ", and ".join(data_names).lower()

    if len(sess_files) == 0:
        raise RuntimeError(
            f"{data_names} data not included{tog_str} in session NWB files."
            )
    
    sess_file = sess_files[0]
    if len(sess_files) > 1 and warn_multiple:
        data_names_str = f" with {data_names} data" if len(data_names) else ""
        warnings.warn(
            f"Several session files{data_names_str} found{tog_str}. "
            f"Using the first listed: {sess_file}."
            )

    return sess_file


#############################################
def get_sess_dirs(maindir, sessid, expid, segid, mouseid, runtype="prod",
                  mouse_dir=True, check=True):
    """
    get_sess_dirs(maindir, sessid, expid, segid, mouseid)

    Returns the full path names of the session directory and subdirectories for 
    the specified session and experiment on the given date that can be used for 
    the Credit Assignment analysis.

    Also checks existence of expected directories.
 
    Required arguments:
        - maindir (str): path of the main data directory
        - sessid (int) : session ID (9 digits)
        - expid (str)  : experiment ID (9 digits)
        - segid (str)  : segmentation ID (9 digits)
        - mouseid (str): mouse 6-digit ID string used for session files
                         e.g. "389778" 

    Optional arguments
        - runtype (str)   : "prod" (production) or "pilot" data
                            default: "prod"
        - mouse_dir (bool): if True, session information is in a "mouse_*"
                            subdirectory
                            default: True
        - check (bool)    : if True, checks whether the directories in the 
                            output dictionary exist
                            default: True

    Returns:
        - sessdir (Path) : full path name of the session directory
        - expdir (Path)  : full path name of the experiment directory
        - procdir (Path) : full path name of the processed 
                           data directory
        - demixdir (Path): full path name of the demixing data directory
        - segdir (Path)  : full path name of the segmentation directory
    """
    
    # get the name of the session and experiment data directories
    if mouse_dir:
        sessdir = Path(maindir, runtype, f"mouse_{mouseid}", 
            f"ophys_session_{sessid}")
    else:
        sessdir = Path(maindir, runtype, f"ophys_session_{sessid}")

    expdir   = Path(sessdir, f"ophys_experiment_{expid}")
    procdir  = Path(expdir, "processed")
    demixdir = Path(expdir, "demix")
    segdir   = Path(procdir, f"ophys_cell_segmentation_run_{segid}")

    # check that directory exists
    if check:
        try:
            file_util.checkdir(sessdir)
        except OSError as err:
            raise OSError(
                f"{sessdir} does not conform to expected OpenScope "
                f"structure: {err}."
                )

    return sessdir, expdir, procdir, demixdir, segdir


#############################################
def get_sess_dirs(maindir, sessid, expid, segid, mouseid, runtype="prod",
                  mouse_dir=True, check=True):
    """
    get_sess_dirs(maindir, sessid, expid, segid, mouseid)

    Returns the full path names of the session directory and subdirectories for 
    the specified session and experiment on the given date that can be used for 
    the Credit Assignment analysis.

    Also checks existence of expected directories.
 
    Required arguments:
        - maindir (str): path of the main data directory
        - sessid (int) : session ID (9 digits)
        - expid (str)  : experiment ID (9 digits)
        - segid (str)  : segmentation ID (9 digits)
        - mouseid (str): mouse 6-digit ID string used for session files
                         e.g. "389778" 

    Optional arguments
        - runtype (str)   : "prod" (production) or "pilot" data
                            default: "prod"
        - mouse_dir (bool): if True, session information is in a "mouse_*"
                            subdirectory
                            default: True
        - check (bool)    : if True, checks whether the directories in the 
                            output dictionary exist
                            default: True

    Returns:
        - sessdir (Path) : full path name of the session directory
        - expdir (Path)  : full path name of the experiment directory
        - procdir (Path) : full path name of the processed 
                           data directory
        - demixdir (Path): full path name of the demixing data directory
        - segdir (Path)  : full path name of the segmentation directory
    """
    
    # get the name of the session and experiment data directories
    if mouse_dir:
        sessdir = Path(maindir, runtype, f"mouse_{mouseid}", 
            f"ophys_session_{sessid}")
    else:
        sessdir = Path(maindir, runtype, f"ophys_session_{sessid}")

    expdir   = Path(sessdir, f"ophys_experiment_{expid}")
    procdir  = Path(expdir, "processed")
    demixdir = Path(expdir, "demix")
    segdir   = Path(procdir, f"ophys_cell_segmentation_run_{segid}")

    # check that directory exists
    if check:
        try:
            file_util.checkdir(sessdir)
        except OSError as err:
            raise OSError(
                f"{sessdir} does not conform to expected OpenScope "
                f"structure: {err}."
                )

    return sessdir, expdir, procdir, demixdir, segdir


#############################################
def get_file_names(maindir, sessid, expid, segid, date, mouseid, 
                   runtype="prod", mouse_dir=True, check=True):
    """
    get_file_names(maindir, sessionid, expid, date, mouseid)

    Returns the full path names of all of the expected data files in the 
    main directory for the specified session and experiment on the given date 
    that can be used for the Credit Assignment analysis.
 
    Required args:
        - maindir (Path): path of the main data directory
        - sessid (int)  : session ID (9 digits)
        - expid (str)   : experiment ID (9 digits)
        - segid (str)   : segmentation ID (9 digits)
        - date (str)    : date for the session in YYYYMMDD, e.g. "20160802"
        - mouseid (str) : mouse 6-digit ID string used for session files

    Optional args:
        - runtype (str)   : "prod" (production) or "pilot" data
                            default: "prod"
        - mouse_dir (bool): if True, session information is in a "mouse_*"
                            subdirectory
                            default: True
        - check (bool)    : if True, checks whether the files and directories 
                            in the output dictionaries exist (with a few 
                            exceptions)
                            default: True

    Returns:
        - dirpaths (dict): dictionary of directory paths
            ["expdir"] (Path)  : full path name of the experiment directory
            ["procdir"] (Path) : full path name of the processed directory
            ["demixdir"] (Path): full path name of the demixed directory
            ["segdir"] (Path)  : full path name of the segmentation directory
        - filepaths (dict): dictionary of file paths
            ["behav_video_h5"] (Path)    : full path name of the behavioral hdf5
                                           video file
            ["max_proj_png"] (Path)      : full path to max projection of stack
                                           in png format
            ["pupil_video_h5"] (Path)    : full path name of the pupil hdf5 
                                           video file
            ["roi_extract_json"] (Path)  : full path name of the ROI extraction 
                                           json
            ["roi_objectlist_txt"] (Path): full path to ROI object list txt
            ["stim_pkl"]  (Path)         : full path name of the stimulus
                                           pickle file
            ["stim_sync_h5"] (Path)      : full path name of the stimulus
                                           synchronization hdf5 file
            ["time_sync_h5"] (Path)      : full path name of the time 
                                           synchronization hdf5 file
            
            Existence not checked:
            ["align_pkl"] (Path)         : full path name of the stimulus
                                           alignment pickle file
            ["corrected_data_h5"] (Path) : full path name of the motion
                                           corrected 2p data hdf5 file
            ["roi_trace_h5"] (Path)      : full path name of the ROI raw 
                                           processed fluorescence trace hdf5 
                                           file (allen version)
            ["roi_trace_dff_h5"] (Path)  : full path name of the ROI dF/F trace 
                                           hdf5 file (allen version)
            ["zstack_h5"] (Path)         : full path name of the zstack 2p hdf5 
                                           file
    """
    
    sessdir, expdir, procdir, demixdir, segdir = get_sess_dirs(
        maindir, sessid, expid, segid, mouseid, runtype, mouse_dir, check)

    roi_trace_paths = get_roi_trace_paths(
        maindir, sessid, expid, segid, mouseid, runtype, mouse_dir, 
        dendritic=False, check=False) # will check below, if required

    # set the file names
    sess_m_d = f"{sessid}_{mouseid}_{date}"

    dirpaths = {"expdir"  : expdir,
                "procdir" : procdir,
                "segdir"  : segdir,
                "demixdir": demixdir
                }

    filepaths = {"align_pkl"         : Path(sessdir, f"{sess_m_d}_df.pkl"),
                 "behav_video_h5"    : Path(sessdir, f"{sess_m_d}_video-0.h5"),
                 "correct_data_h5"   : Path(procdir, "concat_31Hz_0.h5"),
                 "max_proj_png"      : Path(procdir, 
                                       "max_downsample_4Hz_0.png"),
                 "pupil_video_h5"    : Path(sessdir, f"{sess_m_d}_video-1.h5"),
                 "roi_extract_json"  : Path(procdir, 
                                       f"{expid}_input_extract_traces.json"),
                 "roi_trace_h5"      : roi_trace_paths["roi_trace_h5"],
                 "roi_trace_dff_h5"  : roi_trace_paths["roi_trace_dff_h5"],
                 "roi_objectlist_txt": Path(segdir, "objectlist.txt"),
                 "stim_pkl"          : Path(sessdir, f"{sess_m_d}_stim.pkl"),
                 "stim_sync_h5"      : Path(sessdir, f"{sess_m_d}_sync.h5"),
                 "time_sync_h5"      : Path(expdir, 
                                       f"{expid}_time_synchronization.h5"),
                 "zstack_h5"         : Path(sessdir, 
                                       f"{sessid}_zstack_column.h5"),
                }
    
    if check:
        # files not to check for (are created if needed or should be checked 
        # when needed, due to size)
        no_check = ["align_pkl", "correct_data_h5", "zstack_h5", 
            "roi_trace_h5", "roi_trace_dff_h5"]

        for key in filepaths.keys():
            if key not in no_check:
                file_util.checkfile(filepaths[key])

    return dirpaths, filepaths


#############################################
def get_file_names_from_sessid(maindir, sessid, runtype="prod", check=True):
    """
    get_file_names_from_sessid(maindir, sessid)

    Returns the full path names of all of the expected data files in the 
    main directory for the specified session.
 
    Required args:
        - maindir (Path): path of the main data directory
        - sessid (int)  : session ID (9 digits)

    Optional args:
        - runtype (str)   : "prod" (production) or "pilot" data
                            default: "prod"
        - check (bool)    : if True, checks whether the files and directories 
                            in the output dictionaries exist (with a few 
                            exceptions)
                            default: True

    Returns:
        - dirpaths (dict): dictionary of directory paths (see get_file_names)
        - filepaths (dict): dictionary of file paths (see get_file_names)
    """

    sessdir, mouse_dir = get_sess_dir_path(maindir, sessid, runtype)

    mouseid, date = get_mouseid_date(sessdir, sessid)

    expid = get_expid(sessdir)
    segid = get_segid(sessdir)

    dirpaths, filepaths = get_file_names(
        maindir, sessid, expid, segid, date, mouseid, runtype, mouse_dir, 
        check)

    return dirpaths, filepaths


#############################################
def get_sess_dir_path(maindir, sessid, runtype="prod"):
    """
    get_sess_dir_path(maindir, sessid)

    Returns the path to the session directory, and whether a mouse directory 
    is included in the path.

    Required args:
        - maindir (Path): main directory
        - sessid (int)  : session ID

    Optional args:
        - runtype (str): "prod" (production) or "pilot" data
                          default: "prod"

    Returns:
        - sess_dir (Path) : path to the session directory
        - mouse_dir (bool): if True, session information is in a "mouse_*"
                            subdirectory
                            default: True 
    """

    if runtype not in ["pilot", "prod"]:
        gen_util.accepted_values_error("runtype", runtype, ["prod", "pilot"])

    # set the session directory (full path)
    wild_dir  = Path(maindir, runtype, "mouse_*", f"ophys_session_{sessid}")
    name_dir  = glob.glob(str(wild_dir))
    
    # pilot data may not be in a "mouse_" folder
    if len(name_dir) == 0:
        wild_dir  = Path(maindir, runtype,  f"ophys_session_{sessid}")
        name_dir  = glob.glob(str(wild_dir))
        mouse_dir = False
    else:
        mouse_dir = True

    if len(name_dir) == 0:
        raise OSError(f"Could not find the directory for session {sessid} "
            f"(runtype {runtype}) in {maindir} subfolders.")
    elif len(name_dir) > 1:
        raise OSError(f"Found {len(name_dir)} matching session folders in "
            f"{maindir} instead of 1.")

    sess_dir = Path(name_dir[0])

    return sess_dir, mouse_dir


#############################################
def get_mouseid(sessdir, mouse_dir=True):
    """
    get_mouseid(sessdir)

    Returns the mouse ID.

    Required args:
        - sessdir (Path): session directory

    Optional args:
        - mouse_dir (bool): if True, session information is in a "mouse_*"
                            subdirectory
                            default: True
        - sessid (int)    : session ID. If None, it is retrieved from the 
                            session directory.
                            default: None

    Returns:
        - mouseid (int): mouse ID (6 digits)
        - date (str)   : session date (i.e., yyyymmdd)
    """

    if mouse_dir:
        mstr = "mouse_"
        start = str(sessdir).find(mstr) + len(mstr)
        mouseid = str(sessdir)[start:start + 6]

        return mouseid
    
    else:
        mouseid, _ = get_mouseid_date(sessdir)


#############################################
def get_mouseid_date(sessdir, sessid=None):
    """
    get_mouseid_date(sessdir)

    Returns the mouse ID and optionally the date associated with a session, by
    finding the associated stimulus pickle.

    Required args:
        - sessdir (Path): session directory

    Optional args:
        - sessid (int) : session ID. If None, it is retrieved from the session
                         directory.
                         default: None

    Returns:
        - mouseid (int): mouse ID (6 digits)
        - date (str)   : session date (i.e., yyyymmdd)
    """

    if sessid is None:
        sessid = get_sessid(sessdir)

    pklglob = glob.glob(str(Path(sessdir, f"{sessid}*stim.pkl")))
    
    if len(pklglob) == 0:
        raise OSError(f"Could not find stim pkl file in {sessdir}")
    else:
        pklinfo = Path(pklglob[0]).name.split("_")
    
    mouseid = int(pklinfo[1]) # mouse 6 digit nbr
    date    = pklinfo[2]

    return mouseid, date


##############################################
def get_sessid(sessdir):
    """
    get_sessid(sessdir)

    Returns the session ID associated with a session.

    Required args:
        - sessdir (Path): session directory

    Returns:
        - sessid (int): session ID (9 digits)

    """

    sessdir = str(sessdir)

    sesspart = "ophys_session_"
    start = sessdir.find(sesspart) + len(sesspart)
    sessid = sessdir[start:start + 9]

    return sessid


############################################
def get_expid(sessdir):
    """
    get_expid(sessdir)

    Returns the experiment ID associated with a session.

    Required args:
        - sessdir (Path): session directory

    Returns:
        - expid (int): experiment ID (9 digits)

    """

    expglob = glob.glob(str(Path(sessdir, "ophys_experiment*")))
    if len(expglob) == 0:
        raise OSError(f"Could not find experiment directory in {sessdir}.")
    else:
        expinfo = Path(expglob[0]).name.split("_")
    expid = int(expinfo[2])

    return expid


#############################################
def get_segid(sessdir):
    """
    get_segid(sessdir)

    Returns the segmentation ID associated with a session.

    Required args:
        - sessdir (str): session directory

    Returns:
        - segid (int): experiment ID (8 digits)

    """

    segglob = glob.glob(
        str(Path(sessdir, "*", "processed", "ophys_cell_segmentation_run_*"))
        )
    if len(segglob) == 0:
        raise OSError(f"Could not find segmentation directory in {sessdir}")
    else:
        seginfo = Path(segglob[0]).name.split("_")
    segid = int(seginfo[-1])

    return segid


#############################################
def get_dendritic_mask_path(maindir, sessid, expid, mouseid, runtype="prod", 
                            mouse_dir=True, check=True):
    """
    get_dendritic_mask_path(maindir, sessid, expid, mouseid)

    Returns path to dendritic mask file.

    Required args:
        - maindir (Path): path of the main data directory
        - sessid (int)  : session ID (9 digits), e.g. "712483302"
        - expid (str)   : experiment ID (9 digits), e.g. "715925563"
        - date (str)    : date for the session in YYYYMMDD
                          e.g. "20160802"
        - mouseid (str) : mouse 6-digit ID string used for session files
                          e.g. "389778" 

    Optional args:
        - runtype (str)   : "prod" (production) or "pilot" data
                            default: "prod"
        - mouse_dir (bool): if True, session information is in a "mouse_*"
                            subdirectory
                            default: True
        - check (bool)    : if True, checks whether the mask file exists
                            default: True

    Returns:
        - maskfile (Path): full path name of the extract masks hdf5 file
    """

    procdir = get_sess_dirs(
        maindir, sessid, expid, None, mouseid, runtype, mouse_dir, 
        check=check)[2]


    maskfile = Path(procdir, f"{sessid}_dendritic_masks.h5")

    if check:
        file_util.checkfile(maskfile)
    
    return maskfile


#############################################
def get_dendritic_mask_path_from_sessid(maindir, sessid, runtype="prod", 
                                        check=True):
    """
    get_dendritic_mask_path_from_sessid(maindir, sessid)

    Returns path to dendritic mask file for the specified session.

    Required args:
        - maindir (Path): main directory
        - sessid (int)  : session ID

    Optional args:
        - runtype (str)   : "prod" (production) or "pilot" data
                            default: "prod"
        - check (bool)    : if True, checks whether the files in the output 
                            dictionary exist
                            default: True

    Returns:
        - maskfile (Path): full path name of the extract masks hdf5 file
    """

    sessdir, mouse_dir = get_sess_dir_path(maindir, sessid, runtype)

    mouseid = get_mouseid(sessdir, mouse_dir)

    expid = get_expid(sessdir)

    maskfile = get_dendritic_mask_path(
        maindir, sessid, expid, mouseid, runtype, mouse_dir, check)

    return maskfile


#############################################
def get_dendritic_trace_path(orig_file, check=True):
    """
    get_dendritic_trace_path(orig_file)

    Returns path to traces for EXTRACT dendritic trace data.

    Required args:
        - orig_file (Path): path to allen ROI traces

    Optional args:
        - check (bool): if True, the existence of the dendritic file is checked
                        default: True

    Returns:
        - dend_file (Path): path to corresponding EXTRACT dendritic ROI traces
    """

    orig_file = Path(orig_file)
    filepath = Path(orig_file.parent, orig_file.stem)
    ext = orig_file.suffix
    
    dend_part = "_dendritic"

    dend_file = Path(f"{filepath}{dend_part}").with_suffix(ext)

    if check:
        file_util.checkfile(dend_file)

    return dend_file


#############################################
def get_roi_trace_paths(maindir, sessid, expid, segid, mouseid, 
                        runtype="prod", mouse_dir=True, dendritic=False, 
                        check=True):
    """
    get_roi_trace_paths(maindir, sessid, expid, segid, mouseid)

    Returns the full path names of all of the expected ROI trace files in the 
    main directory.

    Required arguments:
        - maindir (Path): path of the main data directory
        - sessid (int)  : session ID (9 digits)
        - expid (str)   : experiment ID (9 digits)
        - segid (str)   : segmentation ID (9 digits)
        - mouseid (str) : mouse 6-digit ID string used for session files
                          e.g. "389778" 

    Optional arguments
        - runtype (str)   : "prod" (production) or "pilot" data
                            default: "prod"
        - mouse_dir (bool): if True, session information is in a "mouse_*"
                            subdirectory
                            default: True
        - dendritic (bool): if True, paths are changed to EXTRACT dendritic 
                            version
                            default: False
        - check (bool)    : if True, checks whether the files in the output 
                            dictionary exist
                            default: True
    
    Returns:
        - roi_trace_paths (dict): ROI trace paths dictionary
            ["demixed_trace_h5"] (Path)   : full path to demixed trace hdf5 file
            ["neuropil_trace_h5"] (Path)  : full path to neuropil trace hdf5 file
            ["roi_trace_h5"] (Path)       : full path name of the ROI raw 
                                            processed fluorescence trace hdf5 
                                            file
            ["roi_trace_dff_h5"] (Path)   : full path name of the ROI dF/F trace 
                                            hdf5 file
            ["unproc_roi_trace_h5"] (Path): full path to unprocessed ROI trace 
                                            hdf5 file (data stored under "FC")
    """

    _, expdir, procdir, demixdir, _ = get_sess_dirs(
        maindir, sessid, expid, segid, mouseid, runtype, mouse_dir, check)

    roi_trace_paths = {
        "unproc_roi_trace_h5": Path(procdir, "roi_traces.h5"),
        "neuropil_trace_h5"  : Path(procdir, "neuropil_traces.h5"),
        "demixed_trace_h5"   : Path(demixdir, f"{expid}_demixed_traces.h5"),
        "roi_trace_h5"       : Path(expdir, "neuropil_correction.h5"),
        "roi_trace_dff_h5"   : Path(expdir, f"{expid}_dff.h5"),
    }

    if dendritic:
        for key, val in roi_trace_paths.items():
            roi_trace_paths[key] = get_dendritic_trace_path(val, check=check)
    elif check:
        for _, val in roi_trace_paths.items():
            file_util.checkfile(val)

    return roi_trace_paths


#############################################
def get_roi_trace_paths_from_sessid(maindir, sessid, runtype="prod", 
                                    dendritic=False, check=True):
    """
    get_roi_trace_paths_from_sessid(maindir, sessid)

    Returns the full path names of all of the expected ROI trace files in the 
    main directory for the specified session.

    Required args:
        - maindir (Path): main directory
        - sessid (int)  : session ID

    Optional args:
        - runtype (str)   : "prod" (production) or "pilot" data
                            default: "prod"
        - dendritic (bool): if True, paths are changed to EXTRACT dendritic 
                            version
                            default: False
        - check (bool)    : if True, checks whether the files in the output 
                            dictionary exist
                            default: True

    Returns:
        - roi_trace_paths (dict): ROI trace paths dictionary 
                                  (see get_roi_trace_paths)
    """

    sessdir, mouse_dir = get_sess_dir_path(maindir, sessid, runtype)

    mouseid = get_mouseid(sessdir, mouse_dir)

    expid = get_expid(sessdir)
    segid = get_segid(sessdir)

    roi_trace_paths = get_roi_trace_paths(
        maindir, sessid, expid, segid, mouseid, runtype, mouse_dir, 
        dendritic, check)

    return roi_trace_paths


#############################################
def get_check_pupil_data_h5_name(pup_h5_name=None, sessid=None, mouseid=None, 
                                 date=None):
    """
    get_check_pupil_data_h5_name()

    Returns path name for pupil data h5 file, or checks whether the provided 
    file name conforms.

    Optional args:
        - pup_h5_name (Path)  : pupil data h5 file name to check. If None, a 
                                file name is generated.
                                default: None
        - sessid (int or str) : session ID to generate pup_h5_name with, or 
                                against which to check pup_h5_name.
                                default: None
        - mouseid (int or str): mouse ID to generate pup_h5_name with, or 
                                against which to check pup_h5_name.
                                default: None
        - date (int or str)   : date (YYYYMMDD) to generate pup_h5_name with, 
                                or against which to check pup_h5_name.
                                default: None

    Returns:
        - pup_data_h5 (Path): pupil data h5 file name (checked or generated)
    """

    if pup_h5_name is not None:
        pup_h5_name = Path(Path(pup_h5_name).parts[-1])
        if pup_h5_name.suffix != ".h5":
            raise ValueError("pup_h5_name should have extension .h5.")
        path_parts = pup_h5_name.stem.split("_")

        expected_parts = [sessid, mouseid, date]
        expected_lens = [9, 6, 8]

        error_str = ("Expected pup_h5_name to have form "
            "'{sessid:9}_{mouseid:6}_{date:8}_pupil_data_df.h5', but "
            f"found {pup_h5_name}.")


        error = False
        error = True if len(path_parts) != 6 else error


        for p, (part, exp_len) in enumerate(zip(expected_parts, expected_lens)):
            if part is not None:
                error = True if str(path_parts[p]) != str(part) else error
            else: # length checked instead
                error = True if len(path_parts[p]) != exp_len else error
        
        if path_parts[-3:] != ["pupil", "data", "df"]:
            error = True

        if error:
            raise RuntimeError(error_str)

    else:
        if sessid is None or mouseid is None or date is None:
            raise ValueError(
                "If 'h5_name' is None, must provide sessid, mouseid and date."
                )
        pup_h5_name = f"{sessid}_{mouseid}_{date}_pupil_data_df.h5"

    return pup_h5_name


#############################################
def get_pupil_data_h5_path(maindir, check_name=True):
    """
    get_pupil_data_h5_path(maindir)

    Returns path to pupil data h5 file.

    Required args:
        - maindir (Path): path of the main data directory

    Optional args:
        - check_name (bool): if True, pupil file name is checked to have the 
                             expected structure.
                             default: True

    Returns:
        - pup_data_h5 (Path or list): full path name(s) of the pupil h5 file
    """

    name_part = "*pupil_data_df.h5"
    pupil_data_files = glob.glob(str(Path(maindir, name_part)))

    if len(pupil_data_files) == 1:
        pup_data_h5 = Path(pupil_data_files[0])
    elif len(pupil_data_files) > 1:
        pup_data_h5 = [Path(data_file) for data_file in pupil_data_files]
    else:
        pup_data_h5 = "none"

    if check_name:
        for h5_name in gen_util.list_if_not(pup_data_h5):
            if h5_name != "none":
                get_check_pupil_data_h5_name(h5_name)

    return pup_data_h5


#############################################
def get_nway_match_path_from_sessid(maindir, sessid, runtype="prod", 
                                    check=True):
    """
    get_nway_match_path_from_sessid(maindir, sessid)

    Returns the full path name for the nway match file in the main directory 
    for the specified session.

    Required args:
        - maindir (path): main directory
        - sessid (int)  : session ID

    Optional args:
        - runtype (str)   : "prod" (production) or "pilot" data
                            default: "prod"
        - check (bool)    : if True, checks whether the files in the output 
                            dictionary exist
                            default: True

    Returns:
        - nway_match_path (path): n-way match path
    """

    sessdir, mouse_dir = get_sess_dir_path(maindir, sessid, runtype)

    mouseid = get_mouseid(sessdir, mouse_dir)

    expid = get_expid(sessdir)
    segid = get_segid(sessdir)

    _, _, procdir, _, _ = get_sess_dirs(
        maindir, sessid, expid, segid, mouseid, runtype, mouse_dir, check)

    nway_match_path = Path(
        procdir, f"mouse_{mouseid}__session_{sessid}__nway_matched_rois.json"
        )

    if check:
        file_util.checkfile(nway_match_path)

    return nway_match_path


#############################################
def get_local_nway_match_path_from_sessid(sessid):
    """
    get_local_nway_match_path_from_sessid(sessid)

    Returns the full path name for the nway match file stored in the repository 
    main directory for the specified session.

    Required args:
        - sessid (int)  : session ID

    Returns:
        - nway_match_path (path): n-way match path
    """

    tracking_dir = Path(Path(__file__).resolve().parent.parent, "roi_tracking")

    if tracking_dir.exists():
        nway_path_pattern = Path(
            tracking_dir, "**", f"*session_{sessid}__nway_matched_rois.json"
            )
        matching_files = glob.glob(str(nway_path_pattern), recursive=True)
        if len(matching_files) == 0:
            raise RuntimeError(
                f"Found no local nway match file for session {sessid} in "
                f"{tracking_dir}."
                )
        elif len(matching_files) > 1:
            raise NotImplementedError(
                f"Found multiple local nway match files for session {sessid} "
                f"in {tracking_dir}."
                )
        else:
            nway_match_path =  Path(matching_files[0])
    else:
        raise RuntimeError(
            "Expected to find the 'roi_tracking' directory in the main "
            f"repository folder: {tracking_dir}"
            )

    return nway_match_path

