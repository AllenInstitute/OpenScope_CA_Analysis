"""
sess_pupil_util.py

This module contains functions for extracting pupil diameter information from
the pupil tracking data generated by the AIBS experiments for the Credit 
Assignment Project.

Authors: Jay Pina

Date: July, 2019

Note: this code uses python 3.7.

"""

import copy

import numpy as np


#############################################
def get_center_dist_diff(center_x, center_y):
    """
    get_center_dist_diff(center_x, center_y)

    Returns the change in pupil center between each pupil frame.  All in pixels.

    Required args:
        - center_x (1D array): pupil center position in x at each pupil frame 
        - center_y (1D array): pupil center position in y at each pupil frame

    Returns:
        - center_dist_diff (1D array): change in pupil center between each 
                                       pupil frame
    """
    
    center = np.stack([center_x, center_y])
    center_diff = np.diff(center, axis=1)
    center_dist_diff = np.sqrt(center_diff[0]**2 + center_diff[1]**2)

    return center_dist_diff


#############################################
def _diam_no_blink(diam, thr=5):
    """
    _diam_no_blink(diam)

    Returns the diameter without large deviations likely caused by blinks
    
    Required args:
        - diam (1D array): array of diameter values

    Optional args:
        - thr (num): threshold diameter to identify blinks
                     default: 5

    Returns:
        - nan_diam (1D array): array of diameter values with aberrant values 
                               removed
    """

    nan_diam = copy.deepcopy(diam)

    # Find aberrant blocks
    diam_diff = np.append(0, np.diff(diam))
    diam_thr = np.where(np.abs(diam_diff) > thr)[0]
    diam_thr_diff = np.append(1, np.diff(diam_thr)) 
    
    if len(diam_thr) == 0:
        return nan_diam

    diff_thr = 10 # how many consecutive frames should be non-aberrant
    searching = True
    i = 0
    while(searching):
        left = diam_thr[i]
        w = np.where(diam_thr_diff[i + 1:] > diff_thr)[0]
        if w.size: # i.e., non-empty array
            right_i = np.min(w + i + 1) - 1
            right = diam_thr[right_i]
        else:
            right = diam_thr[-1]
            searching = False
        i = right_i + 1
        nan_diam[left:right + 1] = np.nan
        
    return nan_diam
        

#############################################
def _eye_diam_center(df, thr=5):
    """
    _eye_diam_center(df)

    Returns the approximated pupil diameter, center, and frame-by-frame
    center differences (approximate derivative).  All in pixels.

    Required args:
        - data (pd DataFrame): dataframe with the following columns 
                               ('coords', 'bodyparts', ordered frame numbers)

    Optional args:
        - thr (num): threshold diameter to identify blinks
                     default: 5

    Returns:
        - nan_diam (1D array)        : array of diameter values with aberrant 
                                       values removed
        - center (2D array)          : pupil center position at each pupil 
                                       frame, structured as 
                                           frame x coord (x, y)
        - center_dist_diff (1D array): change in pupil center between each 
                                       pupil frame
    """
    
    pupil = '--pupil'
    
    pup_df = df.loc[(df['bodyparts'].str.contains(pupil))]

    ds = [None, None]
    all_vals = [None, None]
    coords = ['x', 'y']
    
    for c, coord in enumerate(coords):
        coord_df = pup_df.loc[(pup_df['coords'].str.match(coord))]
    
        col = [col_name.replace(pupil, '') 
               for col_name in coord_df['bodyparts'].tolist()]
    
        # Remove 'bodyparts' and 'coords' columns
        coord_df.pop('bodyparts')
        coord_df.pop('coords')

        vals = coord_df.to_numpy('float')

        diffs = [['left', 'right'], ['top', 'bottom'], 
            ['lower-left', 'upper-right'], ['upper-left', 'lower-right']]
        diff_vals = np.empty([vals.shape[1], len(diffs)])
        
        # pairwise distances between points furthest apart (see diffs for pairs)
        for d, diff in enumerate(diffs):
            diff_vals[:, d] = np.abs(
                vals[col.index(diff[0]), :] - vals[col.index(diff[1]), :])
        ds[c] = diff_vals
        all_vals[c] = vals

    [dx, dy] = ds
    [x, y] = all_vals

    # find diameters (frames x diams (4))
    diams = np.sqrt(dx**2 + dy**2)

    # max_diam = np.max(diams, axis=1)
    # mean_diam = np.mean(diams, axis=1)
    median_diam = np.median(diams, axis=1)
    # min_diam = np.min(diams, axis=1)

    nan_diam = _diam_no_blink(median_diam, thr)

    # find centers and frame-to-frame differences
    center = np.transpose([np.mean(x, axis=0), np.mean(y, axis=0)])
    center_dist_diff = get_center_dist_diff(center[:, 0], center[:, 1])

    nan_idx = np.where(np.isnan(nan_diam))[0]
    center[nan_idx] = np.nan

    nan_idx = np.where(np.isnan(np.diff(nan_diam)))[0]
    center_dist_diff[nan_idx] = np.nan

    return nan_diam, center, center_dist_diff

