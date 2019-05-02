import os
import copy
import argparse
import multiprocessing

from joblib import Parallel, delayed
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import torch

from analysis import quint_analys
from util import data_util, file_util, gen_util, logreg_util, math_util, \
                 plot_util
from sess_util import sess_gen_util, sess_ntuple_util, sess_str_util
from plot_fcts import logreg_plots


#############################################
def get_stimpars(comp='surp', stimtype='gabors', bri_dir='right', bri_size=128, 
                 gabfr=0, gabk=16):
    """
    get_stimpars()
    
    Returns a stimulus parameter named tuple based on the stimulus parameters 
    passed and comparison type.

    Optional args:
        - comp (str)            : type of comparison
                                  default: 'surp'
        - stimtype (str)        : stimulus type
                                  default: 'gabors'
        - bri_dir (str or list) : brick direction
                                  default: 'right'
        - bri_size (int or list): brick direction
                                  default: 128
        - gabfr (int or list)   : gabor frame of reference (may be a list 
                                  depending on 'comp')
                                  default: 0
        - gabk (int or list)    : gabor kappa
                                  default: 16 

    Returns:
        - stimpar (StimPar): named tuple containing stimulus parameters 
    """

    [bri_dir, bri_size, gabfr, 
                 gabk, gab_ori] = sess_gen_util.get_params(stimtype, bri_dir, 
                                                         bri_size, gabfr, gabk)


    if stimtype == 'gabors':
        if comp == 'surp':
            stimpar = sess_ntuple_util.init_stimpar(bri_dir, bri_size, gabfr, 
                                              gabk, gab_ori, 0, 1.5, stimtype)
        else:
            gabfrs = sess_str_util.gabfr_nbrs([comp[0], comp[2]])
            stimpar = sess_ntuple_util.init_stimpar(bri_dir, bri_size, 
                                gabfrs, gabk, gab_ori, 0, 0.45, stimtype)
    elif stimtype == 'bricks':
        if comp == 'surp':
            stimpar = sess_ntuple_util.init_stimpar(bri_dir, bri_size, gabfr, 
                                               gabk, gab_ori, 0, 1.5, stimtype)
        else:
            raise ValueError('Only surprise comparison supported for Bricks.')

    return stimpar


#############################################
def get_rundir(run_n, uniqueid=None):
    """
    get_rundir(run_n)

    Returns the name of the specific subdirectory in which an analysis is
    saved, based on a run number and unique ID.
    
    Required args:
        - run_n (int): run number
    
    Optional args:
        - uniqueid (str or int): unique ID for analysis
                                 default: None

    Returns:
        - rundir (str): name of subdirectory to save analysis in
    """

    if uniqueid is None:
        rundir = 'run_{}'.format(run_n)
    else:
        rundir = '{}_{}'.format(uniqueid, run_n)

    return rundir


#############################################
def get_compdir_dict(rundir):
    """
    get_compdir_dict(rundir)

    Returns a dictionary with analysis parameters based on the full analysis 
    path.
    
    Required args:
        - rundir (str): path of subdirectory in which analysis is saved,
                        structured as 
                        '.../m_s_layer_stim_fluor_scaled_comp_shuffled/
                        uniqueid_run'
    
    Returns:
        - compdir_dict (dict): parameter dictionary
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
            - run_n (int)           : run number
            - shuffle (bool)        : shuffle parameter
            - stimtype (str)        : stimulus type ('gabors' or 'bricks')
            - uniqueid (str)        : unique ID (datetime, 6 digit number or 
                                      None)
    """

    parts    = rundir.split(os.sep)
    param_str = parts[-2]
    run_str   = parts[-1]

    compdir_dict = sess_gen_util.get_params_from_str(param_str)

    if 'run' in run_str:
        compdir_dict['uniqueid'] = None
        compdir_dict['run_n']    = int(run_str.split('_')[1])
    else:
        compdir_dict['uniqueid'] = '_'.join([str(sub) for sub in 
                                             run_str.split('_')[:-1]])
        compdir_dict['run_n']    = int(run_str.split('_')[-1])    

    return compdir_dict


#############################################
def get_df_name(task='analyse', stimtype='gabors', comp='surp'):
    """
    get_df_name()

    Returns a dictionary with analysis parameters based on the full analysis 
    path.
    
    Optional args:
        - task (str)    : type of task for which to get the dataframe 
                          default: 'analyse'
        - stimtype (str): type of stimulus
                          default: 'gabors'
        - comp (str)    : type of comparison
                          default: 'surp'
    
    Returns:
        - df_name (str): name of the dataframe
    """

    if task == 'collate':
        df_name = '{}_{}_all_scores_df.csv'.format(stimtype[0:3], comp)
    elif task == 'analyse':
        df_name = '{}_{}_score_stats_df.csv'.format(stimtype[0:3], comp)
    
    return df_name


