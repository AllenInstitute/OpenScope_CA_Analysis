"""
pup_analys.py

This module analyses pupil data generated by the AIBS experiments 
for the Credit Assignment Project.

Authors: Jay Pina and Colleen Gillon

Date: July, 2019

Note: this code uses python 3.7.

"""
import copy

from joblib import Parallel, delayed
import numpy as np

from util import file_util, gen_util, math_util
from sess_util import sess_gen_util, sess_str_util, sess_ntuple_util
from plot_fcts import pup_analysis_plots as pup_plots


#############################################
def get_ran_s(ran_s=None, datatype='both'):
    """
    get_ran_s()

    Ensures that ran_s is a dictionary and has the correct keys or initializes 
    it as a dictionary if needed, and returns it.

    Optional args:
        - ran_s (dict, list or num): number of frames to take before and after 
                                     surprise for each datatype (ROI, run, 
                                     pupil) (in sec). 
                                        If dictionary, expected keys are:
                                            'pup_pre', 'pup_post', 
                                            ('roi_pre', 'roi_post'), 
                                            ('run_pre', 'run_post'), 
                                        If list, should be structured as 
                                        [pre, post] and the same values will be 
                                        used for all datatypes. 
                                        If num, the same value will be used 
                                            for all keys. 
                                        If None, all keys are initialized with 
                                            3.5.
        - datatype (str)           : if 'roi', roi keys are included, if 'run', 
                                     run keys are included. If 'both', all keys
                                     are included.
                                     default: 'both'
    Returns:                
        - ran_s (dict): dictionary specifying number of frames to take before 
                        and after surprise for each datatype (ROI, run, pupil), 
                        with keys: ('roi_pre', 'roi_post'), ('run_pre', 
                                   'run_post'), 'pup_pre', 'pup_post'
    """

    ran_s = copy.deepcopy(ran_s)

    keys = ['pup_pre', 'pup_post']
    if datatype in ['both', 'roi']:
        keys.extend(['roi_pre', 'roi_post'])
    if datatype in ['both', 'run']:
        keys.extend(['run_pre', 'run_post'])
    elif datatype not in ['both', 'run', 'roi']:
        gen_util.accepted_values_error('datatype', datatype, 
                                        ['both', 'roi', 'run'])

    if isinstance(ran_s, dict):
        missing = [key for key in keys if key not in ran_s.keys()]
        if len(missing) > 0:
            raise ValueError(('`ran_s` is missing keys: '
                              '{}').format((', ').join(missing)))
    else:
        if ran_s is None:
            vals = 3.5
        elif isinstance(ran_s, list):
            if len(ran_s) == 2:
                vals = ran_s[:]
            else:
                raise ValueError('If `ran_s` is a list, must be of length 2.')
        else:
            vals = [ran_s, ran_s]
        ran_s = dict()
        for key in keys:
            if 'pre' in key:
                ran_s[key] = vals[0]
            elif 'post' in key:
                ran_s[key] = vals[1]

    return ran_s


