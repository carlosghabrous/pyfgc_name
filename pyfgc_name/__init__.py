"""
Documentation for the pyfgc_name package

"""
from .pyfgc_name import devices, groups, gateways
from .pyfgc_name import read_name_file, read_subdevice_file, read_group_file, build_device_set, build_device_tset

from .utils import get_gws_for_group, get_fgcs_for_group

__version__ = "1.3.2"