#############################################
def info_dict(analyspar=None, sesspar=None, stimpar=None, extrapar=None, 
              comp='surp', n_rois=None, epoch_n=None):
    """
    info_dict()

    Returns an info dictionary from the parameters. Includes epoch number if it 
    is passed. 

    Returns an ordered list of keys instead if any of the dictionaries or
    namedtuples are None.
    
    Required args:
        - analyspar (AnalysPar): named tuple containing analysis parameters
                                 default: None
        - sesspar (SessPar)    : named tuple containing session parameters
                                 default: None
        - stimpar (SessPar)    : named tuple containing stimulus parameters
                                 default: None
        - extrapar (dict)      : dictionary with extra parameters
                                 default: None
            ['run_n'] (int)   : run number
            ['shuffle'] (bool): whether data is shuffled
            ['uniqueid'] (str): uniqueid

        - comp (str)           : comparison type
                                 default: 'surp'
        - n_rois (int)         : number of ROIs
                                 default: None
        - epoch_n (int)        : epoch number
                                 default: None
    
    Returns:
        if all namedtuples and dictionaries are passed:
            - info (dict): analysis dictionary
        else if any are None:
            - info (list): list of dictionary keys
    """

    if not any(par is None for par in [analyspar, sesspar, stimpar, extrapar]):
        if stimpar.stimtype == 'bricks':
            bri_dir = gen_util.list_if_not(stimpar.bri_dir)
            if len(bri_dir) == 2:
                bri_dir = 'both'
            else:
                bri_dir = bri_dir[0]
        else:
            bri_dir = stimpar.bri_dir

        info = {'mouse_n' : sesspar.mouse_n,
                'sess_n'  : sesspar.sess_n,
                'layer'   : sesspar.layer,
                'line'    : sesspar.line,
                'fluor'   : analyspar.fluor,
                'scale'   : analyspar.scale,
                'shuffle' : extrapar['shuffle'],
                'stimtype': stimpar.stimtype,
                'bri_dir' : bri_dir,
                'comp'    : comp,
                'uniqueid': extrapar['uniqueid'],
                'run_n'   : extrapar['run_n'],
                'runtype' : sesspar.runtype,
                'n_rois'  : n_rois
                }

        if epoch_n is not None:
            info['epoch_n'] = epoch_n

    # if no args are passed, just returns keys
    else:
        info = ['mouse_n', 'sess_n', 'layer', 'line', 'fluor', 'scale', 
                'shuffle', 'stimtype', 'bri_dir', 'comp', 'uniqueid', 'run_n', 
                'runtype', 'n_rois', 'epoch_n']

    return info


#############################################
def save_hyperpar(analyspar, logregpar, sesspar, stimpar, extrapar): 
    """
    save_hyperpar(analyspar, logregpar, sesspar, stimpar, extrapar)

    Saves the hyperparameters for an analysis.
    
    Required args:
        - analyspar (AnalysPar): named tuple containing analysis parameters
        - logregpar (LogRegPar): named tuple containing logistic regression 
                                 parameters
        - sesspar (SessPar)    : named tuple containing session parameters
        - stimpar (SessPar)    : named tuple containing stimulus parameters
        - extrapar (dict)      : dictionary with extra parameters
            ['dirname'] (str): directory in which to save hyperparameters
    
    Returns:
        - hyperpars (dict): hyperparameter dictionary with inputs as keys and 
                            named tuples converted to dictionaries
    """

    hyperpars = {'analyspar': analyspar._asdict(),
                 'logregpar': logregpar._asdict(),
                 'sesspar'  : sesspar._asdict(),
                 'stimpar'  : stimpar._asdict(),
                 'extrapar' : extrapar
                }

    file_util.saveinfo(hyperpars, 'hyperparameters.json', extrapar['dirname'])

    return hyperpars


#############################################
def get_classes(comp='surp'):
    """
    get_classes()

    Returns names for classes based on the comparison type.
    
    Optional args:
        - comp (str)  : type of comparison
                        default: 'surp'
    
    Returns:
        - classes (list)      : list of class names
    """

    if comp == 'surp':
        classes = ['Regular', 'Surprise']
    elif comp in ['AvB', 'AvC', 'BvC', 'DvE']:
        classes = ['Gabor {}'.format(fr) for fr in [comp[0], comp[2]]]    
    else:
        gen_util.accepted_values_error('comp', comp, ['surp', 'AvB', 'AvC', 
                                       'BvC', 'DvE'])

    return classes


