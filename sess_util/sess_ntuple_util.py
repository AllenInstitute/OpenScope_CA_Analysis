"""
sess_ntuple_util.py

This module contains functions to initialize namedtuples for analyses on data
generated by the AIBS experiments for the Credit Assignment Project

Authors: Colleen Gillon

Date: October, 2018

Note: this code uses python 3.7.
"""

from collections import namedtuple

from util import gen_util


#############################################
def init_analyspar(fluor='dff', remnans=True, stats='mean', error='sem', 
                   scale=False, dend='extr'):
    """
    Returns a AnalysPar namedtuple with the inputs arguments as named 
    attributes.

    Optional args:
        - fluor (str)  : whether 'raw' or processed fluorescence traces 
                         'dff' are used  
                         default: 'dff'
        - remnans (str): if True, ROIs with NaN/Inf values are removed in
                         the analyses.
                         default: True
        - stats (str)  : statistic parameter ('mean' or 'median')
                         default: 'mean'
        - error (str)  : error statistic parameter, ('std' or 'sem')
                         default: 'sem'
        - scale (bool) : if True, data is scaled
                         default: False
        - dend (str)   : dendrites to use ('aibs' or 'extr')
                         default: 'extr'

    Returns:
        - analyspar (AnalysPar namedtuple): AnalysPar with input arguments as 
                                            attributes
    """

    analys_pars = [fluor, remnans, stats, error, scale, dend]
    analys_keys = ['fluor', 'remnans', 'stats', 'error', 'scale', 'dend']
    AnalysPar   = namedtuple('AnalysPar', analys_keys)
    analyspar   = AnalysPar(*analys_pars)
    return analyspar


#############################################
def init_sesspar(sess_n, closest=False, layer='soma', line='any', min_rois=1, 
                 pass_fail='P', incl='yes', runtype='prod', mouse_n='any'):
    """
    Returns a SessPar namedtuple with the inputs arguments as named 
    attributes.

    Required args:
        - sess_n (int): session number aimed for

    Optional args:
        - closest (bool)            : if False, only exact session number is 
                                      retained, otherwise the closest.
                                      default: False
        - layer (str)               : layer ('soma', 'dend', 'L23_soma',  
                                      'L5_soma', 'L23_dend', 'L5_dend', 
                                      'L23_all', 'L5_all')
                                      default: 'soma'
        - line (str)                : mouse line
                                      default: 'any'
        - min_rois (int)            : min number of ROIs
                                      default: 1
        - pass_fail (str or list)   : pass/fail values of interest ('P', 'F')
                                      default: 'P'
        - incl (str or list)        : incl values of interest ('yes', 'no', 
                                      'all')
                                      default: 'yes'
        - runtype (str)             : runtype value ('pilot', 'prod')
                                      default: 'prod'
        - mouse_n (str, int or list): mouse number
                                      default: 'any'
    
    Returns:
        - sesspar (SessPar namedtuple): SessPar with input arguments as 
                                        attributes
    """

    sess_pars = [sess_n, closest, layer, line, min_rois, pass_fail, incl, 
                 runtype, mouse_n]
    sess_keys = ['sess_n', 'closest', 'layer', 'line', 'min_rois', 'pass_fail', 
                 'incl', 'runtype', 'mouse_n']
    SessPar   = namedtuple('SessPar', sess_keys)
    sesspar   = SessPar(*sess_pars)
    return sesspar


#############################################
def init_stimpar(stimtype='both', bri_dir=['right', 'left'], bri_size=128, 
                 gabfr=0, gabk=16, gab_ori=[0, 45, 90, 135], pre=0, post=1.5):
    """
    Returns a StimPar namedtuple with the inputs arguments as named 
    attributes.

    Optional args:
        - stimtype (str)         : stimulus to analyse ('bricks', 'gabors' or 
                                   'both')
                                   default: 'both'
        - bri_dir (str or list)  : brick direction values to include
                                   ('right', 'left', ['right', 'left'])
                                   default: ['right', 'left']
        - bri_size (int or list) : brick size values to include
                                   (128, 256 or [128, 256])
                                   default: 128
        - gabfr (int)            : gabor frame at which segments start 
                                   (0, 1, 2, 3) (or to include, for GLM)
                                   default: 0
        - gabk (int or list)     : gabor kappa values to include 
                                   (4, 16 or [4, 16])
                                   default: 16
        - gab_ori (int or list)  : gabor orientation values to include
                                   default: [0, 45, 90, 135]
        - pre (num)              : range of frames to include before each
                                   reference frame (in s)
                                   default: 0
        - post (num)             : range of frames to include after each 
                                   reference frame (in s)
                                   default: 1.5
    
    Returns:
        - stimpar (StimPar namedtuple): StimPar with input arguments as 
                                        attributes
    """

    stim_keys = ['stimtype', 'bri_dir', 'bri_size', 'gabfr', 'gabk', 'gab_ori', 
                 'pre', 'post']
    stim_pars = [stimtype, bri_dir, bri_size, gabfr, gabk, gab_ori, pre, post]
    StimPar   = namedtuple('StimPar', stim_keys)
    stimpar   = StimPar(*stim_pars)
    return stimpar


