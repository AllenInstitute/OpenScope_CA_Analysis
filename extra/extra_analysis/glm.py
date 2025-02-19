"""
glm.py

This module contains functions to run and analyse GLMs predicting ROI activity
from stimulus and behavioural information for data generated by the Allen 
Institute OpenScope experiments for the Credit Assignment Project.

Authors: Colleen Gillon

Date: September, 2019

Note: this code uses python 3.7.

"""

import copy
import logging
import random

from joblib import Parallel, delayed
import numpy as np
import pandas as pd
from sklearn import linear_model, metrics, model_selection, pipeline, \
    preprocessing

from util import file_util, gen_util, logger_util, math_util, rand_util
from sess_util import sess_data_util, sess_gen_util, sess_str_util
from extra_plot_fcts import glm_plots

logger = logging.getLogger(__name__)


#############################################
def build_stim_beh_df(sessions, analyspar, sesspar, stimpar):
    """
    build_stim_beh_df(sessions, analyspar, sesspar, stimpar)

    Builds a dataframe containing the stimulus and behavioural information, for 
    each of the specified segments.

    Inputs: sessions, stimtype, segments, pre-post (pupil, running), pre-post 
    (ROI)

    GLM inputs:
    - Unexpected status (e.g., only 1 for U and the following grayscreen (G))
    - Pupil dilation, if not using pilot data
    - Running velocity
    - ROI data (by ROI)
    - Plane
    - Line
    - SessID
    - Stimulus parameters

    """

    full_df = pd.DataFrame()
    
    sessions = gen_util.list_if_not(sessions)
    pupil = (sesspar.runtype != "pilot")
    for sess in sessions:
        logger.info(f"Building dataframe for session {sess.sessid}", 
            extra={"spacing": "\n"})
        stim = sess.get_stim(stimpar.stimtype)
        sub_df = stim.get_stim_beh_sub_df(
            stimpar.pre, stimpar.post, analyspar.stats, analyspar.fluor, 
            analyspar.rem_bad, gabfr=stimpar.gabfr, gabk=stimpar.gabk, 
            gab_ori=stimpar.gab_ori, visflow_size=stimpar.visflow_size, 
            visflow_dir=stimpar.visflow_dir, pupil=pupil, run=True, 
            roi_stats=False
            )

        full_df = full_df.append(sub_df)
    
    # set unexpected status for any gabor frames other than D_U, G to 0.
    if "gabor_frame" in full_df.columns:
        full_df.loc[
            (~full_df["gabor_frame"].isin(["D", "U", "D_U", "G"])) & 
            (full_df["unexpected"] == 1), 
            "unexpected"
            ] = 0
        
    # set mean orientations to the sequence's expected frame orientation for 
    # unexpected frames
    if "gabor_mean_orientation" in full_df.columns:
        unique_oris = full_df.loc[
            (full_df["gabor_frame"].isin(["D", "U", "D_U", "G"])) &
            (full_df["unexpected"] == 1), 
            "gabor_mean_orientation"
            ].unique()
        for unique_ori in unique_oris:
            full_df.loc[
                (full_df["gabor_frame"].isin(["D", "U", "D_U", "G"])) &
                (full_df["unexpected"] == 1) &
                (full_df["gabor_mean_orientation"] == unique_ori), 
                "gabor_mean_orientation"
                ] = sess_gen_util.get_reg_gab_ori(unique_ori)
    
    # drop unnecessary or redundant columns
    drop = [
        "stimulus_template_name", # unnecessary
        "square_proportion_flipped", # redundant 
        "square_number", # redundant
        "gabor_number", # single value, NaN for "G" frames
        "gabor_locations_x", # full table / array / NaN for "G" frames
        "gabor_locations_y",  # full table / array / NaN for "G" frames
        "gabor_sizes", # full table / array / NaN for "G" frames
        "gabor_orientations" # full table / array / NaN for "G" frames

        ]
    drop_cols = [col for col in full_df.columns if col in drop]
    full_df = full_df.drop(columns=drop_cols)


    full_df = full_df.reset_index(drop=True)
    full_df = gen_util.drop_unique(full_df, in_place=True)

    return full_df


