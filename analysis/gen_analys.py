"""
gen_analys.py

This script runs ROI and running trace analyses using a Session object with 
data generated by the AIBS experiments for the Credit Assignment Project.

Authors: Colleen Gillon

Date: October, 2018

Note: this code uses python 3.7.

"""

import copy
import glob
import os

from joblib import Parallel, delayed
import numpy as np
import scipy.stats as st

from analysis import pup_analys, ori_analys, quint_analys, signif_grps
from util import file_util, gen_util, math_util
from sess_util import sess_gen_util, sess_ntuple_util, sess_str_util
from plot_fcts import gen_analysis_plots as gen_plots


#############################################
def run_full_traces(sessions, analysis, analyspar, sesspar, figpar, 
                    datatype='roi'):
    """
    run_full_traces(sessions, analysis, analyspar, sesspar, figpar)

    Plots full traces across an entire session. If ROI traces are plotted,
    each ROI is scaled and plotted separately and an average is plotted.
    
    Saves results and parameters relevant to analysis in a dictionary.

    Required args:
        - sessions (list)      : list of Session objects
        - analysis (str)       : analysis type (e.g., 't')
        - analyspar (AnalysPar): named tuple containing analysis parameters
        - sesspar (SessPar)    : named tuple containing session parameters
        - figpar (dict)        : dictionary containing figure parameters
    
    Optional args:
        - datatype (str): type of data (e.g., 'roi', 'run')
    """

    dendstr_pr = sess_str_util.dend_par_str(analyspar.dend, sesspar.layer, 
                                            datatype, 'print')
    
    sessstr_pr = (f'session: {sesspar.sess_n}, '
                  f'layer: {sesspar.layer}{dendstr_pr}')

    datastr = sess_str_util.datatype_par_str(datatype)

    print((f'\nPlotting {datastr} traces across an entire '
           f'session\n({sessstr_pr}).'))

    figpar = copy.deepcopy(figpar)
    if figpar['save']['use_dt'] is None:
        figpar['save']['use_dt'] = gen_util.create_time_str()
    
    all_tr, roi_tr, all_edges, all_pars = [], [], [], []
    for sess in sessions:
        # get the block edges and parameters
        edge_fr, par_descs = [], []
        for stim in sess.stims:
            if datatype == 'roi':
                edges = [fr for d_fr in stim.block_ran_twop_fr for fr in d_fr]
            elif datatype == 'run':
                edges = [fr for d_fr in stim.block_ran_fr for fr in d_fr]
            else:
                gen_util.accepted_values_error('datatype', datatype, 
                                               ['roi', 'run'])
            edge_fr.extend(edges)
            # collect parameters for each block
            params = [pars for d_pars in stim.block_params for pars in d_pars]
            par_desc = []
            for pars in params:
                pars = [str(par) for par in pars]
                par_desc.append(sess_str_util.pars_to_desc('{}\n{}'.format(
                            stim.stimtype.capitalize(), ', '.join(pars[0:2]))))
            par_descs.extend(par_desc)
        if datatype == 'roi':
            nanpol = None
            if not analyspar.remnans:
                nanpol = 'omit'
            all_rois = sess.get_roi_traces(None, analyspar.fluor, 
                                           analyspar.remnans)
            full_tr = math_util.get_stats(all_rois, analyspar.stats, 
                                          analyspar.error, axes=0, 
                                          nanpol=nanpol).tolist()
            roi_tr.append(all_rois.tolist())
        elif datatype == 'run':
            full_tr = sess.get_run_speed(remnans=analyspar.remnans).tolist()
            roi_tr = None
        all_tr.append(full_tr)
        all_edges.append(edge_fr)
        all_pars.append(par_descs)

    extrapar = {'analysis': analysis,
                'datatype': datatype,
                }

    trace_info = {'all_tr'   : all_tr,
                  'all_edges': all_edges,
                  'all_pars' : all_pars
                  }

    sess_info = sess_gen_util.get_sess_info(sessions, analyspar.fluor)

    info = {'analyspar' : analyspar._asdict(),
            'sesspar'   : sesspar._asdict(),
            'extrapar'  : extrapar,
            'sess_info' : sess_info,
            'trace_info': trace_info
            }

    fulldir, savename = gen_plots.plot_full_traces(roi_tr=roi_tr, 
                                                    figpar=figpar, **info)
    file_util.saveinfo(info, savename, fulldir, 'json')
    