#############################################
def init_autocorrpar(lag_s=4, byitem=True):
    """
    Returns a Autocorr namedtuple with the inputs arguments as named attributes.

    Optional args:
        - lag_s (num)  : lag for which to calculate autocorrelation (in sec).
                         default: 4
        - byitem (bool): if True, autocorrelation stats are calculated across
                         items (e.g., ROIs)
    
    Returns:
        - autocorrpar (AutocorrPar namedtuple): AutocorrPar with input 
                                                arguments as attributes
    """

    autocorr_pars = [lag_s, byitem]
    autocorr_keys = ['lag_s', 'byitem']
    AutocorrPar   = namedtuple('AutocorrPar', autocorr_keys)
    autocorrpar   = AutocorrPar(*autocorr_pars)
    return autocorrpar


#############################################
def init_permpar(n_perms=10000, p_val=0.05, tails=2, multcomp=True):
    """
    Returns a PermPar namedtuple with the inputs arguments as named attributes.

    Optional args:
        - n_perms (int)     : nbr of permutations to run
                              default: 10000
        - p_val (num)       : p-value to use for significance thresholding 
                              (0 to 1)
                              default: 0.05
        - tails (str or int): which tail(s) to test ('up', 'lo', 2)
                              default: 2
        - multcomp (bool)   : if True, multiple comparison correction used to 
                              assess significance
    
    Returns:
        - permpar (PermPar namedtuple): PermPar with input arguments as 
                                        attributes
    """

    perm_pars = [n_perms, p_val, tails, multcomp]
    perm_keys = ['n_perms', 'p_val', 'tails', 'multcomp']
    PermPar   = namedtuple('PermPar', perm_keys)
    permpar   = PermPar(*perm_pars)
    return permpar


#############################################
def init_quintpar(n_quints=4, qu_idx='all', qu_lab=None, qu_lab_pr=None):
    """
    Returns a QuintPar namedtuple with the inputs arguments as named attributes.

    Optional args:
        - n_quints (int)   : nbr of quintiles
                             default: 4
        - qu_idx (list)    : indices of quintiles used in analyses 
                             default: 'all'
        - qu_lab (list)    : labels of quintiles used in analyses
                             if None, labels are created in format: 'q1'
                             default: None
        - qu_lab_pr (list) : labels for printing of quintiles used in analyses
                             if None, labels are created in format: 'qu 1/1'
                             default: None
    
    Returns:
        - quintpar (QuintPar namedtuple): QuintPar with input arguments as 
                                          attributes
    """

    if qu_idx == 'all':
        qu_idx = list(range(n_quints))
    
    qu_idx = gen_util.list_if_not(qu_idx)

    # Quintile labels
    if qu_lab is None:
        qu_lab = ['q{}'.format(list(range(n_quints))[q]+1) for q in qu_idx]
    else:
        qu_lab = gen_util.list_if_not(qu_lab)

    if qu_lab_pr is None:
        qu_lab_pr = ['qu {}/{}'.format(list(range(n_quints))[q]+1, n_quints) 
                                                       for q in qu_idx]
    else:
        qu_lab_pr = gen_util.list_if_not(qu_lab_pr)

    if len(qu_idx) != len(qu_lab) or len(qu_idx) != len(qu_lab_pr):
        raise ValueError('Must pass as many indices as labels.')

    quint_pars = [n_quints, qu_idx, qu_lab, qu_lab_pr]
    quint_keys = ['n_quints', 'qu_idx', 'qu_lab', 'qu_lab_pr']
    QuintPar   = namedtuple('QuintPar', quint_keys)
    quintpar   = QuintPar(*quint_pars)
    return quintpar