#############################################
def peristim_data(sess, stimpar, ran_s=None, datatype='both',
                  returns='diff', fluor='raw', stats='mean', 
                  remnans=True, first_surp=True, trans_all=False):
    """
    peristim_data(sess)

    Returns pupil, ROI and run data around surprise onset, or the difference 
    between post and pre surprise onset, or both.

    Required args:
        - sess (Session)   : session object
        - stimpar (StimPar): named tuple containing stimulus parameters

    Optional args:
        - ran_s (dict, list or num): number of frames to take before and after 
                                     surprise for each datatype (ROI, run, 
                                     pupil) (in sec).  
                                         If dictionary, expected keys are:
                                            'pup_pre', 'pup_post', 
                                            ('roi_pre', 'roi_post'), 
                                            ('run_pre', 'run_post'), 
                                        If list, should be structured as 
                                        [pre, post] and the same values will be 
                                        used for all datatypes. 
                                        If num, the same value will be used 
                                            for all keys. 
                                        If None, the values are taken from the
                                            stimpar pre and post attributes.
                                     default: None
        - datatype (str)           : type of data to include with pupil data, 
                                     'roi', 'run' or 'both'
                                     default: 'roi' 
        - returns (str)            : type of data to return (data around 
                                     surprise, difference between post and pre 
                                     surprise)
                                     default: 'diff'
        - fluor (str)              : if 'dff', dF/F is used, if 'raw', ROI 
                                     traces
                                     default: 'raw'
        - stats (str)              : measure on which to take the pre and post
                                     surprise difference: either mean ('mean') 
                                     or median ('median')
                                     default: 'mean'
        - remnans (bool)           : if True, removes ROIs with NaN/Inf values 
                                     anywhere in session and running array with
                                     NaNs linearly interpolated is used. If 
                                     False, NaNs are ignored in calculating 
                                     statistics for the ROI and running data 
                                     (always ignored for pupil data)
                                     default: True
        - first_surp (bool)        : if True, only the first of consecutive 
                                     surprises are retained
                                     default: True
        - trans_all (bool)         : if True, only ROIs with transients are 
                                     retained
                                     default: False

    Returns:
        if datatype == 'data' or 'both':
        - datasets (list): list of 2-3D data arrays, structured as
                               datatype (pupil, (ROI), (running)) x 
                               [trial x frames (x ROI)]
        elif datatype == 'diff' or 'both':
        - diffs (list)   : list of 1-2D data difference arrays, structured as
                               datatype (pupil, (ROI), (running)) x 
                               [trial (x ROI)]    
    """

    stim = sess.get_stim(stimpar.stimtype)

    # initialize ran_s dictionary if needed
    if ran_s is None:
        ran_s = [stimpar.pre, stimpar.post]
    ran_s = get_ran_s(ran_s, datatype)

    if first_surp:
        surp_segs = stim.get_segs_by_criteria(bri_dir=stimpar.bri_dir, 
                         bri_size=stimpar.bri_size, gabk=stimpar.gabk, 
                         surp=1, remconsec=True, by='seg')
        if stimpar.stimtype == 'gabors':
            surp_segs = [seg + stimpar.gabfr for seg in surp_segs]
    else:
        surp_segs = stim.get_segs_by_criteria(bri_dir=stimpar.bri_dir, 
                                              bri_size=stimpar.bri_size, 
                                              gabk=stimpar.gabk, 
                                              gabfr=stimpar.gabfr, 
                                              surp=1, remconsec=False, by='seg')
    
    surp_twopfr = stim.get_twop_fr_by_seg(surp_segs, first=True)
    surp_stimfr = stim.get_stim_fr_by_seg(surp_segs, first=True)
    surp_pupfr  = sess.get_pup_fr_by_twop_fr(surp_twopfr)

    # get data
    # trial x fr
    pup_data = stim.get_pup_diam_array(surp_pupfr, ran_s['pup_pre'], 
                                       ran_s['pup_post'], remnans=remnans)[1]
    datasets = [pup_data]
    datanames = ['pup']
    if datatype in ['roi', 'both']:
        # ROI x trial x fr
        roi_data = stim.get_roi_trace_array(surp_twopfr, ran_s['roi_pre'], 
                                ran_s['roi_post'], fluor=fluor, integ=False, 
                                remnans=remnans, transients=trans_all)[1]
        datasets.append(roi_data.transpose([1, 2, 0])) # ROIs last
        datanames.append('roi')
    if datatype in ['run', 'both']:
        # trial x fr
        run_data = stim.get_run_array(surp_stimfr, ran_s['run_pre'], 
                                      ran_s['run_post'], remnans=remnans)[1] 
        datasets.append(run_data)
        datanames.append('run')

    if remnans:
        nanpolgen = None
    else:
        nanpolgen = 'omit'

    if returns in ['diff', 'both']:
        for key in ran_s.keys():
            if 'pre' in key and ran_s[key] == 0:
                raise ValueError(('Cannot set pre to 0 if returns is '
                                  '`diff` or `both`.'))
        # get avg for first and second halves
        diffs = []
        for dataset, name in zip(datasets, datanames):
            if name == 'pup':
                nanpol = 'omit'
            else:
                nanpol = nanpolgen
            n_fr = dataset.shape[1]
            pre_s  = ran_s['{}_pre'.format(name)]
            post_s = ran_s['{}_post'.format(name)]
            split = int(np.round(pre_s/(pre_s + post_s) * n_fr)) # find 0 mark
            pre  = math_util.mean_med(dataset[:, :split], stats, 1, nanpol)
            post = math_util.mean_med(dataset[:, split:], stats, 1, nanpol)
            diffs.append(post - pre)

    if returns == 'data':
        return datasets
    elif returns == 'diff':
        return diffs
    elif returns == 'both':
        return datasets, diffs
    else:
        gen_util.accepted_values_error('returns', returns, 
                                       ['data', 'diff', 'both'])


