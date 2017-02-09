#!/usr/bin/env python
# -*- coding: utf-8 -*-

# bmap_align.py is part of Barleymap.
# Copyright (C)  2013-2014  Carlos P Cantalapiedra.
# Copyright (C) 2016-2017 Carlos P Cantalapiedra
# (terms of use can be found within the distributed LICENSE file).

############################################
# This script allows the user to retrieve map
# positions from fasta seqs.
############################################

import sys, os, traceback
from optparse import OptionParser

from barleymapcore.db.ConfigBase import ConfigBase
from barleymapcore.db.PathsConfig import PathsConfig
from barleymapcore.db.MapsConfig import MapsConfig
from barleymapcore.db.DatasetsConfig import DatasetsConfig
from barleymapcore.db.DatabasesConfig import DatabasesConfig
from barleymapcore.alignment.AlignmentFacade import AlignmentFacade
from barleymapcore.datasets.DatasetsFacade import DatasetsFacade
from barleymapcore.annotators.GenesAnnotator import AnnotatorsFactory
from barleymapcore.maps.MapMarkers import MapMarkers
from barleymapcore.m2p_exception import m2pException
from barleymapcore.output.OutputFacade import OutputFacade

DATABASES_CONF = ConfigBase.DATABASES_CONF
MAPS_CONF = ConfigBase.MAPS_CONF
DATASETS_CONF = ConfigBase.DATASETS_CONF
DATASETS_ANNOTATION_CONF = ConfigBase.DATASETS_ANNOTATION_CONF
ANNOTATION_TYPES_CONF = ConfigBase.ANNOTATION_TYPES_CONF

DEFAULT_QUERY_MODE = "gmap"
DEFAULT_THRES_ID = 98.0
DEFAULT_THRES_COV = 95.0
DEFAULT_N_THREADS = 1
DEFAULT_SORT_PARAM = "map default"
DEFAULT_EXTEND_WINDOW = 0.0

def _print_parameters(fasta_path, genetic_map_name, query_type, \
                      threshold_id, threshold_cov, n_threads, \
                      sort_param, multiple_param, best_score, \
                      show_genes, show_markers, \
                      load_annot, extend_window, \
                      show_unmapped_param, collapsed_view):
    sys.stderr.write("\nParameters:\n")
    sys.stderr.write("\tQuery fasta: "+fasta_path+"\n")
    sys.stderr.write("\tGenetic maps: "+genetic_map_name+"\n")
    sys.stderr.write("\tAligner: "+query_type+"\n")
    sys.stderr.write("\tThresholds --> %id="+str(threshold_id)+" : %query_cov="+str(threshold_cov)+"\n")
    sys.stderr.write("\tThreads: "+str(n_threads)+"\n")
    sys.stderr.write("\tBest score filtering: "+str("yes" if best_score else "no")+"\n")
    sys.stderr.write("\tSort: "+sort_param+"\n")
    sys.stderr.write("\tShow multiples: "+str("yes" if multiple_param else "no")+"\n")
    sys.stderr.write("\tShow genes: "+str("yes" if show_genes else "no")+"\n")
    sys.stderr.write("\tShow markers: "+str("yes" if show_markers else "no")+"\n")
    sys.stderr.write("\tLoad annotation: "+str("yes" if load_annot else "no")+"\n")
    sys.stderr.write("\tExtend genes/markers search: "+str(extend_window)+"\n")
    sys.stderr.write("\tShow unmapped: "+str(show_unmapped_param)+"\n")
    sys.stderr.write("\tShow results as collapsed rows: "+str(collapsed_view)+"\n")
    
    return

