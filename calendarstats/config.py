import argparse
import datetime
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from os.path import expanduser

from utils import FileUtils


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

    def init_logger(self, log_dir, console_debug=False):
        # get root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # create file handler which logs even debug messages
        logfilename = datetime.datetime.now().strftime(
            'calendarstats-%Y_%m_%d_%H%M%S.log')

        fh = TimedRotatingFileHandler(os.path.join(log_dir, logfilename), when='midnight')
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
        self.project_out_root, self.log_dir = self.setup_dirs()
        self.args = self.parse_args()

        # Initialize logging
        verbose = True if self.args.verbose else False
        self.init_logger(self.log_dir, console_debug=verbose)

    @staticmethod
    def setup_dirs():
        home = expanduser("~")
        project_out_root = os.path.join(home, "calendarstats")
        log_dir = os.path.join(project_out_root, 'logs')
        FileUtils.ensure_dir_created(project_out_root)
        FileUtils.ensure_dir_created(log_dir)

        return project_out_root, log_dir