#############################################
def run_pupil_diff_corr(sessions, analysis, analyspar, sesspar, 
                        stimpar, figpar, datatype='roi'):
    """
    run_pupil_diff_corr(sessions, analysis, analyspar, sesspar, 
                        stimpar, figpar)
    
    Calculates and plots between pupil and ROI/running changes
    locked to each surprise, as well as the correlation.

    Saves results and parameters relevant to analysis in a dictionary.

    Required args:
        - sessions (list)      : list of Session objects
        - analysis (str)       : analysis type (e.g., 't')
        - analyspar (AnalysPar): named tuple containing analysis parameters
        - sesspar (SessPar)    : named tuple containing session parameters
        - stimpar (StimPar)    : named tuple containing stimulus parameters
        - figpar (dict)        : dictionary containing figure parameters
    
    Optional args:
        - datatype (str): type of data (e.g., 'roi', 'run')
    """

    sessstr_pr = sess_str_util.sess_par_str(sesspar.sess_n, stimpar.stimtype, 
                                            sesspar.layer, stimpar.bri_dir, 
                                            stimpar.bri_size, stimpar.gabk,
                                            'print')
    dendstr_pr = sess_str_util.dend_par_str(analyspar.dend, sesspar.layer, 
                                            datatype, 'print')
       
    datastr = sess_str_util.datatype_par_str(datatype)

    print(('\nAnalysing and plotting correlations between surprise vs non '
           'surprise {} traces between sessions ({}{}).').format(datastr, 
                                                    sessstr_pr, dendstr_pr))

    sess_diffs = []
    sess_corr = []
    
    for sess in sessions:
        diffs = peristim_data(sess, stimpar, datatype=datatype, returns='diff', 
                              first_surp=True)
        [pup_diff, data_diff] = diffs 
        # trials (x ROIs)
        if datatype == 'roi':
            if analyspar.remnans:
                nanpol = None
            else:
                nanpol = 'omit'
            data_diff = math_util.mean_med(data_diff, analyspar.stats, 
                                            axis=-1, nanpol=nanpol)
        elif datatype != 'run':
            gen_util.accepted_values_error('datatype', datatype, 
                                            ['roi', 'run'])
    
        sess_corr.append(np.corrcoef(pup_diff, data_diff)[0, 1])
        sess_diffs.append([diff.tolist() for diff in [pup_diff, data_diff]])
    
    extrapar = {'analysis': analysis,
                'datatype': datatype,
                }
    
    corr_data = {'corrs': sess_corr,
                 'diffs': sess_diffs
                 }

    sess_info = sess_gen_util.get_sess_info(sessions, analyspar.fluor)
    
    info = {'analyspar': analyspar._asdict(),
            'sesspar'  : sesspar._asdict(),
            'stimpar'  : stimpar._asdict(),
            'extrapar' : extrapar,
            'sess_info': sess_info,
            'corr_data': corr_data
            }

    fulldir, savename = pup_plots.plot_pup_diff_corr(figpar=figpar, **info)

    file_util.saveinfo(info, savename, fulldir, 'json')