#############################################
def log_sklearn_results(model, analyspar, name="bayes_ridge", var_names=None):
    """
    log_sklearn_results(model, analyspar)
    """

    logger.info(f"{name.replace('_', ' ').upper()} regression", 
        extra={"spacing": "\n"})
    if var_names is None:
        var_names = [f"coef {i}" for i in range(len(model.coef_))] 

    results = "\n".join([f"{varn}: {coef:.5f}" for varn, coef 
        in zip(var_names, model.coef_)])
    logger.info(results)
    logger.info(f"intercept: {model.intercept_:.5f}")
    logger.info(f"alpha: {model.alpha_:.5f}", extra={"spacing": "\n"})
    if name == "ridge_cv":
        alpha_idx = np.where(model.alphas == model.alpha_)[0]
        score_data = model.cv_values_[:, alpha_idx]
        score_name = "MSE"
    elif name == "bayes_ridge":
        score_data = model.scores_
        score_name = "Score"
    else:
        gen_util.accepted_values_error(
            "name", name, ["ridge_cv", "bayes_ridge"])
    stats = math_util.get_stats(
        score_data, stats=analyspar.stats, error=analyspar.error)
    math_util.log_stats(stats, f"{score_name}")


#############################################
def run_ridge_cv(x_df, y_df, analyspar, alphas=None):
    """
    run_ridge_cv(x_df, y_df, analyspar)
    """

    if alphas is None:
        alphas=(0.1, 0.1, 2.0)

    steps = [("scaler", preprocessing.StandardScaler()), 
        ("model", linear_model.RidgeCV(
            normalize=True, alphas=alphas, store_cv_values=True))] 

    pipl = pipeline.Pipeline(steps)
    pipl.fit(x_df, y_df)

    log_sklearn_results(
        pipl, analyspar, name="ridge_cv", var_names=x_df.columns)

#############################################
def run_bayesian_ridge(x_df, y_df, analyspar):
    """
    run_bayesian_ridge(x_df, y_df, analyspar)
    """

    steps = [("scaler", preprocessing.StandardScaler()), 
        ("model", linear_model.BayesianRidge(compute_score=True))] 
    pipl = pipeline.Pipeline(steps)
    pipl.fit(x_df, y_df)

    log_sklearn_results(
        pipl, analyspar, name="bayes_ridge", var_names=x_df.columns)


#############################################
def fit_expl_var(x_df, y_df, train_idx, test_idx):
    """
    fit_expl_var(x_df, y_df, train_idx, test_idx)
    """

    x_df = sess_data_util.add_categ_stim_cols(copy.deepcopy(x_df))

    x_tr, y_tr     = x_df.loc[train_idx], y_df.loc[train_idx].to_numpy().ravel()
    x_test, y_test = x_df.loc[test_idx], y_df.loc[test_idx].to_numpy().ravel()

    # get explained variance
    steps = [("scaler", preprocessing.StandardScaler()), 
        ("model", linear_model.BayesianRidge(compute_score=True))] 
    pipl = pipeline.Pipeline(steps)
    pipl.fit(x_tr, y_tr)
    y_pred = pipl.predict(x_test)
    varsc = metrics.explained_variance_score(
        y_test, y_pred, multioutput="uniform_average")
    return varsc


#############################################
def is_bool_var(df_col):
    """
    is_bool_var(df_col)
    """

    if set(df_col.unique()).issubset({0, 1}):
        is_bool = True
    else:
        is_bool = False

    return is_bool


#############################################
def get_categ(col_name):
    """
    get_categ(col_name)
    """

    categ_symb = "$"
    if categ_symb in col_name:
        categ_name = col_name[ : col_name.find(categ_symb)]
    else:
        categ_name = col_name
    return categ_name