#############################################
def run_traces_by_qu_surp_sess(sessions, analysis, analyspar, sesspar, 
                               stimpar, quintpar, figpar, datatype='roi'):
    """
    run_traces_by_qu_surp_sess(sessions, analysis, analyspar, sesspar, 
                               stimpar, quintpar, figpar)

    Retrieves trace statistics by session x surp val x quintile and
    plots traces across ROIs by quintile/surprise with each session in a 
    separate subplot.
    
    Also runs analysis for one quintile (full data).
    
    Saves results and parameters relevant to analysis in a dictionary.

    Required args:
        - sessions (list)      : list of Session objects
        - analysis (str)       : analysis type (e.g., 't')
        - analyspar (AnalysPar): named tuple containing analysis parameters
        - sesspar (SessPar)    : named tuple containing session parameters
        - stimpar (StimPar)    : named tuple containing stimulus parameters
        - quintpar (QuintPar)  : named tuple containing quintile analysis 
                                 parameters
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

    print((f'\nAnalysing and plotting surprise vs non surprise {datastr} '
           f'traces by quintile ({quintpar.n_quints}) \n({sessstr_pr}'
           f'{dendstr_pr}).'))

    # modify quintpar to retain all quintiles
    quintpar_one  = sess_ntuple_util.init_quintpar(1, 0, '', '')
    n_quints      = quintpar.n_quints
    quintpar_mult = sess_ntuple_util.init_quintpar(n_quints, 'all')

    figpar = copy.deepcopy(figpar)
    if figpar['save']['use_dt'] is None:
        figpar['save']['use_dt'] = gen_util.create_time_str()
        
    for quintpar in [quintpar_one, quintpar_mult]:
        print(f'\n{quintpar.n_quints} quint')
        # get the stats (all) separating by session, surprise and quintiles    
        trace_info = quint_analys.trace_stats_by_qu_sess(sessions, analyspar, 
                                                  stimpar, quintpar.n_quints, 
                                                  quintpar.qu_idx, 
                                                  byroi=False, bysurp=True, 
                                                  datatype=datatype)
        extrapar = {'analysis': analysis,
                    'datatype': datatype,
                    }

        all_stats = [sessst.tolist() for sessst in trace_info[1]]
        trace_stats = {'x_ran'     : trace_info[0].tolist(),
                       'all_stats' : all_stats,
                       'all_counts': trace_info[2]
                      }

        sess_info = sess_gen_util.get_sess_info(sessions, analyspar.fluor)

        info = {'analyspar'  : analyspar._asdict(),
                'sesspar'    : sesspar._asdict(),
                'stimpar'    : stimpar._asdict(),
                'quintpar'   : quintpar._asdict(),
                'extrapar'   : extrapar,
                'sess_info'  : sess_info,
                'trace_stats': trace_stats
                }

        fulldir, savename = gen_plots.plot_traces_by_qu_surp_sess(figpar=figpar, 
                                                                  **info)
        file_util.saveinfo(info, savename, fulldir, 'json')

      
#############################################
def run_traces_by_qu_lock_sess(sessions, analysis, seed, analyspar, sesspar, 
                               stimpar, quintpar, figpar, datatype='roi'):
    """
    run_traces_by_qu_lock_sess(sessions, analysis, analyspar, sesspar, 
                               stimpar, quintpar, figpar)

    Retrieves trace statistics by session x quintile at the transition of
    regular to surprise sequences (or v.v.) and plots traces across ROIs by 
    quintile with each session in a separate subplot.
    
    Also runs analysis for one quintile (full data) with different surprise 
    lengths grouped separated 
    
    Saves results and parameters relevant to analysis in a dictionary.

    Required args:
        - sessions (list)      : list of Session objects
        - analysis (str)       : analysis type (e.g., 'l')
        - seed (int)           : seed value to use. (-1 treated as None)
        - analyspar (AnalysPar): named tuple containing analysis parameters
        - sesspar (SessPar)    : named tuple containing session parameters
        - stimpar (StimPar)    : named tuple containing stimulus parameters
        - quintpar (QuintPar)  : named tuple containing quintile analysis 
                                 parameters
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

    print((f'\nAnalysing and plotting surprise vs non surprise {datastr} '
           f'traces locked to surprise onset by quintile ({quintpar.n_quints}) '
           f'\n({sessstr_pr}{dendstr_pr}).'))

    seed = gen_util.seed_all(seed, 'cpu', print_seed=False)

    # modify quintpar to retain all quintiles
    quintpar_one  = sess_ntuple_util.init_quintpar(1, 0, '', '')
    n_quints      = quintpar.n_quints
    quintpar_mult = sess_ntuple_util.init_quintpar(n_quints, 'all')

    stimpar = sess_ntuple_util.get_modif_ntuple(stimpar, ['pre', 'post'], 
                                                [10.0, 10.0])

    figpar = copy.deepcopy(figpar)
    if figpar['save']['use_dt'] is None:
        figpar['save']['use_dt'] = gen_util.create_time_str()
        
    for baseline in [None, stimpar.pre]:
        basestr_pr = sess_str_util.base_par_str(baseline, 'print')
        for quintpar in [quintpar_one, quintpar_mult]:
            locks = ['surp', 'reg']
            if quintpar.n_quints == 1:
                locks.append('surp_split')
            # get the stats (all) separating by session and quintiles
            for lock in locks:
                print(f'\n{quitnpar.n_quints} quint, {lock} lock{basestr_pr}')
                if lock == 'surp_split':
                    trace_info = quint_analys.trace_stats_by_surp_len_sess(
                                            sessions, analyspar, stimpar, 
                                            quintpar.n_quints, quintpar.qu_idx, 
                                            byroi=False, nan_empty=True, 
                                            baseline=baseline, 
                                            datatype=datatype)
                else:
                    trace_info = quint_analys.trace_stats_by_qu_sess(sessions, 
                                         analyspar, stimpar, quintpar.n_quints, 
                                         quintpar.qu_idx, byroi=False, 
                                         lock=lock, nan_empty=True, 
                                         baseline=baseline, datatype=datatype)

                # for comparison, locking to middle of regular sample (1 quint)
                reg_samp = quint_analys.trace_stats_by_qu_sess(sessions, 
                                         analyspar, stimpar, 
                                         quintpar_one.n_quints, 
                                         quintpar_one.qu_idx, byroi=False, 
                                         lock='regsamp', nan_empty=True, 
                                         baseline=baseline, datatype=datatype)

                extrapar = {'analysis': analysis,
                            'datatype': datatype,
                            'seed'    : seed,
                            }

                all_stats = [sessst.tolist() for sessst in trace_info[1]]
                reg_stats = [regst.tolist() for regst in reg_samp[1]]
                trace_stats = {'x_ran'     : trace_info[0].tolist(),
                               'all_stats' : all_stats,
                               'all_counts': trace_info[2],
                               'lock'      : lock,
                               'baseline'  : baseline,
                               'reg_stats' : reg_stats,
                               'reg_counts': reg_samp[2]
                               }

                if lock == 'surp_split':
                    trace_stats['surp_lens'] = trace_info[3]

                sess_info = sess_gen_util.get_sess_info(sessions, 
                                                        analyspar.fluor)

                info = {'analyspar'  : analyspar._asdict(),
                        'sesspar'    : sesspar._asdict(),
                        'stimpar'    : stimpar._asdict(),
                        'quintpar'   : quintpar._asdict(),
                        'extrapar'   : extrapar,
                        'sess_info'  : sess_info,
                        'trace_stats': trace_stats
                        }

                [fulldir, 
                savename] = gen_plots.plot_traces_by_qu_lock_sess(
                                                        figpar=figpar, **info)
                file_util.saveinfo(info, savename, fulldir, 'json')

      