#############################################
def get_sess_data(sess, analyspar, stimpar, quintpar):
    """
    get_sess_data(sess, analyspar, stimpar, quintpar)

    Print session information and returns ROI trace segments, target classes 
    and class information and number of surprise segments in the dataset.
    
    Required args:
        - sess (Session)       : session
        - analyspar (AnalysPar): named tuple containing analysis parameters        
        - stimpar (StimPar)    : named tuple containing stimulus parameters
        - quintpar (QuintPar)  : named tuple containing quintile parameters

    Optional args:
        - q1v4 (bool) : if True, analysis is separated across first and last
                         quintiles
                         default: False
 
    Returns:
        - roi_seqs (list)   : ROI trace sequences, listed by quintile, 
                              each structured as: 
                                  seqs x frames x ROIs
        - seg_classes (list): all sequence classes, listed by quintile,
                              each structured as:
                                  seq x 1
        - n_surps (list)    : number of surprise sequences, listed by quintile
    """

    stim = sess.get_stim(stimpar.stimtype)

    roi_seqs = []
    seq_classes = []

    n_qu = len(quintpar.qu_idx)

    classes = [0, 1]
    for cl in classes:
        surp = cl
        if stimpar.stimtype == 'gabors':
            gabfr_lett = sess_str_util.gabfr_letters(stimpar.gabfr)
            if len(gabfr_lett) == 2:
                surp = 'any'
        stimpar_sp = stimpar
        if stimpar.stimtype == 'gabors' and isinstance(gabfr_lett, list):
            gabfr_lett   = ', '.join(gabfr_lett)
            stimpar_dict = stimpar._asdict()
            stimpar_dict['gabfr'] = stimpar.gabfr[cl]
            stimpar_sp = sess_ntuple_util.init_stimpar(**stimpar_dict)

        qu_segs, _ = quint_analys.quint_segs(stim, stimpar_sp, 
                                      quintpar.n_quints, quintpar.qu_idx, surp)
        _, surp_ns = quint_analys.quint_segs(stim, stimpar_sp, 
                                             quintpar.n_quints, 
                                             quintpar.qu_idx, surp=1)
        qu_roi_tr = []
        qu_classes = []
        for segs in qu_segs:
            twop_fr = stim.get_twop_fr_per_seg(segs, first=True)
            roi_info = stim.get_roi_trace_array(twop_fr, stimpar_sp.pre, 
                                                stimpar.post, analyspar.fluor)
            # transpose to seqs x frames x ROIs
            qu_roi_tr.append(np.transpose(roi_info[1], [1, 2, 0]))
            qu_classes.append(np.full(roi_info[1].shape[1], cl))
        
        roi_seqs.append(qu_roi_tr)
        seq_classes.append(qu_classes)
        
    roi_seqs = [np.concatenate([roi_seqs[0][q], roi_seqs[1][q]], axis=0) 
                                                    for q in range(n_qu)]
    seq_classes = [np.concatenate([seq_classes[0][q], seq_classes[1][q]],
                                   axis=0) for q in range(n_qu)]
        
    log_var = np.log(np.var(np.concatenate(roi_seqs, axis=0)))
    n_fr, nrois = roi_seqs[0].shape[1:]

    if stimpar.stimtype == 'gabors':
        stim_info = '\nGab fr: {}\nGab K: {}'.format(gabfr_lett, stimpar.gabk)
    elif stimpar.stimtype == 'bricks':
        stim_info = '\nBri dir: {}\nBri size: {}'.format(stimpar.bri_dir, 
                                                         stimpar.bri_size)

    print('\nRuntype: {}\nMouse: {}\nSess: {}\nLayer: {}\nLine: {}\nFluor: {}'
          '\nROIs: {}{}\nFrames per seg: {}'
          '\nLogvar: {:.2f}'.format(sess.runtype, sess.mouse_n, sess.sess_n, 
                                    sess.layer, sess.line, analyspar.fluor, 
                                    nrois, stim_info, n_fr, log_var))

    return roi_seqs, seq_classes, surp_ns


#############################################
def sample_seqs(roi_seqs, seq_classes, n_surp):
    """
    sample_seqs(roi_seqs, seq_classes, n_surp)

    Samples sequences to correspond to the ratio of surprise to regular 
    sequences.
    
    Required args:
        - roi_seqs (3D array)   : array of all ROI trace sequences, structured 
                                  as: sequences x frames x ROIs
        - seq_classes (2D array): array of all sequence classes, structured as 
                                  classes x 1
        - n_surp (int)          : number of surprise sequences

    Returns:
        - roi_seqs (3D array)   : array of selected ROI trace sequences, 
                                  structured as sequences x frames x ROIs
        - seq_classes (2D array): array of sequence classes, structured as 
                                  classes x 1
    """
    class0_all = np.where(seq_classes == 0)[0]
    class1_all = np.where(seq_classes == 1)[0]
    n_reg = (len(class0_all) + len(class1_all))//2 - n_surp

    class0_idx = np.random.choice(class0_all, n_reg, replace=False)
    class1_idx = np.random.choice(class1_all, n_surp, replace=False)
    
    roi_seqs = np.concatenate([roi_seqs[class0_idx], roi_seqs[class1_idx]], 
                              axis=0)

    seq_classes = np.concatenate([seq_classes[class0_idx], 
                                  seq_classes[class1_idx]], axis=0)
    return roi_seqs, seq_classes


