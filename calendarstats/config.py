import argparse
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pythoncommons.project_utils import ProjectUtils

PROJECT_NAME = "calendarstats"


class Config:
    def parse_args(self):
        """This function parses and return arguments passed in"""

        parser = argparse.ArgumentParser()

        parser.add_argument('-v', '--verbose', action='store_true',
                            dest='verbose', default=None, required=False,
                            help='More verbose log')

        parser.add_argument('-f', '--file', dest='file', default=None, required=True,
                            help='Input file (ics)')

        parser.add_argument("-e", "--event-exceptions", nargs="+", default=[])
        parser.add_argument("--filter-year", nargs="+", default=[])

        args = parser.parse_args()
        print("Parsed cmd line args: " + str(args))

        return args

    @staticmethod
    def init_logger(console_debug=False):
        # get root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # create file handler which logs even debug messages
        logfilename = ProjectUtils.get_default_log_file(PROJECT_NAME)
        fh = TimedRotatingFileHandler(logfilename, when='midnight')
        fh.suffix = '%Y_%m_%d.log'
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(logging.INFO)
        if console_debug:
            ch.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)

    def __init__(self):
        self.setup_dirs()
        self.args = self.parse_args()
        verbose = True if self.args.verbose else False
        Config.init_logger(console_debug=verbose)

    @staticmethod
    def setup_dirs():
        ProjectUtils.get_output_basedir(PROJECT_NAME)
        ProjectUtils.get_logs_dir()