#############################################
def run_pup_roi_stim_corr(sessions, analysis, analyspar, sesspar, stimpar, 
                          figpar, datatype='roi', parallel=False):
    """
    run_pup_roi_stim_corr(sessions, analysis, analyspar, sesspar, stimpar, 
                          figpar)
    
    Calculates and plots correlation between pupil and ROI changes locked to
    surprise for gabors vs bricks.
    
    Saves results and parameters relevant to analysis in a dictionary.

    Required args:
        - sessions (list)      : list of Session objects
        - analysis (str)       : analysis type (e.g., 't')
        - analyspar (AnalysPar): named tuple containing analysis parameters
        - sesspar (SessPar)    : named tuple containing session parameters
        - stimpar (StimPar)    : named tuple containing stimulus parameters
        - figpar (dict)        : dictionary containing figure parameters
    
    Optional args:
        - datatype (str) : type of data (e.g., 'roi', 'run')
        - parallel (bool): if True, some of the analysis is parallelized across 
                           CPU cores
                           default: False
    """

    if datatype != 'roi':
        raise ValueError('Analysis only implemented for roi datatype.')
    
    stimtypes = ['gabors', 'bricks']
    if stimpar.stimtype != 'both':
        non_stimtype = stimtypes[1 - stimtypes.index(stimpar.stimtype)]
        print(('stimpar.stimtype will be set to `both`, but non default '
               '{} parameters are lost.').format(non_stimtype))
        stimpar_dict = stimpar._asdict()
        for key in list(stimpar_dict.keys()): # remove any 'none's
            if stimpar_dict[key] == 'none':
                stimpar_dict.pop(key)

    sessstr_pr = 'session: {}, layer: {}'.format(sesspar.sess_n, sesspar.layer)
    dendstr_pr = sess_str_util.dend_par_str(analyspar.dend, sesspar.layer, 
                                            datatype, 'print')
    stimstr_pr = []
    stimpars = []
    for stimtype in stimtypes:
        stimpar_dict['stimtype'] = stimtype
        stimpars.append(sess_ntuple_util.init_stimpar(**stimpar_dict))
        stimstr_pr.append(sess_str_util.stim_par_str(stimtype, 
                                   stimpars[-1].bri_dir, stimpars[-1].bri_size, 
                                   stimpars[-1].gabk, 'print'))
    stimpar_dict = stimpars[0]._asdict()
    stimpar_dict['stimtype'] = 'both'

    print(('\nAnalysing and plotting correlations between surprise vs non '
           'surprise ROI traces between sessions ({}{}).').format(sessstr_pr, 
                                                                  dendstr_pr))
    sess_corrs = []
    sess_roi_corrs = []
    for sess in sessions:
        stim_corrs = []
        for sub_stimpar in stimpars:
            diffs = peristim_data(sess, sub_stimpar, datatype='roi', 
                                  returns='diff', first_surp=True, 
                                  remnans=analyspar.remnans)
            [pup_diff, roi_diff] = diffs 
            nrois = roi_diff.shape[-1]
            if parallel:
                n_jobs = gen_util.get_n_jobs(nrois)
                corrs = Parallel(n_jobs=n_jobs)(delayed(np.corrcoef)
                (roi_diff[:, r], pup_diff) for r in range(nrois))
                corrs = np.asarray([corr[0, 1] for corr in corrs])
            else:
                corrs = np.empty(nrois)
                for r in range(nrois): # cycle through ROIs
                    corrs[r] = np.corrcoef(roi_diff[:, r], pup_diff)[0, 1]
            stim_corrs.append(corrs)
        sess_corrs.append(np.corrcoef(stim_corrs[0], stim_corrs[1])[0, 1])
        sess_roi_corrs.append([corrs.tolist() for corrs in stim_corrs])

    extrapar = {'analysis': analysis,
                'datatype': datatype,
                }
    
    corr_data = {'stim_order': stimtypes,
                 'roi_corrs' : sess_roi_corrs,
                 'corrs'     : sess_corrs
                 }

    sess_info = sess_gen_util.get_sess_info(sessions, analyspar.fluor)
    
    info = {'analyspar': analyspar._asdict(),
            'sesspar'  : sesspar._asdict(),
            'stimpar'  : stimpar_dict,
            'extrapar' : extrapar,
            'sess_info': sess_info,
            'corr_data': corr_data
            }

    fulldir, savename = pup_plots.plot_pup_roi_stim_corr(figpar=figpar, **info)

    file_util.saveinfo(info, savename, fulldir, 'json')