#############################################
def shuffle_col_idx(full_df, col, idx=None):
    """
    shuffle_col_idx(full_df, col)
    """

    full_df = copy.deepcopy(full_df)
    if idx is None:
        other_vals = full_df[col].tolist()
        random.shuffle(other_vals)
        full_df[col] = other_vals    
    else:
        other_vals = full_df.loc[idx, col].tolist()
        random.shuffle(other_vals)
        full_df.loc[idx, col] = other_vals
    return full_df


#############################################
def fit_expl_var_per_coeff(x_df, y_df, train_idx, test_idx):
    """
    fit_expl_var_per_coeff(x_df, y_df, train_idx, test_idx)
    """

    # get df with categorical variables split up
    x_df_cat = sess_data_util.add_categ_stim_cols(copy.deepcopy(x_df))
    
    x_cols     = x_df.columns
    x_cols_cat = x_df_cat.columns

    done = []
    expl_var = dict()
    for col in x_cols_cat:
        for run in ["full_categ", "single_categ_value"]:
            curr_x_df = copy.deepcopy(x_df)
            act = col
            key = col
            # categorical variables
            if is_bool_var(x_df_cat[col]):
                categ_name = get_categ(col)
                act = categ_name
                if run == "full_categ":
                    key = categ_name
                    if categ_name in done or categ_name == col:
                        continue
                    else:
                        done.append(categ_name)
                # shuffle the other instances of category
                elif run == "single_categ_value":
                    act_idx_tr = (x_df_cat.loc[train_idx, col] == 0)
                    curr_x_df.loc[train_idx] = shuffle_col_idx(
                        curr_x_df.loc[train_idx], categ_name, act_idx_tr)

            # shuffle all other columns
            for oth_col in x_cols:
                if oth_col != act:
                    curr_x_df.loc[train_idx] = shuffle_col_idx(
                        curr_x_df.loc[train_idx], oth_col)

            expl_var[key] = fit_expl_var(curr_x_df, y_df, train_idx, test_idx)
    
    return expl_var


#############################################
def fit_unique_expl_var_per_coeff(x_df, y_df, train_idx, test_idx, 
                                  full_expl_var):
    """
    fit_unique_expl_var_per_coeff(x_df, y_df, train_idx, test_idx, 
                                  full_expl_var):
    """

    # get df with categorical variables split up
    x_df_cat = sess_data_util.add_categ_stim_cols(copy.deepcopy(x_df))
    x_cols_cat = x_df_cat.columns

    expl_var = dict()
    done = []
    for col in x_cols_cat:
        if is_bool_var(x_df_cat[col]):
            categ_name = get_categ(col)
            if categ_name in done:
                continue
            else:
                done.append(categ_name)
                col = categ_name

        curr_x_df = copy.deepcopy(x_df)
        curr_x_df.loc[train_idx] = shuffle_col_idx(
            curr_x_df.loc[train_idx], col)
        varsc = fit_expl_var(curr_x_df, y_df, train_idx, test_idx)
        expl_var[col] = full_expl_var - varsc

    return expl_var


#############################################
def compile_dict_fold_stats(dict_list, analyspar):
    """
    compile_dict_fold_stats(dict_list, analyspar)
    """
    
    full_dict = dict()
    all_keys = dict_list[0].keys()
    for key in all_keys:
        fold_vals = np.asarray([sub_dict[key] for sub_dict in dict_list])
        me, de = math_util.get_stats(
            fold_vals, stats=analyspar.stats, error=analyspar.error)
        full_dict[key] = [me, de]
    return full_dict


