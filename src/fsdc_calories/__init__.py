from importlib.metadata import version
from .data_process import DataCal

__version__ = version("fsdc_calories")
__all__ = ["DataCal"]