########################
# OTHER PLOTS



# #############################################
# def scale_sort_trace_data(tr_data, fig_type='byplot', dils=['dil', 'undil']):
#     """
#     scale_sort_trace_data(tr_data)

#     Returns a dictionary ROI traces scaled and sorted as specified.

#     Required args:        
#         - tr_data (dict): dictionary containing information to plot colormap.
#             ['n_seqs'] (list)    : ordered list of number of segs for each
#                                    dilation value
#             ['roi_me'] (dict)    : ordered list of trace mean/medians
#                                    for each ROI as 2D arrays or nested lists, 
#                                    structured as:
#                                        ROIs x frames, 
#                                    (NaN arrays for combinations with 0 seqs.)

#     Optional args:
#         - fig_type (str) : how to scale and sort ROIs, 
#                            i.e. each plot separately ('byplot'), or by a
#                                 dilation ('byundil', 'bydil')
#                            default: 'byplot'
#         - dils (list)    : dilation value names used in keys, ordered
#                            default: ['undil', 'dil']
    
#     Returns:
#         - scaled_sort_data_me (list): list sorted by dils of 2D arrays, 
#                                       structured as: ROIs x frames
#     """

#     sorted_data = []

#     scale_vals = []
#     sort_args = []
#     for data in tr_data['roi_me']:
#         min_vals = np.nanmin(data, axis=1).tolist()
#         max_vals = np.nanmax(data, axis=1).tolist()
#         scale_vals.append([min_vals, max_vals])
#         sort_args.append(np.argsort(np.argmax(data, axis=1)).tolist()) # sort order

#     for d, dil in enumerate(dils):
#         me = np.asarray(tr_data['roi_me'][d])
#         if tr_data['n_seqs'][d] == 0:
#             min_v, max_v = np.asarray(scale_vals[1-d])
#             sort_arg = sort_args[1-d]
#         elif fig_type == 'byplot':
#             min_v, max_v = np.asarray(scale_vals[d])
#             sort_arg = sort_args[d]
#         else:
#             min_v = np.nanmin(np.asarray([vals[0] for vals in scale_vals]), axis=0)
#             max_v = np.nanmax(np.asarray([vals[1] for vals in scale_vals]), axis=0)
#             if fig_type == 'by{}'.format(dil):
#                 sort_arg = sort_args[d]
#             elif fig_type == 'by{}'.format(dils[1-d]):
#                 sort_arg = sort_args[1-d]

#         me_scaled = ((me.T - min_v)/(max_v - min_v))[:, sort_arg]
#         sorted_data.append(me_scaled)                
    
#     return sorted_data


# #############################################
# def split_2p_colorplots(data, sess, stimtype='bricks', eyesec=3.5, runsec=3.5, 
#                         phtsec=3.5):

#     sessstr_pr = sess_str_util.sess_par_str(sesspar.sess_n, stimpar.stimtype, 
#                                             sesspar.layer, stimpar.bri_dir, 
#                                             stimpar.bri_size, stimpar.gabk,
#                                             'print')
#     dendstr_pr = sess_str_util.dend_par_str(analyspar.dend, sesspar.layer, 
#                                             datatype, 'print')
       
#     datastr = sess_str_util.datatype_par_str(datatype)

#     print(('\nAnalysing and plotting correlations between surprise vs non '
#            'surprise {} traces between sessions ({}{}).').format(datastr, 
#                                                     sessstr_pr, dendstr_pr))

#     sess_diffs = []
#     sess_corr = []
    
#     for sess in sessions:
#         data = peristim_data(sess, stimpar, datatype=datatype, returns='data', 
#                              first_surp=True)
        
#         [pup_data, data_data] = data 
#         pup_overall_mean = np.nanmean(pup_data) # dilation threshold