############ BARLEYMAP_ALIGN_SEQS
try:
    
    ## Usage
    __usage = "usage: bmap_align.py [OPTIONS] [FASTA_FILE]\n\n"+\
              "typical: bmap_align.py --maps=map queries.fasta"
    optParser = OptionParser(__usage)
    
    ########## Define parameters
    ##########
    
    ## Parameters related with alignment
    optParser.add_option('--aligner', action='store', dest='query_mode', type='string',
                     help='Alignment software to use (default "'+DEFAULT_QUERY_MODE+'"). '+\
                     'The "gmap" option means to use only GMAP. '+\
                     'The "blastn" option means to use only Blastn. '+\
                     'The order and aligners can be explicitly specified by separating the names by ","'+\
                     ' (e.g.: blastn,gmap --> First Blastn, then GMAP).')
    
    optParser.add_option('--thres-id', action='store', dest='thres_id', type='string',
                         help='Minimum identity for valid alignments. '+\
                         'Float between 0-100 (default '+str(DEFAULT_THRES_ID)+').')
    
    optParser.add_option('--thres-cov', action='store', dest='thres_cov', type='string',
                         help='Minimum coverage for valid alignments. '+\
                         'Float between 0-100 (default '+str(DEFAULT_THRES_COV)+').')
    
    optParser.add_option('--threads', action='store', dest='n_threads', type='string',
                         help='Number of threads to perform alignments (default '+str(DEFAULT_N_THREADS)+').')
    
    ## Parameters in common with bmap_find
    optParser.add_option('--maps', action='store', dest='maps_param', type='string', help='Comma delimited list of Maps to show.')
    
    optParser.add_option('-b', '--best-score', action='store_true', dest='best_score',
                         help='Will return only best score hits.')
    
    optParser.add_option('--sort', action='store', dest='sort_param', type='string', \
                         help='Sort results by centimorgan (cm) or basepairs (bp) '+\
                         '(default: defined for each map in maps configuration.')
    
    optParser.add_option('-k', '--show-multiples', action='store_true', dest='multiple_param',
                         help='Queries with multiple positions will be shown (are obviated by default).')
    
    optParser.add_option('-g', '--genes', action='store_true', dest='show_genes',
                         help='Genes at positions of queries will be shown.')
    
    optParser.add_option('-m', '--markers', action='store_true', dest='show_markers',
                         help='Additional markers at positions of queries will be shown. Ignored if -g.')
    
    optParser.add_option('--extend', action='store', dest='extend_window',
                         help='Centimorgans or basepairs (depending on sort) to extend the search of -g or -m.'+\
                         '(default '+str(DEFAULT_EXTEND_WINDOW)+')')
    
    optParser.add_option('-a', '--annot', action='store_true', dest='load_annot',
                         help='Annotation info for genes will be shown.')
    
    optParser.add_option('-u', '--show-unmapped', action='store_true', dest='show_unmapped',
                         help='Not found (unaligned, unmapped), will be shown.')
    
    optParser.add_option('-c', '--collapse', action='store_true', dest='collapse',
                         help='Mapping results and features (markers, genes) will be shown at the same level.')
    
    optParser.add_option('-f', action='store_true', dest='format_numbers', \
                         help='cM positions will be output with all decimals (default, 2 decimals).')
    
    optParser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='More information printed.')
    
    ########### Read parameters
    ###########
    (options, arguments) = optParser.parse_args()
    
    if not arguments or len(arguments)==0:
        optParser.exit(0, "You may wish to run '-help' option.\n")
    
    # INPUT FILE
    query_fasta_path = arguments[0] # THIS IS MANDATORY
    
    # Verbose
    verbose_param = options.verbose
    
    if verbose_param: sys.stderr.write("Command: "+" ".join(sys.argv)+"\n")
    
    # Output format of decimal numbers (cM positions)
    beauty_nums = not options.format_numbers
    
    # Query mode
    if options.query_mode: query_mode = options.query_mode
    else: query_mode = DEFAULT_QUERY_MODE
        
    # Threshold Identity
    if options.thres_id: threshold_id = float(options.thres_id)
    else: threshold_id = DEFAULT_THRES_ID
    
    # Threshold coverage
    if options.thres_cov: threshold_cov = float(options.thres_cov)
    else: threshold_cov = DEFAULT_THRES_COV
    
    # Num threads
    if options.n_threads: n_threads = int(options.n_threads)
    else: n_threads = DEFAULT_N_THREADS
    
    ## Show only alignments from database with best scores
    best_score = options.best_score
    
    ## Sort
    if options.sort_param and options.sort_param == "bp":
        sort_param = "bp"
    elif options.sort_param and options.sort_param == "cm":
        sort_param = "cm"
    else:
        sort_param = DEFAULT_SORT_PARAM
    
    ## Multiple
    multiple_param = options.multiple_param
    
    ## Show genes
    show_genes = options.show_genes
    
    ## Show markers
    show_markers = options.show_markers
    
    ## Annotation
    load_annot = options.load_annot
    
    ## Genes window
    if options.extend_window:
        extend_window = float(options.extend_window)
    else:
        extend_window = DEFAULT_EXTEND_WINDOW
    
    ## Show unmapped
    show_unmapped = options.show_unmapped
    
    # Collapsed view
    collapsed_view = options.collapse
    
    ######### Read configuration files
    #########
    app_abs_path = os.path.dirname(os.path.abspath(__file__))
    
    paths_config = PathsConfig(app_abs_path)
    __app_path = paths_config.get_app_path()
    
    # Maps
    maps_conf_file = __app_path+MAPS_CONF
    maps_config = MapsConfig(maps_conf_file)
    if options.maps_param:
        maps_names = options.maps_param
        maps_ids = maps_config.get_maps_ids(maps_names.strip().split(","))
    else:
        maps_ids = maps_config.get_maps().keys()
        maps_names = ",".join(maps_config.get_maps_names(maps_ids))
    
    maps_path = paths_config.get_maps_path() #__app_path+config_path_dict["maps_path"]
    
    ##### Print parameters
    #####
    if verbose_param: _print_parameters(query_fasta_path, maps_names, query_mode, \
                      threshold_id, threshold_cov, n_threads, \
                      sort_param, multiple_param, best_score, \
                      show_genes, show_markers, \
                      load_annot, extend_window, \
                      show_unmapped_param)
    
    ############### MAIN
    if verbose_param: sys.stderr.write("\n")
    
    ############# ALIGNMENTS - REFERENCES
    # Load configuration paths
    
    split_blast_path = paths_config.get_split_blast_path() #__app_path+config_path_dict["split_blast_path"]
    tmp_files_path = paths_config.get_tmp_files_path() #__app_path+config_path_dict["tmp_files_path"]
    blastn_app_path = paths_config.get_blastn_app_path() #config_path_dict["blastn_app_path"]
    gmap_app_path = paths_config.get_gmap_app_path() #config_path_dict["gmap_app_path"]
    gmapl_app_path = paths_config.get_gmapl_app_path() #config_path_dict["gmapl_app_path"]
    hsblastn_app_path = paths_config.get_hsblastn_app_path()  #config_path_dict["hsblastn_app_path"]
    
    blastn_dbs_path = paths_config.get_blastn_dbs_path()  #config_path_dict["blastn_dbs_path"]
    gmap_dbs_path = paths_config.get_gmap_dbs_path() # config_path_dict["gmap_dbs_path"]
    hsblastn_dbs_path = paths_config.get_hsblastn_dbs_path() #config_path_dict["hsblastn_dbs_path"]
    
    # Databases
    databases_conf_file = __app_path+DATABASES_CONF
    databases_config = DatabasesConfig(databases_conf_file, verbose_param)
    
    facade = AlignmentFacade(split_blast_path, blastn_app_path, gmap_app_path, hsblastn_app_path,
                             blastn_dbs_path, gmap_dbs_path, hsblastn_dbs_path, gmapl_app_path,
                             tmp_files_path, databases_config, verbose = verbose_param)
    
    ############ Pre-loading of some objects
    ############
    # DatasetsFacade
    if show_markers or show_genes:
        # Datasets config
        datasets_conf_file = __app_path+DATASETS_CONF
        datasets_config = DatasetsConfig(datasets_conf_file)
        
        # Load DatasetsFacade
        datasets_path = paths_config.get_datasets_path() #__app_path+config_path_dict["datasets_path"]
        datasets_facade = DatasetsFacade(datasets_config, datasets_path, verbose = verbose_param)
    
    # GenesAnnotator
    if show_genes and load_annot:
        ## Load annotation config
        dsannot_conf_file = __app_path+DATASETS_ANNOTATION_CONF
        anntypes_conf_file = __app_path+ANNOTATION_TYPES_CONF
        annot_path = paths_config.get_annot_path()
        
        annotator = AnnotatorsFactory.get_annotator(dsannot_conf_file, anntypes_conf_file, annot_path, verbose_param)
    else:
        annotator = None
        
    # OutputFacade
    if collapsed_view:
        outputPrinter = OutputFacade.get_collapsed_printer(sys.stdout, verbose = verbose_param, beauty_nums = beauty_nums, show_headers = True)
    else:
        outputPrinter = OutputFacade.get_expanded_printer(sys.stdout, verbose = verbose_param, beauty_nums = beauty_nums, show_headers = True)
    
    ########### Create maps
    ###########
    for map_id in maps_ids:
        sys.stderr.write("bmap_align: Map "+map_id+"\n")
        
        map_config = maps_config.get_map_config(map_id)
        databases_ids = map_config.get_db_list()
        hierarchical = map_config.is_hierarchical()
        
        sort_by = map_config.check_sort_param(map_config, sort_param, DEFAULT_SORT_PARAM)
        
        ############ Perform alignments
        # TODO: avoid aligning to the same DB as one of a previous map
        # this "TODO" would need to handle correctly best_score and hierarchical
        facade.perform_alignment(query_fasta_path, databases_ids, hierarchical, query_mode,
                                           threshold_id, threshold_cov, n_threads, \
                                           best_score)
        
        results = facade.get_alignment_results()
        unaligned = facade.get_alignment_unmapped()  
        
        ############ MAPS
        mapMarkers = MapMarkers(maps_path, map_config, verbose_param)
        
        mapMarkers.create_map(results, unaligned, sort_by, multiple_param)
        
        if show_markers or show_genes:
            
            ############ OTHER MARKERS
            if show_markers and not show_genes:
                
                # Enrich with markers
                mapMarkers.enrich_with_markers(datasets_facade, extend_window,
                                                collapsed_view, constrain_fine_mapping = False)
                
            ########### GENES
            if show_genes:
                
                # Enrich with genes
                mapMarkers.enrich_with_genes(datasets_facade, extend_window,
                                             annotator, collapsed_view, constrain_fine_mapping = False)
        
        mapping_results = mapMarkers.get_mapping_results()
        
        ############################################################ OUTPUT
        if show_markers:
            outputPrinter.print_map_with_markers(mapping_results, map_config, multiple_param)
        elif show_genes:
            outputPrinter.print_map_with_genes(mapping_results, map_config, multiple_param, load_annot, annotator)
        else:
            outputPrinter.print_map(mapping_results, map_config, multiple_param)
        
        if show_unmapped:
            outputPrinter.print_unmapped(mapping_results, map_config)
            outputPrinter.print_unaligned(mapping_results, map_config)


except m2pException as m2pe:
    sys.stderr.write("\nThere was an error.\n")
    sys.stderr.write(m2pe.msg+"\n")
except Exception as e:
    traceback.print_exc(file=sys.stderr)
    sys.stderr.write("\nERROR\n")
    sys.stderr.write(str(e)+"\n")
    sys.stderr.write('An error was detected. If you can not solve it please contact compbio@eead.csic.es ('+\
                                   'laboratory of computational biology at EEAD).\n')
finally:
    pass

## END