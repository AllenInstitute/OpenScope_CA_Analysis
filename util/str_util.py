'''
str_util.py

This module contains basic math functions for getting strings to print or save
files for AIBS experiments for the Credit Assignment Project.

Authors: Colleen Gillon

Date: October, 2018

Note: this code uses python 2.7.

'''
import datetime

import gen_util


#############################################
def shuff_par_str(shuffle=True, type_str='print'):
    """
    shuff_par_str()

    Creates a string from shuffle parameter to print or for a filename.

    Optional arguments:
        - shuffle (bool): default: True
        - type (str)    : 'print' for a printable string and 'file' for a
                          string usable in a filename.
                          default: 'print'
    
    Returns:
        - shuff_str (str): shuffle parameter string
    """

    if shuffle:
        if type_str == 'print':
            shuff_str = ', shuffled'
        elif type_str == 'file':
            shuff_str = '_shuffled'
        elif type_str == 'labels':
            shuff_str = ' (shuffled labels)'
        else:
            gen_util.accepted_values_error('type_str', type_str, ['print', 'file'])
    else:
        shuff_str = ''

    return shuff_str
    
    
#############################################
def norm_par_str(norm=True, type_str='print'):
    """
    norm_par_str()

    Creates a string from norm parameter to print or for a filename.

    Optional arguments:
        - norm (bool): default: True
        - type (str) : 'print' for a printable string and 'file' for a
                       string usable in a filename.
                       default: 'print'
    
    Returns:
        - norm_str (str): norm parameter string
    """

    if norm:
        if type_str == 'print':
            norm_str = ', norm'
        elif type_str == 'file':
            norm_str = '_norm'
        else:
            gen_util.accepted_values_error('type_str', type_str, ['print', 'file'])
    else:
        norm_str = ''

    return norm_str
    

#############################################
def fluor_par_str(raw=True, type_str='print'):
    """
    fluor_par_str()

    Creates a string from the fluorescence parameter to print or for a 
    filename.

    Optional arguments:
        - raw (bool): whether raw or processed fluorescence traces are used  
                      default: True
        - type (str): 'print' for a printable string and 'file' for a
                      string usable in a filename.
                      default: 'print'
    
    Returns:
        - fluor_str (str): fluorescence parameter string
    """

    if raw:
        if type_str == 'print':
            fluor_str = 'raw fluorescence intensity'
        elif type_str == 'file':
            fluor_str = 'raw'
        else:
            gen_util.accepted_values_error('type_str', type_str, ['print', 'file'])
    else:
        if type_str == 'print':
            fluor_str = 'dF/F'
        elif type_str == 'file':
            fluor_str = 'dff'
        else:
            gen_util.accepted_values_error('type_str', type_str, ['print', 'file'])

    return fluor_str
    

#############################################
def stat_par_str(stats='mean', error='std'):
    """
    stat_par_str()

    Creates a string from statistical analysis parameters to print or for a 
    title.

    Optional arguments:
        - stats (str): 'mean' or 'median'
                       default: 'mean'
        - error (str): 'std' (for std or quartiles) or 'sem' (for SEM or MAD)
                       default: 'std'
    
    Returns:
        - stat_str (str): statistics combo string
    """

    if stats == 'mean':
        stat_str = '{}/{}'.format(stats, error)
    elif stats == 'median':
        if error == 'std':
            stat_str = '{}/qu'.format(stats)
        elif error == 'sem':
            stat_str = '{}/mad'.format(stats)
        else:
            gen_util.accepted_values_error('error', error, ['std', 'sem'])
    else:
        gen_util.accepted_values_error('stats', stats, ['mean', 'median'])
    return stat_str


#############################################
def op_par_str(plot_vals='diff', op='diff', area=False, str_type='file'):
    """
    op_par_str()

    Creates a string from operation parameter (e.g., surprise, non surprise 
    or the difference/ratio between the two) to print or for a title.

    Optional arguments:
        - plot_vals (str): 'surp', 'nosurp' or 'diff'
                           default: 'diff'
        - op (str)       : 'diff' or 'ratio'
                           default: 'diff'
        - str_type (str) : use of output str, i.e., for a filename ('file') or
                           to print the info to console ('print')
                           default = 'file'
    
    Returns:
        - area (bool) : if True, print string indicates that 'area' is plotted,
                        not trace
                        default: False 
        - op_str (str): operation type string
    """
    if area:
        area_str = ' area'
    else:
        area_str = ''
    if plot_vals == 'diff':
        if str_type == 'print':
            op_str = '{} in dF/F{} for surp v nosurp'.format(area_str, op)
        elif str_type == 'file':
            op_str = plot_vals
    elif plot_vals in ['surp', 'nosurp']:
        if str_type == 'print':
            op_str = 'dF/F{} for {}'.format(area_str, plot_vals)
        elif str_type == 'file':
            op_str = plot_vals
    else:
        gen_util.accepted_values_error('plot_vals', plot_vals, ['diff', 'surp', 'nosurp'])
    return op_str


#############################################
def create_time_str():
    """
    create_time_str()

    Creates a string in a format appropriate for a directory or filename
    containing date and time information based on time at which the function is
    called.

    Return:
        dir_name (str): string containing date and time formatted as 
                        YYMMDD_HHMMSS
    """

    now = datetime.datetime.now()
    dir_name = ('{:02d}{:02d}{:02d}_'
                '{:02d}{:02d}{:02d}').format(now.year, now.month, now.day, 
                                             now.hour, now.minute, now.second)
    return dir_name


#############################################
def sess_par_str(sess_par, gab_k, str_type='file'):
    """
    sess_par_str(sess_par, gab_k)

    Creates a string from session and gabor kappa parameters for a filename, 
    or to print or use in a title.

    Required arguments:
        - sess_par (dict)     : dictionary containing session parameters: 
                                e.g. 'layer', 'overall_sess_n'
                ['layer'] (str)         : layer ('soma', 'dend', 'L23_soma',  
                                                'L5_soma', 'L23_dend', 'L5_dend', 
                                                'L23_all', 'L5_all')
                ['overall_sess_n'] (int): overall session number aimed for
        - gab_k (int or list) : gabor kappa parameter

    Optional arguments:
        - str_type (str): use of output str, i.e., for a filename ('file') or to
                          print the info to console ('print')
                          default = 'file'
    Return:
        - sess_str (list): string containing info on session and gabor kappa 
                           parameters
    """

    gab_k_str = gab_k_par_str(gab_k)
    if str_type == 'file':
        sess_str = 'sess{}_gab{}_{}'.format(sess_par['overall_sess_n'], gab_k_str,
                                             sess_par['layer'])
    elif str_type == 'print':
        if len(gab_k_str) == 0:
            sess_str = ('gabors, ')
        else:
            sess_str = 'gabors: {}, '.format(gab_k_str)
        sess_str += 'session: {}, layer: {}'.format(sess_par['overall_sess_n'], 
                                                     sess_par['layer'])
    else:
        gen_util.accepted_values_error('str_type', str_type, ['file', 'print'])
    return sess_str
    

#############################################
def gab_k_par_str(gab_k):
    """
    gab_k_par_str(gab_k)

    Creates a string from gabor kappa parameter (e.g., '4' or '16'). Returns
    an empty string if both gabor kappa parameters are passed.

    Required arguments:
        - gab_k (int or list): gabor kappa parameter

    Return:
        (list): string containing gabor kappa parameter value or empty string
                if both parameters are passed.
    """

    gab_k = gen_util.list_if_not(gab_k)
    if len(gab_k) > 1:
        return ''
    else:
        return str(gab_k[0])