#         n_fr = dataset.shape[1]
#         pre_s  = ran_s['{}_pre'.format(name)]
#         post_s = ran_s['{}_post'.format(name)]
#         ratio = stimpar.pre/(stimpar.pre + stimpar.post)
#         pup_split = int(np.round( * pup_data.shape[1])) # find 0 mark



#         # trials (x ROIs)
#         if datatype == 'roi':
#             if analyspar.remnans:
#                 nanpol = None
#             else:
#                 nanpol = 'omit'
#             data_diff = math_util.mean_med(data_diff, analyspar.stats, 
#                                             axis=-1, nanpol=nanpol)
#         elif datatype != 'run':
#             gen_util.accepted_values_error('datatype', datatype, 
#                                             ['roi', 'run'])
    
#         sess_corr.append(np.corrcoef(pup_diff, data_diff)[0, 1])
#         sess_diffs.append([diff.tolist() for diff in [pup_diff, data_diff]])
    
#     extrapar = {'analysis': analysis,
#                 'datatype': datatype,
#                 }
    
#     corr_data = {'corrs': sess_corr,
#                  'diffs': sess_diffs
#                  }

#     sess_info = sess_gen_util.get_sess_info(sessions, analyspar.fluor)
    
#     info = {'analyspar': analyspar._asdict(),
#             'sesspar'  : sesspar._asdict(),
#             'stimpar'  : stimpar._asdict(),
#             'extrapar' : extrapar,
#             'sess_info': sess_info,
#             'corr_data': corr_data
#             }

#     fulldir, savename = pup_plots.plot_pup_diff_corr(figpar=figpar, **info)

#     file_util.saveinfo(info, savename, fulldir, 'json')




#     # trial x fr [x ROI]
#     [roi_data, run_data, pup_data] = data

#     if stimtype == 'bricks':
#         start = 1/2
#     else:
#         start = 0
#     pre = (1 - 2*start) * phtsec

#     # I actually just want the second half of the data
#     roi_data = roi_data[:, int(np.round(roi_data.shape[1]*start)):]
#     run_data = run_data[:, int(np.round(run_data.shape[1]*start)):]
#     pup_data = pup_data[:, int(np.round(pup_data.shape[1]*start)):]

#     print(roi_data.shape)

#     pup_overall_mean = np.nanmean(pup_data)
#     pup_trial_means = np.nanmean(pup_data, axis=-1) 
#     # pup_trial_mean = np.nanmean(pup_trial_means, axis=-1) # altern. threshold

#     dilated_trials = np.where(pup_trial_means > pup_overall_mean)[0].tolist()
#     undilated_trials = list(set(range(len(pup_data))) - set(dilated_trials))

#     dil_roi_data = np.nanmean(roi_data[dilated_trials], axis=0).T
#     undil_roi_data = np.nanmean(roi_data[undilated_trials], axis=0).T

#     if len(dilated_trials) == 0:
#         dil_roi_data = np.full_like(undil_roi_data, np.nan, dtype=np.double)
#     elif len(undilated_trials) == 0:
#         undil_roi_data = np.full_like(dil_roi_data, np.nan, dtype=np.double)

#     tr_data = {'roi_me': [dil_roi_data, undil_roi_data],
#                'n_seqs': [len(dilated_trials), len(undilated_trials)]}

#     cmap = plot_util.manage_mpl(cmap=True, nbins=100)

#     gentitle = (('Mouse {}, {} {}, sess {}, {}\nSurprise responses during '
#                  'high vs low pupil dilation').format(sess.mouse_n, sess.line, 
#                   sess.layer, sess.sess_n, stimtype))
#     dils = ['dil', 'undil']
#     nrois = roi_data.shape[-1]
#     yticks_ev = int(10 * np.max([1, np.ceil(nrois/100)])) # to avoid more than 10 ticks
#     print('Plotting colormaps\n')
#     for fig_type in ['byplot', 'bydil', 'byundil']:
#         tr_data['sorted_data'] = scale_sort_trace_data(tr_data, 
#                                       fig_type=fig_type, dils=dils)    

