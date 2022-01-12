#!/usr/bin/env python

"""
run_logreg.py

This script runs and analyses logistic regressions predicting stimulus 
information based on ROI activity for data generated by the Allen Institute 
OpenScope experiments for the Credit Assignment Project

Authors: Colleen Gillon

Date: October, 2018

Note: this code uses python 3.7.

"""

import argparse
import copy
import logging
from pathlib import Path

from matplotlib import pyplot as plt

# try to set cache/config as early as possible (for clusters)
from util import gen_util 
gen_util.CC_config_cache()

gen_util.extend_sys_path(__file__, parents=2)
from util import gen_util, logger_util
from sess_util import sess_gen_util, sess_ntuple_util
from extra_analysis import logreg
from extra_plot_fcts import plot_from_dicts_tool as plot_dicts


DEFAULT_DATADIR = Path("..", "data", "OSCA")
DEFAULT_MOUSE_DF_PATH = Path("mouse_df.csv")
DEFAULT_FONTDIR = Path("..", "tools", "fonts")

logger = logging.getLogger(__name__)


TASK_DESCR = {
    "run_regr": "runs regressions, saving results into individual folders",
    "analyse" : "compiles regression results produced by run_regr, and runs statistics",
    "plot"    : "plots statistics produced by analyse",
}

#############################################
def check_args(comp="unexp", stimtype="gabors", q1v4=False, exp_v_unexp=False):
    """
    check_args()

    Verifies whether the comparison type is compatible with the stimulus type, 
    q1v4 and exp_v_unexp.

    Optional args:
        - comp (str)        : comparison type
                              default: "unexp"
        - stimtype (str)    : stimtype
                              default: "gabors"
        - q1v4 (bool)       : if True, analysis is trained on first and tested 
                              on last quartiles
                              default: False
        - exp_v_unexp (bool): if True, analysis is trained on expected and 
                              tested on unexpected sequences
                              default: False
    """

    poss_comps = logreg.get_comps(stimtype, q1v4, exp_v_unexp)

    if q1v4 and exp_v_unexp:
        raise ValueError("q1v4 and exp_v_unexp cannot both be set to True.")

    if comp not in poss_comps:
        comps_str = ", ".join(poss_comps)
        raise ValueError(f"With stimtype={stimtype}, q1v4={q1v4}, "
            f"exp_v_unexp={exp_v_unexp}, cannot use {comp}. Can only use "
            f"the following comps: {comps_str}")
    return


#############################################
def set_ctrl(ctrl=False, comp="unexp"):
    """
    set_ctrl()

    Sets the control value (only modifies if it is True).

    Optional args:
        - ctrl (bool): whether the run is a control
                       default: False
        - comp (str) : comparison type
                       default: "unexp"
    
    Returns:
        - ctrl (bool): modified control value
    """    

    ori_with_U = "U" in comp and "ori" in comp
    if comp in ["unexp", "DvU", "dir_unexp"] or ori_with_U:
        ctrl = False
    
    if comp == "all":
        raise ValueError("Should not be used if comp is 'all'.")
    
    return ctrl


#############################################
def format_output(output, runtype="prod", q1v4=False, bal=False, 
                  exp_v_unexp=False):
    """
    format_output(output)

    Returns output path with subdirectory added based on the arguments.

    Required args:
        - output (Path): base output path

    Optional args:
        - runtype (str)     : runtype
                              default: "prod"
        - q1v4 (bool)       : if True, analysis is trained on first and tested 
                              on last quartiles
                              default: False
        - bal (bool)        : if True, all classes are balanced
                              default: False
        - exp_v_unexp (bool): if True, analysis is trained on expected and 
                              tested on unexpected sequences
                              default: False

    Returns:
        - output (Path): output path with subdirectory added
    """

    subdir = "logreg_models"
    if runtype == "pilot":
       subdir = f"{subdir}_pilot"

    if q1v4:
        subdir = f"{subdir}_q1v4"

    if bal:
        subdir = f"{subdir}_bal"

    if exp_v_unexp:
        subdir = f"{subdir}_evu"

    output = Path(output, subdir)

    return output