#############################################
def init_roigrppar(grps, add_reg=True, op='diff', plot_vals='surp'):
    """
    Returns a RoiGrpPar namedtuple with the inputs arguments as named 
    attributes.

    Required args:
        - grps (str or list): set or sets of groups to return, ('all', 
                              'change', 'no_change', 'reduc', 'incr'). 
                              If several sets are passed, each set will be 
                              collapsed into group and 'add_reg' will be set 
                              to False.

    Optional args:
        - add_reg (bool)    : if True, the group of ROIs showing no 
                              significance in either is added to the groups 
                              returned
                              default: True
        - op (str)          : operation on values, if plotvals if 'both' 
                              ('ratio' or 'diff') 
                              default: 'diff'
        - plot_vals (str)   : values to plot ('surp', 'reg', 'both')
                              default: 'surp' 
    
    Returns:
        - roigrppar (RoiGrpPar namedtuple): RoiGrpPar with input arguments as 
                                            attributes
    """

    roigrp_pars = [grps, add_reg, op, plot_vals]
    roigrp_keys = ['grps', 'add_reg', 'op', 'plot_vals']
    RoiGrpPar    = namedtuple('RoiGrpPar', roigrp_keys)
    roigrppar    = RoiGrpPar(*roigrp_pars)
    return roigrppar


#############################################
def init_tcurvpar(gabfr=3, pre=0, post=0.6, grp2='surp', test=False, 
                  prev=False):
    """
    Returns a TCurvPar namedtuple with the inputs arguments as named 
    attributes.
    
    Optional args:
        - gabfr (int or str): gabor frame at which sequences start 
                              (0, 1, 2, 3) for tuning curve analysis
                              (x_x, interpreted as 2 gabfrs)
                              default: 3
        - pre (num)         : range of frames to include before each 
                              reference frame (in s) for tuning curve analysis
                              default: 0
        - post (num)        : range of frames to include after each 
                              reference frame (in s) for tuning curve analysis
                              default: 0.6
        - tc_grp2 (str)     : second group: either surp, reg or rand (random 
                              subsample of reg, the size of surp)
                              default: 'surp'
        - test (bool)       : if True, tuning curve analysis is run on a 
                              small subset of ROIs and gabors
                              default: False
        - prev (bool)       : if True, analysis is run using previous tuning 
                              estimation method
    """
    # break 2 gabfr values into list
    if isinstance(gabfr, list):
        gabfr = [int(gf) for gf in gabfr]
    elif '_' in str(gabfr):
        gabfr = [int(gf) for gf in gabfr.split('_')]
    else:
        gabfr = int(gabfr)

    tcurv_pars = [gabfr, float(pre), float(post), grp2, test, prev]
    tcurv_keys = ['gabfr', 'pre', 'post', 'grp2', 'test', 'prev']
    TCurvPar   = namedtuple('TCurvPar', tcurv_keys)
    tcurvpar   = TCurvPar(*tcurv_pars)
    return tcurvpar


#############################################
def init_logregpar(comp='surp', ctrl=False, q1v4=False, regvsurp=False, 
                   n_epochs=1000, batchsize=200, lr=0.0001, train_p=0.75, 
                   wd=0, bal=False, alg='sklearn'):
    """
    Returns a LogRegPar namedtuple with the inputs arguments as named 
    attributes.

    Optional args:
        - comp (str)     : comparison to run regression on 
                           (e.g., 'surp', 'AvB', 'AvC', 'BvC', 'DvE')
                           default: 'surp'
        - ctrl (bool)    : if True, regression is run as a control for surp 
                           comparison
                           default: False
        - q1v4 (bool)    : if True, regression is run on quintile 1 and tested 
                           on quintile 4
                           default: False
        - regvsurp (bool): if True, regression is run on regular bricks 
                           direction and tested on surprise trials
        - n_epochs (int) : number of epochs to run
                           default: 1000
        - batchsize (int): batch size
                           default: 200
        - lr (num)       : learning rate
                           default: 0.0001
        - train_p (num)  : proportion of dataset used in training set
                           default: 0.75
        - wd (num)       : weight decay
                           default: 0
        - bal (bool)     : if True, classes are balanced
                           default: False
        - alg (str)      : algorithm to use ('sklearn' or 'pytorch')
                           default: 'sklearn'

    Returns:
        - logregpar (LogRegPar namedtuple): LogRegPar with input arguments as 
                                            attributes
    """

    logreg_pars = [comp, ctrl, q1v4, regvsurp, n_epochs, batchsize, lr, 
                   train_p, wd, bal, alg]
    logreg_keys = ['comp', 'ctrl', 'q1v4', 'regvsurp', 'n_epochs', 'batchsize', 
                   'lr', 'train_p', 'wd', 'bal', 'alg']
    LogRegPar   = namedtuple('LogRegPar', logreg_keys)
    logregpar   = LogRegPar(*logreg_pars)
    return logregpar