#         if fig_type in ['bydil', 'byundil']:
#             peak_sort = ' across plots'
#             scale_type = ' by {}ated data'.format(fig_type[2:])
#             sharey = True
#         else:
#             peak_sort = ''
#             scale_type = ' within plot'
#             sharey = False

#         subtitle = ('ROIs sorted by peak activity{} and '
#                     'scaled{}').format(peak_sort, scale_type)
#         fig, ax = plt.subplots(ncols=2, figsize=[30, 15], sharey=sharey)
        
#         for d, dil in enumerate(dils):    
#             sub_ax = ax[d]
#             title = u'{}ated seqs (n={})'.format(dil.capitalize(), 
#                                                  tr_data['n_seqs'][d])

#             sess_plot_util.add_axislabels(sub_ax, fluor='dff', 
#                                           y_ax='ROIs', datatype='roi')
#             im = plot_util.plot_colormap(sub_ax, tr_data['sorted_data'][d], 
#                                     title=title, cmap=cmap, 
#                                     yticks_ev=yticks_ev,
#                                     xran=[-pre, phtsec])
#             plot_util.add_bars(sub_ax, 0)
#         if stimtype == 'gabors':
#             t_hei = -0.02
#             gabfr = 3
#             sess_plot_util.plot_labels(ax, gabfr=gabfr, plot_vals='reg', 
#                             pre=pre, post=0, sharey=sharey, 
#                             t_heis=t_hei)
#             sess_plot_util.plot_labels(ax, gabfr=gabfr, plot_vals='surp', 
#                             pre=0, post=phtsec, sharey=sharey, 
#                             t_heis=t_hei)

#         plot_util.add_colorbar(fig, im, len(dils))
#         fig.suptitle('{}\n{}'.format(gentitle, subtitle))
#         fig.savefig('results/latest2/m{}_s{}_{}_cm_ext_{}_{}.png'.format(sess.mouse_n, 
#                                    sess.sess_n, sess.layer, stimtype, fig_type))
#         plt.close(fig)


# ############### CORRELATION BTW GABORS AND BRICKS


# def quick_run(sessid, stimtype='bricks', runtype='prod', roi_s=3.5, run_s=2, 
#               pup_s=3.5):

#     sess = session.Session('../data/AIBS', sessid=sessid, runtype=runtype)
#     sess.extract_sess_attribs()
#     sess.extract_info(fulldict=False, dend='extr')

#     try:
#         sess._load_pup_data()
#     except OSError as err:
#         print(err)
#         return

#     diffs = peristim_beh(sess, stimtype=stimtype, roi_s=roi_s, run_s=run_s, 
#                          pup_s=pup_s, datatype='diff', first_surp=True)

#     pup_2p_plots(diffs, sess, stimtype, roi_s, run_s, pup_s)


#     if stimtype == 'gabors': # to avoid doing it twice
#         gab_diffs = peristim_beh(sess, stimtype='gabors', roi_s=roi_s, 
#                                  run_s=run_s, pup_s=pup_s, datatype='diff', 
#                                  first_surp=True, trans_all=True)
#         bri_diffs = peristim_beh(sess, stimtype='bricks', roi_s=roi_s, 
#                                  run_s=run_s, pup_s=pup_s, datatype='diff', 
#                                  first_surp=True, trans_all=True)

#         pup_2p_ROI_plots(gab_diffs, bri_diffs, sess, stimtype, roi_s, run_s, 
#                          pup_s)

#     first_surp = True
#     roi_s, run_s, pup_s = [4, 4, 4]
#     if stimtype == 'gabors':
#         first_surp = True # also did False
#         roi_s, run_s, pup_s = [1.5, 1.5, 1.5]

#     data = peristim_beh(sess, stimtype=stimtype, roi_s=roi_s, run_s=run_s, 
#                         pup_s=pup_s, datatype='data', first_surp=first_surp)

#     split_2p_colorplots(data, sess, stimtype, roi_s, run_s, pup_s)

    