#############################################
def run_regr(args):
    """
    run_regr(args)

    Does runs of a logistic regressions on the specified comparison and range
    of sessions.
    
    Required args:
        - args (Argument parser): parser with analysis parameters as attributes:
            alg (str)             : algorithm to use ("sklearn" or "pytorch")
            bal (bool)            : if True, classes are balanced
            batchsize (int)       : nbr of samples dataloader will load per 
                                    batch (for "pytorch" alg)
            visflow_dir (str)     : visual flow direction to analyse
            visflow_per (float)   : number of seconds to include before visual 
                                    flow segments
            visflow_size (int or list): visual flow square sizes to include
            comp (str)            : type of comparison
            datadir (str)         : data directory
            dend (str)            : type of dendrites to use ("allen" or "dend")
            device (str)          : device name (i.e., "cuda" or "cpu")
            ep_freq (int)         : frequency at which to log loss to 
                                    console
            error (str)           : error to take, i.e., "std" (for std 
                                    or quantiles) or "sem" (for SEM or MAD)
            fluor (str)           : fluorescence trace type
            fontdir (str)         : directory in which additional fonts are 
                                    located
            gabfr (int)           : gabor frame of reference if comparison 
                                    is "unexp"
            gabk (int or list)    : gabor kappas to include
            gab_ori (list or str) : gabor orientations to include
            incl (str or list)    : sessions to include ("yes", "no", "all")
            lr (num)              : model learning rate (for "pytorch" alg)
            mouse_n (int)         : mouse number
            n_epochs (int)        : number of epochs
            n_reg (int)           : number of regular runs
            n_shuff (int)         : number of shuffled runs
            scale (bool)          : if True, each ROI is scaled
            output (str)          : general directory in which to save 
                                    output
            parallel (bool)       : if True, runs are done in parallel
            plt_bkend (str)       : pyplot backend to use
            q1v4 (bool)           : if True, analysis is trained on first and 
                                    tested on last quartiles
            exp_v_unexp (bool)    : if True, analysis is trained on 
                                    expected and tested on unexpected sequences
            runtype (str)         : type of run ("prod" or "pilot")
            seed (int)            : seed to seed random processes with
            sess_n (int)          : session number
            stats (str)           : stats to take, i.e., "mean" or "median"
            stimtype (str)        : stim to analyse ("gabors" or "visflow")
            train_p (list)        : proportion of dataset to allocate to 
                                    training
            uniqueid (str or int) : unique ID for analysis
            wd (float)            : weight decay value (for "pytorch" arg)
    """

    args = copy.deepcopy(args)

    if args.datadir is None: 
        args.datadir = DEFAULT_DATADIR
    else:
        args.datadir = Path(args.datadir)

    if args.uniqueid == "datetime":
        args.uniqueid = gen_util.create_time_str()
    elif args.uniqueid in ["None", "none"]:
        args.uniqueid = None

    reseed = False
    if args.seed in [None, "None"]:
        reseed = True

    # deal with parameters
    extrapar = {"uniqueid" : args.uniqueid,
                "seed"     : args.seed
               }
    
    techpar = {"reseed"   : reseed,
               "device"   : args.device,
               "alg"      : args.alg,
               "parallel" : args.parallel,
               "plt_bkend": args.plt_bkend,
               "fontdir"  : args.fontdir,
               "output"   : args.output,
               "ep_freq"  : args.ep_freq,
               "n_reg"    : args.n_reg,
               "n_shuff"  : args.n_shuff,
               }

    mouse_df = DEFAULT_MOUSE_DF_PATH

    stimpar = logreg.get_stimpar(args.comp, args.stimtype, args.visflow_dir, 
        args.visflow_size, args.gabfr, args.gabk, gab_ori=args.gab_ori, 
        visflow_pre=args.visflow_pre)
    
    analyspar = sess_ntuple_util.init_analyspar(args.fluor, stats=args.stats, 
        error=args.error, scale=not(args.no_scale), dend=args.dend)  
    
    if args.q1v4:
        quantpar = sess_ntuple_util.init_quantpar(4, [0, -1])
    else:
        quantpar = sess_ntuple_util.init_quantpar(1, 0)
    
    logregpar = sess_ntuple_util.init_logregpar(args.comp, not(args.not_ctrl), 
        args.q1v4, args.exp_v_unexp, args.n_epochs, args.batchsize, args.lr, 
        args.train_p, args.wd, args.bal, args.alg)
    
    omit_sess, omit_mice = sess_gen_util.all_omit(stimpar.stimtype, 
        args.runtype, stimpar.visflow_dir, stimpar.visflow_size, stimpar.gabk)

    sessids = sorted(
        sess_gen_util.get_sess_vals(mouse_df, "sessid", args.mouse_n, 
        args.sess_n, args.runtype, incl=args.incl, omit_sess=omit_sess, 
        omit_mice=omit_mice)
        )

    if len(sessids) == 0:
        logger.warning(
            f"No sessions found (mouse: {args.mouse_n}, sess: {args.sess_n}, "
            f"runtype: {args.runtype})")

    for sessid in sessids:
        sess = sess_gen_util.init_sessions(sessid, args.datadir, mouse_df, 
            args.runtype, full_table=False, fluor=analyspar.fluor, 
            dend=analyspar.dend, temp_log="warning")[0]
        logreg.run_regr(sess, analyspar, stimpar, logregpar, quantpar, 
            extrapar, techpar)
            
        plt.close("all")