#############################################
def init_glmpar(each_roi=False, k=10, test=False):
    """
    Returns a GLMPar namedtuple with the inputs arguments as named attributes.

    Optional args:
        - each_roi (bool): if True, GLMs are run by ROI
                           default: False
        - k (int)        : number of folds to repeat GLM
                           default: 10
        - test (bool)    : if True, runs on only a few ROIs (if each_roi)
    Returns:
        - glmpar (GLMPar namedtuple): GLMPar with input arguments as attributes
    """

    glm_pars = [each_roi, k, test]
    glm_keys = ['each_roi', 'k', 'test']
    GLMPar   = namedtuple('GLMPar', glm_keys)
    glmpar   = GLMPar(*glm_pars)
    return glmpar


#############################################
def init_latpar(method='ttest', p_val_thr=0.005, rel_std=0.5):
    """
    Returns a latency namedtuple with the inputs arguments as named attributes.

    Optional args:
        - method (str)     : latency calculating method ('ratio' or 'ttest')
                             default: 'ttest'
        - p_val_thr (float): p-value threshold for t-test method
                             default: 0.005
        - rel_std (flot)   : relative standard deviation threshold for ratio 
                             method
                             default: 0.5
    Returns:
        - latpar (LatPar namedtuple): LatPar with input arguments as attributes
    """

    lat_pars = [method, p_val_thr, rel_std]
    lat_keys = ['method', 'p_val_thr', 'rel_std']
    LatPar   = namedtuple('LatPar', lat_keys)
    latpar   = LatPar(*lat_pars)
    return latpar


#############################################
def init_basepar(baseline=0.1):
    """
    Returns a baseline namedtuple with the inputs arguments as named attributes.

    Optional args:
        - baseline (float): baseline time
                            default: 0.1
    Returns:
        - basepar (BasePar namedtuple): BasePar with input arguments as 
                                        attributes
    """

    base_pars = [baseline]
    base_keys = ['baseline']
    BasePar   = namedtuple('BasePar', base_keys)
    basepar   = BasePar(*base_pars)
    return basepar


#############################################
def get_modif_ntuple(ntuple, keys, key_vals):
    """
    get_modif_ntuple(ntuple, keys, key_vals)
    
    Returns a ntuple with certain attributes modified.

    Required args:
        - ntuple (named tuple): specific type of named tuple
        - keys (list)         : list of keys to modify
        - key_vals (list)     : list of values to assign to keys

    Returns:
        - ntuple (named tuple): same namedtuple type, but modified
    """

    ntuple_dict = ntuple._asdict()

    ntuple_name = type(ntuple).__name__

    ntuple_types = ['AnalysPar', 'SessPar', 'StimPar', 'AutocorrPar', 'PermPar', 
                    'QuintPar', 'RoiGrpPar', 'TCurvPar', 'LogRegPar', 'GLMPar']
    
    init_fcts = [init_analyspar, init_sesspar, init_stimpar, init_autocorrpar, 
                 init_permpar, init_quintpar, init_roigrppar, init_tcurvpar, 
                 init_logregpar, init_glmpar]

    if not isinstance(keys, list):
        keys = [keys]
        key_vals = [key_vals]

    for key, val in zip(keys, key_vals):
        if key not in ntuple_dict.keys():
            raise ValueError('{} not in ntuple dictionary keys.'.format(key))
        ntuple_dict[key] = val

    if ntuple_name in ntuple_types:
        type_idx = ntuple_types.index(ntuple_name)
        fct = init_fcts[type_idx]
        ntuple_new = fct(**ntuple_dict)
    else:
        raise ValueError(('ntuple of type {} not recognized.').format(
                            ntuple_name))

    return ntuple_new