#############################################
def init_comp_model(roi_seqs, seq_classes, logregpar, extrapar, scale='roi', 
                    device='cpu', thresh_cl=2):
    """
    init_comp_model(roi_seqs, seq_classes, logregpar, extrapar)

    Initializes and returns the comparison model and dataloaders.
    
    Required args:
        - roi_seqs (list)       : list of 3D arrays of selected ROI trace 
                                  sequences per quintile (max 2), structured as 
                                      sequences x frames x ROIs
        - seq_classes (list)    : list of 2D arrays of sequence classes per
                                  quintile (max 2), structured as 
                                      classes x 1
        - logregpar (LogRegPar) : named tuple containing logistic regression 
                                  parameters
        - extrapar (dict)       : dictionary with extra parameters
            ['shuffle'] (bool): if True, data is shuffled
    
    Optional args:
        - scale (str)    : type of scaling to use 
                           (e.g., 'roi', 'all', or 'none')
                           default: 'roi'
        - device (str)   : device to use
                           default: 'cpu'
        - thresh_cl (int): size threshold for classes in each non empty set 
                           beneath which the indices are reselected (only if
                           targets are passed). Not checked if thresh_cl is 0.
                           default: 2

    Returns:
        - model (torch.nn.Module)        : Neural network module with optimizer 
                                           and loss function as attributes
        - dls (list of torch DataLoaders): list of torch DataLoaders for 
                                           each set. If a set is empty, the 
                                           corresponding dls value is None.
        - extrapar (dict)                : dictionary with extra parameters
            ['cl_wei'] (list)      : list of weights for each class
            ['loss_name'] (str)    : name of the loss function used
            ['sc_facts'] (list)    : high percentile value(s) with which to
                                     scale
            ['shuffle'] (bool)     : if True, data is shuffled
            ['shuff_reidx'] (list) : list of indices with which targets were 
                                     shuffled 
    """

    if scale == 'roi':
        scale = 'last' # by last dimension

    if len(roi_seqs) > 2:
        raise ValueError(('Must pass data for no more than 2 quintiles, but '
                          'found {}.'.format(len(roi_seqs))))

    dl_info = data_util.create_dls(roi_seqs[0], seq_classes[0], 
                                   train_p=logregpar.train_p, sc_dim=scale, 
                                   sc_type='min_max', extrem='perc', 
                                   shuffle=extrapar['shuffle'], 
                                   batchsize=logregpar.batchsize, 
                                   thresh_cl=thresh_cl)
    dls = dl_info[0]

    extrapar = copy.deepcopy(extrapar)

    if scale not in ['None', 'none']:
       extrapar['sc_facts'] = dl_info[-1]
    
    if len(roi_seqs) == 2:
        class_vals = seq_classes[1]
        if extrapar['shuffle']:
            np.random.shuffle(class_vals)
        if scale not in ['None', 'none']:
            roi_seqs[1] = data_util.scale_datasets(torch.Tensor(roi_seqs[1]), 
                                              sc_facts=extrapar['sc_facts'])[0]
        dls.append(data_util.init_dl(roi_seqs[1], class_vals, 
                                     logregpar.batchsize))

    if extrapar['shuffle']:
        extrapar['shuff_reidx'] = dl_info[1]
 
    # from train targets
    extrapar['cl_wei'] = logreg_util.class_weights(dls[0].dataset.targets) 

    n_fr, n_rois  = roi_seqs[0].shape[1:]
    model         = logreg_util.LogReg(n_rois, n_fr).to(device)
    model.opt     = torch.optim.Adam(model.parameters(), lr=logregpar.lr, 
                                     weight_decay=logregpar.L2reg)
    model.loss_fn = logreg_util.weighted_BCE(extrapar['cl_wei'])
    extrapar['loss_name'] = model.loss_fn.name
    
    return model, dls, extrapar


#############################################
def save_scores(info, scores, key_order=None, dirname='.'):
    """
    save_scores(args, scores, saved_eps)

    Saves run information and scores per epoch as a dataframe.
    
    Required args:
        - info (dict)          : dictionary of parameters (see info_dict())
        - scores (pd DataFrame): dataframe of recorded scores
    
    Optional args:
        - key_order (list): ordered list of keys
                            default: None
        - dirname (str)   : directory in which to save scores
                            default: '.'
    
    Returns:
        - summ_df (pd DataFrame): dataframe with scores and recorded parameters
    """

    summ_df = copy.deepcopy(scores)

    if key_order is None:
        key_order = info.keys()

    for key in reversed(key_order):
        if key in info.keys():
            summ_df.insert(0, key, info[key])

    file_util.saveinfo(summ_df, 'scores_df.csv', dirname)

    return summ_df