#############################################
def run_mag_change(sessions, analysis, seed, analyspar, sesspar, stimpar, 
                   permpar, quintpar, figpar, datatype='roi'):
    """
    run_mag_change(sessions, analysis, seed, analyspar, sesspar, stimpar, 
                   permpar, quintpar, figpar)

    Calculates and plots the magnitude of change in activity of ROIs between 
    the first and last quintile for non surprise vs surprise sequences.
    Saves results and parameters relevant to analysis in a dictionary.

    Required args:
        - sessions (list)      : list of Session objects
        - analysis (str)       : analysis type (e.g., 'm')
        - seed (int)           : seed value to use. (-1 treated as None) 
        - analyspar (AnalysPar): named tuple containing analysis parameters
        - sesspar (SessPar)    : named tuple containing session parameters
        - stimpar (StimPar)    : named tuple containing stimulus parameters
        - permpar (PermPar)    : named tuple containing permutation parameters
        - quintpar (QuintPar)  : named tuple containing quintile analysis 
                                 parameters
        - figpar (dict)        : dictionary containing figure parameters   

    Optional args:
        - datatype (str): type of data (e.g., 'roi', 'run') 
    """

    sessstr_pr = sess_str_util.sess_par_str(sesspar.sess_n, stimpar.stimtype,
                                       sesspar.layer, stimpar.bri_dir,
                                       stimpar.bri_size, stimpar.gabk, 'print')
    dendstr_pr = sess_str_util.dend_par_str(analyspar.dend, sesspar.layer, 
                                            datatype, 'print')
  
    datastr = sess_str_util.datatype_par_str(datatype)

    print((f'\nCalculating and plotting the magnitude changes in {datastr} '
           f'activity across quintiles \n({sessstr_pr}{dendstr_pr})'))

    
    if permpar.multcomp:
        print(('NOTE: Multiple comparisons not implemented for magnitude '
               'analysis. Setting to False.'))
        permpar = sess_ntuple_util.get_modif_ntuple(permpar, 'multcomp', False)

    # get full data: session x surp x quints of interest x [ROI x seq]
    integ_info = quint_analys.trace_stats_by_qu_sess(sessions, analyspar, 
                                stimpar, quintpar.n_quints, quintpar.qu_idx, 
                                bysurp=True, integ=True, ret_arr=True, 
                                datatype=datatype)
    all_counts = integ_info[-2]
    qu_data = integ_info[-1]

    # extract session info
    mouse_ns = [sess.mouse_n for sess in sessions]
    lines    = [sess.line for sess in sessions]

    if analyspar.remnans:
        nanpol = None
    else:
        nanpol = 'omit'

    seed = gen_util.seed_all(seed, 'cpu', print_seed=False)

    mags = quint_analys.qu_mags(qu_data, permpar, mouse_ns, lines, 
                                analyspar.stats, analyspar.error, 
                                nanpol=nanpol, op_qu='diff', op_surp='diff')

    # convert mags items to list
    mags = copy.deepcopy(mags)
    mags['all_counts'] = all_counts
    for key in ['mag_st', 'L2', 'mag_rel_th', 'L2_rel_th']:
        mags[key] = mags[key].tolist()

    sess_info = sess_gen_util.get_sess_info(sessions, analyspar.fluor)
    extrapar  = {'analysis': analysis,
                 'datatype': datatype,
                 'seed'    : seed
                 }

    info = {'analyspar': analyspar._asdict(),
            'sesspar': sesspar._asdict(),
            'stimpar': stimpar._asdict(),
            'extrapar': extrapar,
            'permpar': permpar._asdict(),
            'quintpar': quintpar._asdict(),
            'mags': mags,
            'sess_info': sess_info
            }
    
    fulldir, savename = gen_plots.plot_mag_change(figpar=figpar, **info)

    file_util.saveinfo(info, savename, fulldir, 'json')


