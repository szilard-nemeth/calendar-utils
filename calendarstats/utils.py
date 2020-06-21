import errno
import logging
import os
LOG = logging.getLogger(__name__)


def auto_str(cls):
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    cls.__str__ = __str__
    return cls


class FileUtils:
    @classmethod
    def ensure_dir_created(cls, dirname):
        """
    Ensure that a named directory exists; if it does not, attempt to create it.
    """
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        return dirname