#############################################
def single_run(run_n, analyspar, logregpar, quintpar, sesspar, stimpar, 
               extrapar, techpar, sess_data):
    """
    single_run(run, analyspar, logregpar, quintpar, sesspar, stimpar, extrapar, 
               techpar, sess_data)

    Does a single run of a logistic regression on the specified comparison
    and session data. Records hyperparameters, best model, last model, 
    tr_stats dictionary. Plots scores and training statistics. 
    
    Required args:
        - run_n (int)          : run number
        - analyspar (AnalysPar): named tuple containing analysis parameters
        - logregpar (LogRegPar): named tuple containing logistic regression 
                                 parameters
        - quintpar (QuintPar)  : named tuple containing quintile parameters
        - sesspar (SessPar)    : named tuple containing session parameters
        - stimpar (SessPar)    : named tuple containing stimulus parameters
        - extrapar (dict)      : dictionary with extra parameters
            ['seed'] (int)    : seed to use
            ['shuffle'] (bool): if analysis is on shuffled data
            ['uniqueid'] (str): unique ID for the analysis
        - techpar (dict)       : dictionary with technical parameters
            ['compdir'] (str) : specific output comparison directory
            ['device'] (str)   : device to use (e.g., 'cpu' or 'cuda')
            ['output'] (str)   : main output directiory
            ['plt_bkend'] (str): plt backend to use (e.g., 'agg' or None)
            ['reseed'] (bool)  : if True, run is reseeded
        - sess_data (list): list of session data:
            - roi_seqs (list)   : ROI trace sequences, listed by quintile, 
                                  each structured as: 
                                    seqs x frames x ROIs
            - seg_classes (list): all sequence classes, listed by quintile,
                                  each structured as:
                                    seq x 1
            - n_surps (list)    : number of surprise sequences, listed by 
                                  quintile
    """
    
    # needs to be repeated within joblib
    if techpar['plt_bkend'] is not None:
        plt.switch_backend(techpar['plt_bkend']) 

    # set pyplot params
    plot_util.linclab_plt_defaults(font=['Arial', 'Liberation Sans'], 
                                 font_dir=os.path.join('..', 'tools', 'fonts'))

    extrapar = copy.deepcopy(extrapar)
    extrapar['run_n'] = run_n
    if techpar['reseed']: # reset seed         
        extrapar['seed'] = None
    extrapar['seed'] = gen_util.seed_all(extrapar['seed'], techpar['device'])
    
    rundir = get_rundir(extrapar['run_n'], extrapar['uniqueid'])
    extrapar['dirname'] = file_util.createdir([techpar['output'], 
                                               techpar['compdir'], rundir])
    extrapar['classes'] = get_classes(logregpar.comp)
    
    [roi_seqs, seq_classes, n_surp] = copy.deepcopy(sess_data)
    extrapar['n_rois']  = roi_seqs[0].shape[-1]
    for i in range(len(quintpar.qu_idx)):
        if logregpar.comp in ['AvB', 'AvC', 'BvC']: # select a random subsample
            roi_seqs[i], seq_classes[i] = sample_seqs(roi_seqs[i], 
                                                      seq_classes[i], n_surp[i])  
        if logregpar.bal: # balance classes
            roi_seqs[i], seq_classes[i] = data_util.bal_classes(roi_seqs[i], 
                                                                seq_classes[i])
    
    thresh_cl = 2
    if sesspar.runtype == 'pilot':
        thresh_cl = 1

    mod, dls, extrapar = init_comp_model(roi_seqs, seq_classes, logregpar, 
                                  extrapar, analyspar.scale, techpar['device'], 
                                  thresh_cl=thresh_cl)
    hyperpars = save_hyperpar(analyspar, logregpar, sesspar, stimpar, extrapar)

    if logregpar.q1v4:
        dl_names = ['train', 'test_Q4']
        plot_data = [dls[i].dataset.data for i in [0, -1]]
        plot_targ = [dls[i].dataset.targets for i in [0, -1]]
    else:
        dl_names = ['train', None]
        plot_data = [dls[0].dataset.data]
        plot_targ = [dls[0].dataset.targets]

    len_s   = stimpar.post - stimpar.pre
    tr_stats = {'n_rois': extrapar['n_rois']}
    for i in range(len(plot_data)): # get stats
        xran, class_stats, ns = logreg_util.get_stats(plot_data[i].numpy(), 
                                           plot_targ[i].numpy(), [0, 1], len_s, 
                                           analyspar.stats, analyspar.error)
        tr_stats['xran'] = xran.tolist()
        tr_stats['{}_class_stats'.format(dl_names[i])] = class_stats.tolist()
        tr_stats['{}_ns'.format(dl_names[i])] = ns

    file_util.saveinfo(tr_stats, 'tr_stats.json', extrapar['dirname'])

    scale_str = sess_str_util.scale_par_str(analyspar.scale, 'print')
    shuff_str = sess_str_util.shuff_par_str(extrapar['shuffle'], 'labels')
    print('\nRun: {}{}{}'.format(extrapar['run_n'], scale_str, shuff_str))

    info = info_dict(analyspar, sesspar, stimpar, extrapar, logregpar.comp, 
                     n_rois=tr_stats['n_rois'])
    scores = logreg_util.fit_model(info, logregpar.epochs, mod, dls, 
                                   techpar['device'], extrapar['dirname'], 
                                   ep_freq=techpar['ep_freq'], 
                                   test_dl2_name=dl_names[-1])

    print('Run {}: training done.\n'.format(extrapar['run_n']))

    # save scores in dataframe
    full_scores = save_scores(info, scores, key_order=info_dict(), 
                              dirname=extrapar['dirname'])

    # plot traces and scores
    logreg_plots.plot_traces_scores(hyperpars, tr_stats, full_scores, 
                                    plot_wei=True)

    plt.close('all')