#############################################
def run_autocorr(sessions, analysis, analyspar, sesspar, stimpar, autocorrpar, 
                 figpar, datatype='roi'):
    """
    run_autocorr(sessions, analysis, analyspar, sesspar, stimpar, autocorrpar, 
                 figpar)

    Calculates and plots autocorrelation during stimulus blocks.
    Saves results and parameters relevant to analysis in a dictionary.

    Required args:
        - sessions (list)          : list of Session objects
        - analysis (str)           : analysis type (e.g., 'a')
        - analyspar (AnalysPar)    : named tuple containing analysis parameters
        - sesspar (SessPar)        : named tuple containing session parameters
        - stimpar (StimPar)        : named tuple containing stimulus parameters
        - autocorrpar (AutocorrPar): named tuple containing autocorrelation 
                                     analysis parameters
        - figpar (dict)            : dictionary containing figure parameters

    Optional args:
        - datatype (str): type of data (e.g., 'roi', 'run')
    """

    sessstr_pr = sess_str_util.sess_par_str(sesspar.sess_n, stimpar.stimtype,
                                       sesspar.layer, stimpar.bri_dir,
                                       stimpar.bri_size, stimpar.gabk, 'print')
    dendstr_pr = sess_str_util.dend_par_str(analyspar.dend, sesspar.layer, 
                                            datatype, 'print')
  
    datastr = sess_str_util.datatype_par_str(datatype)

    print((f'\nAnalysing and plotting {datastr} autocorrelations ' 
           f'({sessstr_pr}{dendstr_pr}).'))

    xrans = []
    stats = []
    for sess in sessions:
        stim = sess.get_stim(stimpar.stimtype)
        all_segs = stim.get_segs_by_criteria(bri_dir=stimpar.bri_dir, 
                                             bri_size=stimpar.bri_size, 
                                             gabk=stimpar.gabk, by='block')
        sess_traces = []
        for segs in all_segs:
            if len(segs) == 0:
                continue
            segs = sorted(segs)
            # check that segs are contiguous
            if max(np.diff(segs)) > 1:
                raise NotImplementedError(('Segments used for autocorrelation '
                                           'must be contiguous within blocks.'))
            if datatype == 'roi':
                frame_edges = stim.get_twop_fr_by_seg([min(segs), max(segs)])
                fr = list(range(min(frame_edges[0]), max(frame_edges[1])+1))
                traces = sess.get_roi_traces(fr, fluor=analyspar.fluor, 
                                             remnans=analyspar.remnans)
            elif datatype == 'run':
                if autocorrpar.byitem != False:
                    raise ValueError(('autocorrpar.byitem must be False for '
                                      'running data.'))
                frame_edges = stim.get_stim_fr_by_seg([min(segs), max(segs)])
                fr = list(range(min(frame_edges[0]), max(frame_edges[1])+1))
                
                traces = sess.get_run_speed_by_fr(fr, fr_type='stim', 
                            remnans=analyspar.remnans)[np.newaxis, :]
                
            sess_traces.append(traces)
        xran, ac_st = math_util.autocorr_stats(sess_traces, autocorrpar.lag_s, 
                                  sess.twop_fps, byitem=autocorrpar.byitem, 
                                  stats=analyspar.stats, error=analyspar.error)
        if not autocorrpar.byitem: # also add a 10x lag
            lag_fr = 10 * int(autocorrpar.lag_s * sess.twop_fps)
            _, ac_st_10x = math_util.autocorr_stats(sess_traces, lag_fr, 
                                                byitem=autocorrpar.byitem, 
                                                stats=analyspar.stats, 
                                                error=analyspar.error)
            downsamp = range(0, ac_st_10x.shape[-1], 10)
            if len(downsamp) != ac_st.shape[-1]:
                raise ValueError(('Failed to downsample correctly. '
                                  'Check implementation.'))
            ac_st = np.stack([ac_st, ac_st_10x[:, downsamp]], axis=1)
        xrans.append(xran)
        stats.append(ac_st)

    autocorr_data = {'xrans': [xran.tolist() for xran in xrans],
                     'stats': [stat.tolist() for stat in stats]
                     }

    sess_info = sess_gen_util.get_sess_info(sessions, analyspar.fluor)
    extrapar  = {'analysis': analysis,
                 'datatype': datatype,
                 }

    info = {'analyspar'     : analyspar._asdict(),
            'sesspar'       : sesspar._asdict(),
            'stimpar'       : stimpar._asdict(),
            'extrapar'      : extrapar,
            'autocorrpar'   : autocorrpar._asdict(),
            'autocorr_data' : autocorr_data,
            'sess_info'     : sess_info
            }

    fulldir, savename = gen_plots.plot_autocorr(figpar=figpar, **info)

    file_util.saveinfo(info, savename, fulldir, 'json')