#############################################
def scale_across_rois(y_df, tr_idx, sessids, stats="mean"):
    """
    scale_across_rois(y_df, tr_idx, sessids)
    """

    y_df_new = copy.deepcopy(y_df)
    sessid_vals = np.unique(sessids)

    tr_idx_set = set(tr_idx)
    for val in sessid_vals:
        all_idx_set = set(np.where(sessids == val)[0])
        curr_tr   = list(all_idx_set.intersection(tr_idx_set))
        curr_test = list(all_idx_set - tr_idx_set)

        scaled_tr, facts = math_util.scale_data(
            y_df.loc[curr_tr].to_numpy(), axis=0, sc_type="stand_rob", 
            nanpol="omit")
        acr_rois_tr   = math_util.mean_med(
            scaled_tr, stats=stats, axis=1, nanpol="omit")
        y_df_new.loc[curr_tr, "roi_data"] = acr_rois_tr

        scaled_test = math_util.scale_data(y_df.loc[curr_test].to_numpy(), 
            axis=0, sc_type="stand_rob", facts=facts, nanpol="omit")
        acr_rois_test = math_util.mean_med(
            scaled_test, stats=stats, axis=1, nanpol="omit")
        y_df_new.loc[curr_test, "roi_data"] = acr_rois_test

    y_df_new = y_df_new[["roi_data"]]

    return y_df_new


#############################################
def run_explained_variance(x_df, y_df, analyspar, k=10, log_roi_n=True):
    """
    run_explained_variance(x_df, y_df, analyspar)

    Consider splitting 80:20 for a test set?
    """

    x_df = copy.deepcopy(x_df)
    y_df_cols = y_df.columns

    if len(y_df_cols) > 1: # multiple ROIs (to scale and average)
        all_rois = True
        if "session_id" in x_df.columns:
            sessids = x_df["session_id"].tolist()
        else:
            sessids = [1] * len(x_df)
        logger.info("Calculating explained variance for all ROIs together...")
    else:
        all_rois = False
        if log_roi_n:
            roi_n = int(y_df_cols[0].replace('roi_data_', ''))
            logger.info(f"Calculating explained variance for ROI {roi_n}...")

    kf = model_selection.KFold(k, shuffle=True, random_state=None)

    full, coef_all, coef_uni = [], [], []
    for tr_idx, test_idx in kf.split(x_df):
        if all_rois:
            y_df = scale_across_rois(y_df, tr_idx, sessids, analyspar.stats)
        # one model per category
        full.append(fit_expl_var(x_df, y_df, tr_idx, test_idx))
        coef_all.append(fit_expl_var_per_coeff(
            x_df, y_df, tr_idx, test_idx))
        coef_uni.append(fit_unique_expl_var_per_coeff(
            x_df, y_df, tr_idx, test_idx, full[-1]))


    full = math_util.get_stats(
        np.asarray(full), stats=analyspar.stats, error=analyspar.error).tolist()

    coef_all = compile_dict_fold_stats(coef_all, analyspar)
    coef_uni = compile_dict_fold_stats(coef_uni, analyspar)

    return full, coef_all, coef_uni