#############################################
def run_regr(args):
    """
    run_regr(args)

    Does runs of a logistic regressions on the specified comparison and range
    of sessions.
    
    Required args:
        - args (Argument parser): parser with analysis parameters as attributes:
            bal (bool)            : if True, classes are balanced
            batchsize (int)       : nbr of samples dataloader will load per 
                                    batch
            bri_dir (str)         : brick direction to analyse
            bri_size (int or list): brick sizes to include
            comp (str)            : type of comparison
            datadir (str)         : data directory
            device (str)          : device name (i.e., 'cuda' or 'cpu')
            ep_freq (int)         : frequency at which to print loss to 
                                    console
            error (str)           : error to take, i.e., 'std' (for std 
                                    or quintiles) or 'sem' (for SEM or MAD)
            fluor (str)           : fluorescence trace type
            gabfr (int)           : gabor frame of reference if comparison 
                                    is 'surp'
            gabk (int or list)    : gabor kappas to include
            lr (float)            : model learning rate
            mouse_n (int)         : mouse number
            n_epochs (int)        : number of epochs
            n_reg (int)           : number of regular runs
            n_shuff (int)         : number of shuffled runs
            scale (str)           : type of scaling
            output (str)          : general directory in which to save 
                                    output
            parallel (bool)       : if True, runs are done in parallel
            plt_bkend (str)       : pyplot backend to use
            q1v4 (bool)           : if True, analysis is separated across 
                                    first and last quintiles
            reg (str)             : regularization to use
            runtype (str)         : type of run ('prod' or 'pilot')
            seed (int)            : seed to seed random processes with
            sess_n (int)          : session number
            stats (str)           : stats to take, i.e., 'mean' or 'median'
            stimtype (str)        : stim to analyse ('gabors' or 'bricks')
            train_p (list)        : proportion of dataset to allocate to 
                                    training
            uniqueid (str or int) : unique ID for analysis
    """

    args = copy.deepcopy(args)

    if args.datadir is None:
        args.datadir = os.path.join('..', 'data', 'AIBS') 

    if args.uniqueid == 'datetime':
        args.uniqueid = gen_util.create_time_str()

    reseed = False
    if args.seed in [None, 'None']:
        reseed = True

    # deal with parameters
    extrapar = {'uniqueid' : args.uniqueid,
                'seed'     : args.seed
               }
    
    techpar = {'reseed'   : reseed,
               'device'   : args.device,
               'parallel' : args.parallel,
               'plt_bkend': args.plt_bkend,
               'output'   : args.output,
               'ep_freq'  : args.ep_freq,
               'n_reg'    : args.n_reg,
               'n_shuff'  : args.n_shuff,
               }

    mouse_df = 'mouse_df.csv'

    stimpars = get_stimpars(args.comp, args.stimtype, args.bri_dir, 
                            args.bri_size, args.gabfr, args.gabk)
    analyspar = sess_ntuple_util.init_analyspar(args.fluor, stats=args.stats, 
                                            error=args.error, scale=args.scale)  
    if args.q1v4:
        quintpar = sess_ntuple_util.init_quintpar(4, [0, -1])
    else:
        quintpar = sess_ntuple_util.init_quintpar(1)
    logregpar = sess_ntuple_util.init_logregpar(args.comp, args.q1v4, 
                                        args.n_epochs, args.batchsize, args.lr, 
                                        args.train_p, args.L2reg, args.bal)
    omit_sess, omit_mice = sess_gen_util.all_omit(args.stimtype, args.runtype, 
                                   stimpars.bri_dir, stimpars.bri_size, 
                                   stimpars.gabk)

    sessids = sess_gen_util.get_sess_vals(mouse_df, 'sessid', args.mouse_n, 
                                          args.sess_n, args.runtype, 
                                          omit_sess=omit_sess, 
                                          omit_mice=omit_mice)
    if len(sessids) == 0:
        print(('No sessions found (mouse: {}, sess: {}, '
               'runtype: {})').format(args.mouse_n, args.sess_n, args.runtype))

    for sessid in sessids:
        # initialize first session
        sess = sess_gen_util.init_sessions(sessid, args.datadir, mouse_df, 
                                           args.runtype, fulldict=False)[0]
        
        sesspar = sess_ntuple_util.init_sesspar(sess.sess_n, False, sess.layer,
                                                sess.line, runtype=sess.runtype, 
                                                mouse_n=sess.mouse_n)

        sess_data = get_sess_data(sess, analyspar, stimpars, quintpar)

        for runs, shuffle in zip([techpar['n_reg'], techpar['n_shuff']], 
                                 [False, True]):
            extrapar['shuffle'] = shuffle
            techpar['compdir'] = sess_gen_util.get_analysdir(sesspar.mouse_n, 
                                            sesspar.sess_n, sesspar.layer, 
                                            analyspar.fluor, analyspar.scale, 
                                            stimpars.stimtype, stimpars.bri_dir, 
                                            stimpars.bri_size, stimpars.gabk, 
                                            logregpar.comp, extrapar['shuffle'])

            if techpar['parallel']:
                num_cores = multiprocessing.cpu_count()
                Parallel(n_jobs=num_cores)(delayed(single_run)
                        (run, analyspar, logregpar, quintpar, sesspar, stimpars, 
                         extrapar, techpar, sess_data) for run in range(runs))
            else:
                for run in range(runs):
                    single_run(run, analyspar, logregpar, quintpar, sesspar, 
                               stimpars, extrapar, techpar, sess_data)


#############################################
def collate_scores(direc, all_labels):
    """
    collate_scores(direc, all_labels)

    Collects the analysis information and scores from the last epoch recorded 
    for a run and returns in dataframe.
    
    Required args:
        - direc (str)      : path to the specific comparison run folder
        - all_labels (list): ordered list of columns to save to dataframe
    
    Return:
        - scores (pd DataFrame): Dataframe containing run analysis information
                                 and scores from the last epoch recorded.
    """

    print(direc)
 
    scores = pd.DataFrame()

    ep_info, hyperpars = logreg_util.get_scores(direc)

    if ep_info is None:
        comp_dict = get_compdir_dict(direc)
        comp_dict['scale'] = hyperpars['analyspar']['scale']
        comp_dict['runtype'] = hyperpars['sesspar']['runtype']
        comp_dict['line'] = hyperpars['sesspar']['line']
        comp_dict['n_rois'] = hyperpars['extrapar']['n_rois']
        for col in all_labels: # ensures correct order
            if col in comp_dict.keys():
                scores.loc[0, col] = comp_dict[col]
    else:
        for col in all_labels:
            scores.loc[0, col] = ep_info[col].item()

    return scores