#############################################
def main(args):
    """
    main(args)

    Runs analyses with parser arguments.

    Required args:
        - args (dict): parser argument dictionary
    """

    logger_util.set_level(level=args.log_level)

    args.device = gen_util.get_device(args.cuda)
    args.fontdir = DEFAULT_FONTDIR


    if args.comp == "all":
        comps = logreg.get_comps(args.stimtype, args.q1v4, args.exp_v_unexp)
    else:
        check_args(args.comp, args.stimtype, args.q1v4, args.exp_v_unexp)
        comps = gen_util.list_if_not(args.comp)

    args.output = format_output(
        args.output, args.runtype, args.q1v4, args.bal, args.exp_v_unexp)

    args_orig = copy.deepcopy(args)

    if args.dict_path is not None:
        plot_dicts.plot_from_dicts(
            Path(args.dict_path), source="logreg", plt_bkend=args.plt_bkend, 
            fontdir=args.fontdir, parallel=args.parallel)

    else:
        for comp in comps:
            args = copy.deepcopy(args_orig)
            args.comp = comp
            args.not_ctrl = not(set_ctrl(not(args.not_ctrl), comp=args.comp))

            logger.info(f"Task: {args.task}\nStim: {args.stimtype} "
                f"\nComparison: {args.comp}\n", extra={"spacing": "\n"})

            if args.task == "run_regr":
                run_regr(args)

            # collates regression runs and analyses accuracy
            elif args.task == "analyse":
                logger.info(f"Folder: {args.output}")
                logreg.run_analysis(
                    args.output, args.stimtype, args.comp, not(args.not_ctrl), 
                    args.CI, args.alg, args.parallel)

            elif args.task == "plot":
                logreg.run_plot(
                    args.output, args.stimtype, args.comp, not(args.not_ctrl), 
                    args.visflow_dir, args.fluor, not(args.no_scale), args.CI, 
                    args.alg, args.plt_bkend, args.fontdir, args.modif)

            else:
                gen_util.accepted_values_error("args.task", args.task, 
                    ["run_regr", "analyse", "plot"])