#############################################
def run_trace_corr_acr_sess(sessions, analysis, analyspar, sesspar, 
                            stimpar, figpar, datatype='roi'):
    """
    run_trace_corr_acr_sess(sessions, analysis, analyspar, sesspar, 
                             stimpar, quintpar, figpar)

    Retrieves trace statistics by session x surp val and calculates 
    correlations across sessions per surp val.
    
    Currently only prints results to the console. Does NOT save results and 
    parameters relevant to analysis in a dictionary.

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
    # dendstr_pr = sess_str_util.dend_par_str(analyspar.dend, sesspar.layer, 
    #                                         datatype, 'print')
       
    datastr = sess_str_util.datatype_par_str(datatype)

    if sesspar.layer in ['any', 'all'] and sesspar.runtype == 'pilot':
        print('WARNING: Layers may not match between sessions for a mouse!')

    print(('\nAnalysing and plotting correlations between surprise vs non '
           f'surprise {datastr} traces between sessions ({sessstr_pr}).'))

    figpar = copy.deepcopy(figpar)
    if figpar['save']['use_dt'] is None:
        figpar['save']['use_dt'] = gen_util.create_time_str()
    
    # correlate average traces between sessions for each mouse and each surprise
    # value   
    all_counts = []
    all_me_tr = []
    all_corrs = []
    print('\nIntramouse correlations')
    for sess_grp in sessions:
        print((f'Mouse {sess_grp[0].mouse_n}, sess {sess_grp[0].sess_n} vs '
               f'{sess_grp[1].sess_n} corr:'))
        trace_info = quint_analys.trace_stats_by_qu_sess(sess_grp, analyspar, 
                                            stimpar, 1, [0], byroi=False, 
                                            bysurp=True, datatype=datatype)
        # remove quint dim
        grp_stats = np.asarray(trace_info[1]).squeeze(2) 
        all_counts.append([[qu_c[0] for qu_c in c] for c in trace_info[2]])
        # get mean/median per grp (sess x surp_val x frame)
        grp_me = grp_stats[:, :, 0]
        grp_corrs = []
        for s, surp in enumerate(['reg', 'surp']):
            # numpy corr
            # corr = float(np.correlate(grp_me[0, s], grp_me[1, s]))
            corr = st.pearsonr(grp_me[0, s], grp_me[1, s])
            grp_corrs.append(corr[0])
            print(f'    {surp}: {corr[0]:.4f} (p={corr[1]:.2f})')
        all_corrs.append(grp_corrs)
        all_me_tr.append(grp_me)
        
    # mice x sess x surp x frame
    all_me_tr = np.asarray(all_me_tr)
    print('\nIntermouse correlations')
    all_mouse_corrs = []
    for n, m1_sess_mes in enumerate(all_me_tr):
        if n + 1 < len(all_me_tr):
            mouse_corrs = []
            for n_add, m2_sess_mes in enumerate(all_me_tr[n+1:]):
                sess_corrs = []
                print((f'Mouse {sessions[n][0].mouse_n} vs '
                       f'{sessions[n+1+n_add][0].mouse_n} corr:'))
                for se, m1_s1_me in enumerate(m1_sess_mes):
                    surp_corrs = []
                    print(f'    sess {sessions[n][se].sess_n}:')
                    for s, surp in enumerate(['reg', 'surp']):
                        # numpy corr
                        # corr = float(np.correlate(m1_s1_me[s], 
                        #                           m2_sess_mes[se][s]))
                        corr = st.pearsonr(m1_s1_me[s], m2_sess_mes[se][s])
                        surp_corrs.append(corr[0])
                        print(f'\t{surp}: {corr[0]:.4f} (p={corr[1]:.2f})')
                    sess_corrs.append(corr)
                mouse_corrs.append(sess_corrs)
            all_mouse_corrs.append(mouse_corrs)

    # CURRENTLY RESULTS ARE ONLY PRINTED TO THE CONSOLE, NOT SAVED
    # extrapar = {'analysis': analysis,
    #             'datatype': datatype,
    #             }

    # corr_data = {'all_corrs'      : all_corrs,
    #              'all_mouse_corrs': all_mouse_corrs,
    #              'all_counts'     : all_counts
    #             }
    
    # sess_info = []
    # for sess_grp in sessions:
    #     sess_info.append(sess_gen_util.get_sess_info(sess_grp, analyspar.fluor))

    # info = {'analyspar': analyspar._asdict(),
    #         'sesspar'  : sesspar._asdict(),
    #         'stimpar'  : stimpar._asdict(),
    #         'extrapar' : extrapar,
    #         'sess_info': sess_info,
    #         'corr_data': corr_data
    #         }

    # savename = 'trace_corr' # should be modified to include session info
    # file_util.saveinfo(info, savename, fulldir, 'json')