#############################################
def run_collate(args):
    """
    run_collate(args)

    Collects the analysis information and scores from the last epochs recorded 
    for all runs for a comparison type, and saves to a dataframe.

    Overwrites any existing dataframe of collated data.  
    
    Required args:
        - args (Argument parser): parser with analysis parameters as attributes:
            bri_dir (str)  : brick direction
            comp (str)     : type of comparison
            output (str)   : general directory in which run information is 
                             located output
            parallel (bool): if True, run information is collected in parallel
            stimtype (str) : type of stimulus

    Returns:
        - all_scores (pd DataFrame): dataframe compiling all the scores for 
                                     logistic regression runs in the output 
                                     folder that correspond to the stimulus 
                                     type and comparison type criteria
    """

    args = copy.deepcopy(args)

    q1v4 = False
    if 'q1v4' in args.output:
        q1v4 = True

    gen_dirs = file_util.getfiles(args.output, 'subdirs', [args.stimtype[0:3], 
                                                           args.comp])
    if len(gen_dirs) == 0:
        print('No runs found.')
        return

    run_dirs = [run_dir for gen_dir in gen_dirs
                for run_dir in file_util.getfiles(gen_dir, 'subdirs')]
    
    if q1v4:
        ext_test_name = 'test_Q4'
    else:
        ext_test_name = None

    all_labels = info_dict() + \
                 logreg_util.get_sc_labs(True, ext_test_name=ext_test_name) + \
                 ['saved']

    if args.parallel:
        num_cores = multiprocessing.cpu_count()
        scores_list = Parallel(n_jobs=num_cores)(delayed(collate_scores)
                        (run_dir, all_labels) for run_dir in run_dirs)
        all_scores = pd.concat(scores_list)
        all_scores = all_scores[all_labels] # reorder
    else:
        all_scores = pd.DataFrame(columns=all_labels)
        for run_dir in run_dirs:
            scores = collate_scores(run_dir, all_labels)
            all_scores = all_scores.append(scores)

    # sort df by mouse, session, layer, line, fluor, scale, shuffle, stimtype,
    # bri_dir, comp, uniqueid, run_n, runtype
    sorter = info_dict()[0:13]
        
    all_scores = all_scores.sort_values(by=sorter).reset_index(drop=True)

    savename = get_df_name('collate', args.stimtype, args.comp)
    file_util.saveinfo(all_scores, savename, args.output, overwrite=True)

    return all_scores


#############################################
def calc_stats(scores_summ, curr_lines, curr_idx, CI=0.95, q1v4=False):
    """
    calc_stats(scores_summ, curr_lines, curr_idx)

    Calculates statistics on scores from runs with specific analysis criteria
    and records them in the summary scores dataframe.  
    
    Required args:
        - scores_summ (pd DataFrame): DataFrame containing scores summary
        - curr_lines (pd DataFrame) : DataFrame lines corresponding to specific
                                      analysis criteria
        - curr_idx (int)            : Current row in the scores summary 
                                      DataFrame 
    
    Optional args:
        - CI (float) : Confidence interval around which to collect percentile 
                       values
                       default: 0.95
        - q1v4 (bool): if True, analysis is separated across first and last 
                       quintiles
                       default: False

    Returns:
        - scores_summ (pd DataFrame): Updated DataFrame containing scores 
                                      summary
    """

    # score labels to perform statistics on
    if q1v4:
        ext_test_name = 'test_Q4'
    else:
        ext_test_name = None

    sc_labs = ['epoch_n'] + logreg_util.get_sc_labs(True, ext_test_name=ext_test_name)

    # percentiles to record
    ps, p_names = math_util.get_percentiles(CI)

    for sc_lab in sc_labs:
        if sc_lab in curr_lines.keys():
            cols = []
            vals = []
            for stat in ['mean', 'median']:
                cols.extend([stat])
                vals.extend([math_util.mean_med(curr_lines[sc_lab], stats=stat, 
                                                nanpol='omit')])
            for error in ['std', 'sem']:
                cols.extend([error])
                vals.extend([math_util.error_stat(curr_lines[sc_lab], 
                                    stats='mean', error=error, nanpol='omit')])
            # get 25th and 75th quartiles
            cols.extend(['q25', 'q75'])
            vals.extend(math_util.error_stat(curr_lines[sc_lab], 
                                   stats='median', error='std', nanpol='omit'))                                            
            # get other percentiles (for CI)
            cols.extend(p_names)
            vals.extend(math_util.error_stat(curr_lines[sc_lab], 
                            stats='median', error='std', nanpol='omit', qu=ps))
            
            # get MAD
            cols.extend(['mad'])
            vals.extend([math_util.error_stat(curr_lines[sc_lab], 
                            stats='median', error='sem', nanpol='omit')])

            # plug in values
            cols = ['{}_{}'.format(sc_lab, name) for name in cols]
            gen_util.set_df_vals(scores_summ, curr_idx, cols, vals)
    
    return scores_summ


#############################################
def run_analysis(args):  
    """
    run_analysis(args)

    Calculates statistics on scores from runs for each specific analysis 
    criteria and saves them in the summary scores dataframe.

    Overwrites any existing dataframe of analysed data.
    
    Required args:
        - args (Argument parser): parser with analysis parameters as 
                                  attributes:
            bri_dir (str)  : brick direction
            CI (float)     : confidence interval around which to collect 
                             percentile values
            comp (str)     : type of comparison
            output (str)   : general directory in which run information is 
                             located output
            parallel (bool): if True, run information is collected in parallel
            stimtype (str) : type of stimulus
    """

    args = copy.deepcopy(args)

    all_scores_df = run_collate(args)

    scores_summ = pd.DataFrame()

    q1v4 = False
    if 'q1v4' in args.output:
        q1v4 = True

    # common labels
    comm_labs = gen_util.remove_if(info_dict(), 
                                   ['uniqueid', 'run_n', 'epoch_n'])

    # get all unique comb of labels
    df_unique = all_scores_df[comm_labs].drop_duplicates()
    for _, df_row in df_unique.iterrows():
        vals = [df_row[x] for x in comm_labs]
        curr_lines = gen_util.get_df_vals(all_scores_df, comm_labs, vals)
        # assign values to current line in summary df
        curr_idx = len(scores_summ)
        gen_util.set_df_vals(scores_summ, curr_idx, comm_labs, vals)
        # calculate n_runs (without nans and with)
        scores_summ.loc[curr_idx, 'runs_total'] = len(curr_lines)
        scores_summ.loc[curr_idx, 'runs_nan'] = curr_lines['epoch_n'].isna().sum()
        # calculate stats
        scores_summ = calc_stats(scores_summ, curr_lines, curr_idx, args.CI, 
                                 q1v4)

    savename = get_df_name('analyse', args.stimtype, args.comp)
    
    file_util.saveinfo(scores_summ, savename, args.output, overwrite=True)