#############################################
def parse_args():
    """
    parse_args()

    Returns parser arguments.

    Returns:
        - args (dict): parser argument dictionary
    """

    parser = argparse.ArgumentParser()

    TASK_STR = " || ".join(
        [f"{key}: {item}" for key, item in TASK_DESCR.items()])

    parser.add_argument("--output", default=Path("results"), 
        type=Path, help="where to store output")
    parser.add_argument("--datadir", default=None, 
        help="data directory (if None, uses a directory defined below)")
    parser.add_argument("--task", default="run_regr", 
        help=(f"TASKS: {TASK_STR}"))
        
        # technical parameters
    parser.add_argument("--plt_bkend", default=None, 
        help="switch mpl backend when running on server")
    parser.add_argument("--parallel", action="store_true", 
        help="do runs in parallel.")
    parser.add_argument("--cuda", action="store_true", 
        help="run on cuda.")
    parser.add_argument("--ep_freq", default=50, type=int,  
        help="epoch frequency at which to log loss")
    parser.add_argument("--n_reg", default=50, type=int, help="n regular runs")
    parser.add_argument("--n_shuff", default=50, type=int, 
        help="n shuffled runs")
    parser.add_argument("--log_level", default="info", 
        help="logging level (does not work with --parallel)")

        # logregpar
    parser.add_argument("--comp", default="unexp", 
        help="unexp, AvB, AvC, BvC, DvU, Uori, dir_all, dir_exp, dir_unexp, "
            "half_right, half_left, half_diff")
    parser.add_argument("--not_ctrl", action="store_true", 
        help=("run comparisons not as controls for unexp (ignored for unexp)"))
    parser.add_argument("--n_epochs", default=1000, type=int)
    parser.add_argument("--batchsize", default=200, type=int)
    parser.add_argument("--lr", default=0.0001, type=float, 
        help="learning rate")
    parser.add_argument("--train_p", default=0.75, type=float, 
        help="proportion of dataset used in training set")
    parser.add_argument("--wd", default=0, type=float, 
        help="weight decay to use")
    parser.add_argument("--q1v4", action="store_true", 
        help="run on 1st quartile and test on last")
    parser.add_argument("--exp_v_unexp", action="store_true", 
        help="use with dir_exp to run on reg and test on unexp")
    parser.add_argument("--bal", action="store_true", 
        help="if True, classes are balanced")
    parser.add_argument("--alg", default="sklearn", 
        help="use sklearn or pytorch log reg.")

        # sesspar
    parser.add_argument("--mouse_n", default=1, type=int)
    parser.add_argument("--runtype", default="prod", help="prod or pilot")
    parser.add_argument("--sess_n", default="all")
    parser.add_argument("--incl", default="any",
        help="include only 'yes', 'no' or 'any'")
        # stimpar
    parser.add_argument("--stimtype", default="gabors", 
        help="gabors or visflow")
    parser.add_argument("--gabk", default=16, type=int, 
        help="gabor kappa parameter")
    parser.add_argument("--gabfr", default=0, type=int, 
        help="starting gab frame if comp is unexp")
    parser.add_argument("--gab_ori", default="all",  
        help="gabor orientations to include or 'all'.")
    parser.add_argument("--visflow_dir", default="both", 
        help="visual flow direction")
    parser.add_argument("--visflow_size", default=128, help="visual flow size")
    parser.add_argument("--visflow_pre", default=0.0, type=float, 
        help="visual flow pre")

        # analyspar
    parser.add_argument("--no_scale", action="store_true", 
        help="do not scale each roi")
    parser.add_argument("--fluor", default="dff", help="raw or dff")
    parser.add_argument("--stats", default="mean", help="mean or median")
    parser.add_argument("--error", default="sem", help="std or sem")
    parser.add_argument("--dend", default="extr", help="allen, extr")

        # extra parameters
    parser.add_argument("--seed", default=-1, type=int, 
        help="manual seed (-1 for None)")
    parser.add_argument("--uniqueid", default="datetime", 
        help=("passed string, 'datetime' for date and time "
            "or 'none' for no uniqueid"))

        # CI parameter for analyse and plot tasks
    parser.add_argument("--CI", default=0.95, type=float, help="shuffled CI")

        # from dict
    parser.add_argument("--dict_path", default=None, 
        help=("path to directory from which to plot data "
            "(up to 2 directories up from hyperparameters.json)."))

        # plot modif
    parser.add_argument("--modif", action="store_true", 
        help=("run plot task using modified plots."))

    args = parser.parse_args()

    return args


#############################################
if __name__ == "__main__":

    args = parse_args()
    main(args)