#############################################
def run_glm(sessions, analyspar, sesspar, stimpar, glmpar, parallel=False):
    """
    run_glm(sessions, analyspar, stimpar, glmpar)
    """

    full_df = build_stim_beh_df(sessions, analyspar, sesspar, stimpar)
    # run_bayesian_ridge(x_df, y_df, analyspar)
    # run_ridge_cv(x_df, y_df, analyspar)
    # run_ols_summary(x_df, y_df)

    roi_nbrs = [-1]
    roi_cols = [[col for col in full_df.columns if "roi_data_" in col]]
    if glmpar.each_roi:
        indiv_roi_cols = []
        for col in roi_cols[0]:
            indiv_roi_cols.append([col])
            roi_nbrs.append(int(col.replace("roi_data_", "")))
        # sort columns by ROI, if needed
        sorting = np.argsort(roi_nbrs)
        if (sorting != np.arange(len(roi_nbrs))).all():
            indiv_roi_cols = [indiv_roi_cols[n] for n in sorting]
            roi_nbrs = [roi_nbrs[n] for n in sorting]
        roi_cols = roi_cols + indiv_roi_cols

    x_df = full_df.drop(columns=roi_cols[0])

    if glmpar.test:
        roi_cols = roi_cols[:4]
        roi_nbrs = roi_nbrs[:4]

    # optionally runs in parallel
    if parallel and glmpar.each_roi and len(roi_cols) > 1:
        logger.info("Calculating explained variance per ROI in parallel...")
        n_jobs = gen_util.get_n_jobs(len(roi_cols))
        outs = Parallel(n_jobs=n_jobs)(delayed(run_explained_variance)
            (x_df, full_df[cols], analyspar, glmpar.k, log_roi_n=False) 
            for cols in roi_cols)
        fulls, coef_alls, coef_unis = zip(*outs)
    else:
        fulls, coef_alls, coef_unis = [], [], []
        log_freq = math_util.round_by_order_of_mag((len(roi_cols) - 1) / 10)
        log_freq = np.max([1, log_freq])
        for c, cols in enumerate(roi_cols):
            log_roi_n = (c == 0 or not ((c - 1) % log_freq))
            out = run_explained_variance(
                x_df, full_df[cols], analyspar, glmpar.k, log_roi_n=log_roi_n
                )
            fulls.append(out[0])
            coef_alls.append(out[1])
            coef_unis.append(out[2])

    expl_var = {"full"    : fulls,
                "coef_all": gen_util.compile_dict_list(coef_alls),
                "coef_uni": gen_util.compile_dict_list(coef_unis),
                "rois"    : roi_nbrs
                }

    return expl_var


#############################################
def run_glms(sessions, analysis, seed, analyspar, sesspar, stimpar, glmpar, 
             figpar, parallel=False):
    """
    run_glms(sessions, analysis, seed, analyspar, sesspar, stimpar, glmpar, 
             figpar)
    """

    seed = rand_util.seed_all(seed, "cpu", log_seed=False)

    sessstr_pr = sess_str_util.sess_par_str(
        sesspar.sess_n, stimpar.stimtype, sesspar.plane, stimpar.visflow_dir, 
        stimpar.visflow_size, stimpar.gabk, "print")
    dendstr_pr = sess_str_util.dend_par_str(
        analyspar.dend, sesspar.plane, "roi", "print")

    logger.info("Analysing and plotting explained variance in ROI activity "
        f"({sessstr_pr}{dendstr_pr}).", extra={"spacing": "\n"})

    if glmpar.each_roi: # must do each session separately
        glm_type = "per_ROI_per_sess"
        sess_batches = sessions
        logger.info("Per ROI, each session separately.")
    else:
        glm_type = "across_sess"
        sess_batches = [sessions]
        logger.info(f"Across ROIs, {len(sessions)} sessions together.")

    # optionally runs in parallel, or propagates parallel to next level
    parallel_here = (
        parallel and not(glmpar.each_roi) and (len(sess_batches) != 1)
        )
    parallel_after = True if (parallel and not(parallel_here)) else False

    args_list = [analyspar, sesspar, stimpar, glmpar]
    args_dict = {"parallel": parallel_after} # proactively set next parallel
    all_expl_var = gen_util.parallel_wrap(
        run_glm, sess_batches, args_list, args_dict, parallel=parallel_here
        )
    
    if glmpar.each_roi:
        sessions = sess_batches
    else:
        sessions = sess_batches[0]

    sess_info = sess_gen_util.get_sess_info(
        sessions, analyspar.fluor, rem_bad=analyspar.rem_bad
        )

    extrapar = {"analysis": analysis,
                "seed"    : seed,
                "glm_type": glm_type,
                }

    info = {"analyspar"   : analyspar._asdict(),
            "sesspar"     : sesspar._asdict(),
            "stimpar"     : stimpar._asdict(),
            "glmpar"      : glmpar._asdict(),
            "extrapar"    : extrapar,
            "all_expl_var": all_expl_var,
            "sess_info"   : sess_info
            }

    fulldir, savename = glm_plots.plot_glm_expl_var(figpar=figpar, **info)

    file_util.saveinfo(info, savename, fulldir, "json")

    return