#############################################    
def run_plot(args):
    """
    run_plot(args)

    Plots summary data for a specific comparison, for each datatype in a 
    separate figure and saves figures. 

    Required args:
        - args (Argument parser): parser with analysis parameters as 
                                  attributes:
            bri_dir (str)  : brick direction
            CI (float)     : CI for shuffled data
            comp (str)     : type of comparison
            fluor (str)    : fluorescence trace type
            output (str)   : general directory in which summary dataframe 
                             is saved
            plt_bkend (str): pyplot backend to use
            scale (str)    : type of scaling
            stimtype (str) : stimulus type
    """
    
    savename = get_df_name('analyse', args.stimtype, args.comp)

    logreg_plots.plot_summ(args.output, savename, args.stimtype, args.comp,
                           args.bri_dir, args.fluor, args.scale, args.CI, 
                           args.plt_bkend)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--output', 
                        default=os.path.join('results', 'logreg_models'),
                        help='where to store output')
    parser.add_argument('--datadir', default=None, 
                        help=('data directory (if None, uses a directory '
                              'defined below'))
    parser.add_argument('--task', default='run_regr', 
                        help='run_regr, analyse or plot')

        # technical parameters
    parser.add_argument('--plt_bkend', default=None, 
                        help='switch mpl backend when running on server')
    parser.add_argument('--parallel', action='store_true', 
                        help='do runs in parallel.')
    parser.add_argument('--cuda', action='store_true', 
                        help='run on cuda.')
    parser.add_argument('--ep_freq', default=50, type=int,  
                        help='epoch frequency at which to print loss')
    parser.add_argument('--n_reg', default=50, type=int, help='n regular runs')
    parser.add_argument('--n_shuff', default=50, type=int, 
                        help='n shuffled runs')

        # logregpar
    parser.add_argument('--comp', default='surp', 
                        help='surp, AvB, AvC, BvC, DvE, all')
    parser.add_argument('--n_epochs', default=1000, type=int)
    parser.add_argument('--batchsize', default=200, type=int)
    parser.add_argument('--lr', default=0.0001, type=float, 
                        help='learning rate')
    parser.add_argument('--train_p', default=0.75, type=float, 
                        help='proportion of dataset used in training set')
    parser.add_argument('--L2reg', default=0, type=float, 
                        help='weight of L2 regularization to use')
    parser.add_argument('--q1v4', action='store_true', 
                        help='run on 1st quintile and test on last')
    parser.add_argument('--bal', action='store_true', 
                        help='if True, classes are balanced')

        # sesspar
    parser.add_argument('--mouse_n', default=1, type=int)
    parser.add_argument('--runtype', default='prod', help='prod or pilot')
    parser.add_argument('--sess_n', default='all')
    parser.add_argument('--layer', default='soma')
    
        # stimpar
    parser.add_argument('--stimtype', default='gabors', help='gabors or bricks')
    parser.add_argument('--gabk', default=16, type=int, 
                        help='gabor kappa parameter')
    parser.add_argument('--gabfr', default=0, type=int, 
                        help='starting gab frame if comp is surp')
    parser.add_argument('--bri_dir', default='both', help='brick direction')
    parser.add_argument('--bri_size', default=128, help='brick size')

        # analyspar
    parser.add_argument('--scale', default='roi', 
                        help='scaling data: none, all or roi (by roi)')
    parser.add_argument('--fluor', default='dff', help='raw or dff')
    parser.add_argument('--stats', default='mean', help='mean or median')
    parser.add_argument('--error', default='sem', help='std or sem')

        # extra parameters
    parser.add_argument('--seed', default=-1, type=int, 
                        help='manual seed (-1 for None)')
    parser.add_argument('--uniqueid', default='datetime', 
                        help=('passed string, \'datetime\' for date and time '
                              'or None for no uniqueid'))

        # CI parameter for analyse and plot tasks
    parser.add_argument('--CI', default=0.95, type=float, help='shuffled CI')


    args = parser.parse_args()

    args.device = gen_util.get_device(args.cuda)

    if args.plt_bkend is not None: # necessary for running on server
        plt.switch_backend(args.plt_bkend)
    
    # set pyplot params
    plot_util.linclab_plt_defaults(font=['Arial', 'Liberation Sans'], 
                                 font_dir=os.path.join('..', 'tools', 'fonts'))


    if args.runtype == 'pilot':
       args.output = '{}_pilot'.format(args.output)

    if args.q1v4:
        args.output = '{}_q1v4'.format(args.output)
    if args.bal:
        args.output = '{}_bal'.format(args.output)

    if args.comp == 'all':
        comps = ['surp', 'AvB', 'AvC', 'BvC', 'DvE']
    else:
        comps = gen_util.list_if_not(args.comp)


    for comp in comps:
        args.comp = comp
        print(('\nTask: {}\nStim: {} \nComparison: {}\n').format(args.task, 
                                                 args.stimtype, args.comp))

        if args.task == 'run_regr':
            run_regr(args)

        # collates regression runs and analyses accuracy
        elif args.task == 'analyse':
            run_analysis(args)

        elif args.task == 'plot':
            run_plot(args)
        
        else:
            gen_util.accepted_values_error('args.task', args.task, 
                                           ['run_regr', 'analyse', 'plot'])


