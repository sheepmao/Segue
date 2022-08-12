from abc import ABC, abstractmethod
from src.utils.logging.logging_segue import create_logger
from src.consts.segments_composition_consts import *
from src.consts.splitter_consts import *
import os
import json
from src.consts.augmenter_consts import *
import importlib.machinery
class Augmenter(ABC):
    
    def __init__(   self, raw_video,
                    rescaled_videos, ss,
                    original_segments_dir,
                    augmented_dir_out,
                    augmentation_module_args,
                    splitting_module_args,
                    log_dir, figs_dir,
                    verbose=False):
 
        
        self.log_dir = log_dir
        self.figs_dir = figs_dir
        self.verbose = verbose
        log_file = os.path.join(log_dir, 'Lambda_B.log')
        self.logger = create_logger('Lambda B Augmenter', log_file, verbose=verbose)
        

        augmenter_encoding_name =  augmentation_module_args[K_AUGMENTER_ENCODING_NAME]
        augmenter_encoding_module = augmentation_module_args[K_AUGMENTER_ENCODING_MODULE].replace('/','.').replace('.py', '')
        augmenter_encoding_class = augmentation_module_args[K_AUGMENTER_ENCODING_CLASS]

        self.logger.info("Augmenter encoding name = {}".format(augmenter_encoding_name))
        self.logger.info("Augmenter encoding module = {}".format(augmenter_encoding_module))
        self.logger.info("Augmenter encoding class = {}".format(augmenter_encoding_class))

        try:
            augmenter_encoding_args = augmentation_module_args[K_AUGMENTER_ENCODING_ARGS]
            self.logger.debug("Augmenter encoding module args = {}".format(augmenter_encoding_args))
        except:
            augmenter_encoding_args = {}
            self.logger.warning("No splitting module argument has been passed")
        
        try:
            self.logger.debug("Retrieving augmenter encoding policy")
            AEPolicy = getattr(importlib.import_module(augmenter_encoding_module), augmenter_encoding_class)
            self.logger.info("Augmenter policy retrieved correctly")
        except:
            self.logger.error("{} doesn't contain class name {}, or some errors are present in module".format(augmenter_encoding_module,
                                                                                                              augmenter_encoding_class))
            self.logger.exception("message") 
            sys.exit(-1)
        

        try:
            self.logger.debug("Instantiating augmenter encoding policy")
            augmented_dir_out = os.path.join(augmented_dir_out, augmenter_encoding_name, '{}')
            self.ae = AEPolicy(   raw_video,
                                  rescaled_videos, ss,
                                  original_segments_dir,
                                  augmented_dir_out,
                                  splitting_module_args, augmenter_encoding_args,
                                  log_dir, figs_dir, verbose=verbose)

            self.logger.info("Augmenter encoding policy instantiated correctly")
        except:
            self.logger.error("Something went wrong in the instantiation of the class")
            self.logger.exception("message")
            sys.exit(-1)
        
        self.rescaled_videos = rescaled_videos
        self.augmentation_module_args = augmentation_module_args

    @abstractmethod
    def augment(self, multiresolution_video):
        pass
