import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from typing import Set, List, Optional

import pyfgc_const as fc


# Constants 

# Maximum number of devices in WFIP and Ether buses, respectively
FGC_MAX_NUM_WFIP  = 32
FGC_MAX_NUM_ETHER = 64

# Timestamp of last read. Initialized to 1970, Jan 1
last_time_read_name  = 0
last_time_read_sub   = 0
last_time_read_group = 0

rdevname  = re.compile("[A-Z][A-Z0-9._\\-]+")
rhostname = re.compile("[a-z][a-z0-9\\-]+")
romode    = re.compile("0x[0-9A-Fa-f]{4}")


# Initialize just once
try:
    gateways
except NameError:
    gateways = dict()

try:
    devices
except NameError:
    devices = dict()

try:
    groups
except NameError:
    groups = dict()


def read_name_file(filename: Optional[str] = None) -> None:
    """[summary]
    
    [description]
    
    Keyword Arguments:
        filename {[type]} -- [description] (default: {FGC_NAME_FILE_URL})
    """
    if filename is None:
        filename = fc.FGC_NAME_FILE_URL

    # If the filename does not contain the protocol, assume it is a file        
    if not re.match("(file|http|https|ftp)://.*", filename):
        filename = "file://" + filename

    global last_time_read_name
    name_file_content = _get_file_content(filename, last_time_read_name)
    _parse_name_file(filename, name_file_content)

    last_time_read_name = time.time()

def read_subdevice_file(basepath: Optional[str] = None) -> None:
    """[summary]
    
    [description]
    
    Keyword Arguments:
        basepath {[type]} -- [description] (default: {FGC_SUB_NAME_URL_BASE})
    
    Returns:
        [type] -- [description]
    """
    if basepath is None:
        basepath = fc.FGC_SUB_NAME_URL_BASE

    # It is mandatory to read the name file first
    try:
        assert (len(gateways) != 0 and len(devices) != 0)
        
    except AssertionError:
        raise AssertionError("It is mandatory to read the name file first (pyfgc_name.read_name_file())")

    if not re.match("(file|http|https|ftp)://.*", basepath):
        # If the filename does not contain the protocol, assume it is a file
        basepath = "file://" + basepath

    # Iterate over all gateways 
    for gateway in gateways:
        filename = os.path.join(basepath, gateway)

        global last_time_read_sub

        try:
            subdevice_file_content = _get_file_content(filename, last_time_read_sub)
            _parse_subdevice_file(filename, subdevice_file_content)

        except urllib.error.URLError:
            # Try to read as many files as possible
            pass

    last_time_read_sub = time.time()

def read_group_file(filename: Optional[str] = None) -> None:

    if filename is None:
        filename = fc.FGC_GROUP_FILE_URL

    # If the filename does not contain the protocol, assume it is a file
    if not re.match("(file|http|https|ftp)://.*", filename):
        filename = "file://" + filename
    
    try:
        assert (len(gateways) != 0 and len(devices) != 0)

    except AssertionError:
        raise AssertionError("It is mandatory to read the name file first (pyfgc_name.read_name_file())!!!")

    global last_time_read_group
    group_file_content = _get_file_content(filename, last_time_read_group)
    _parse_group_file(filename, group_file_content)

    last_time_read_group = time.time()

def build_device_set(devs) -> Set:
    """
    Builds up set of strings [DEVICE, ...]
    """

    if not devs:
        return set()
    global devices

    # devs is a regex string
    if isinstance(devs, str):   
        regex_obj = re.compile(devs.upper()) 
        devices_names = devices.keys()
        return {dev.upper() for dev in devices_names if regex_obj.fullmatch(dev)}
    # devs is list or set
    elif isinstance(devs, (list, set)):
        return {dev.upper() for dev in devs}
    # devs is filter function
    elif callable(devs):       
        return {k.upper() for k,v in devices.items() if devs(k, v)}
    
    raise TypeError("Argument type not allowed")

def build_device_tset(devs) -> Set:
    """
    Builds up set of tuples [(DEVICE, ADDRESS), ...]
    """

    def is_tuple_of_2str(v):
        return isinstance(v, tuple) and list(map(type, v)) == [str, str]
        
    if not devs:
        return set()

    elif is_tuple_of_2str(devs):
        (dev, gw) = devs
        return {(dev.upper(), gw)}
          
    elif all(is_tuple_of_2str(dev) for dev in devs):
        return {(dev.upper(), gw) for dev, gw in devs}
        
    elif isinstance(devs, str) or all(isinstance(dev, str) for dev in devs):
        try:
            return {(dev.upper(), devices[dev.upper()]["gateway"]) for dev in build_device_set(devs)}
        except KeyError as e:
            raise KeyError(f"Unable to obtain devices'{devs}' gateway name") from e

    raise TypeError("Argument type not allowed")

def _parse_name_file(filename, content):
    if not content:
        return

    # Clear previous content if there is new one
    global devices
    devices.clear()

    global gateways
    gateways.clear()

    for linenum, line in enumerate(content.split("\n")):

        # Skip empty lines
        if not line.strip():
            continue

        hostname, channel, class_id, devname, omodemask = line.split(":")

        # Validate channel number 
        try:
            channel = int(channel)
        except:
            raise ValueError(f"{filename}(line {linenum}): Channel number '{channel}' is not an integer")

        if channel < 0:
            raise ValueError(f"{filename}(line {linenum}): Channel number '{channel}' is not an integer >= 0")

        # Validate class id
        try:
            class_id = int(class_id)
        except:
            raise ValueError(f"{filename}(line {linenum}): Class id '{class_id}' is not an integer")

        if class_id < 0 or class_id > 255:
            raise ValueError(f"{filename}(line {linenum}): Class id '{class_id}' is not an integer >= 0 and <= 255")

        if 50 < class_id < 60:
            if channel > FGC_MAX_NUM_WFIP:
                raise ValueError(f"{filename}(line {linenum}): Channel '{channel}' not allowed for class '{class_id}'")

        if 60 < class_id < 70:
            if channel > FGC_MAX_NUM_ETHER:
                raise ValueError(f"{filename}(line {linenum}): Channel '{channel}' not allowed for class '{class_id}'")

        # Validate device name
        if len(devname) > fc.FGC_MAX_DEV_LEN:
            raise ValueError(f"{filename}(line {linenum}): Length of the device name '{devname}' is > {fc.FGC_MAX_DEV_LEN}")

        global rdevname
        if channel > 0:
            if not rdevname.match(devname):
                raise ValueError(f"{filename}(line {linenum}): Device name '{devname}' contains one or more characters different than 'A-Z0-9.-_'")
        else:
            expected_devname = hostname.upper()
            if devname != expected_devname:
                raise ValueError(f"{filename}(line {linenum}): Gateway device name '{devname}' must be '{expected_devname}'")

        if devname in devices:
            raise ValueError(f"{filename}(line {linenum}): Duplicate device name '{devname}'")

        if channel > 0:
            if hostname not in gateways:
                raise ValueError(f"{filename}(line {linenum}): Device '{devname}' defined before the gateway definition")

            if channel < len(gateways[hostname]["channels"]):
                raise ValueError(f"{filename}(line {linenum}): Out of order device channel '{channel}'. It is smaller than expected ({len(gateways[hostname]['channels'])})")

            if channel in gateways[hostname]["channels"]:
                raise ValueError(f"{filename}(line {linenum}): Duplicate channel number '{channel} in gateway '{hostname}'") 

        # Validate omode mask
        if not romode.match(omodemask):
            raise ValueError(f"{filename}(line {linenum}): omode mask '{omodemask} must be a 4-byte hexadecimal number")

        omodemask = int(omodemask,16)

        # Validate number of gateways
        if channel == 0 and len(gateways) == fc.FGC_MAX_FGCDS:
            raise ValueError(f"{filename}(line {linenum}): Maximum number of gateways exceeded (< {fc.FGC_MAX_FGCDS}")

        # Insert items in gateways and devices 
        if channel == 0:
            gateways[hostname]             = dict()
            gateways[hostname]["channels"] = list()
            gateways[hostname]["devices"]  = list()

        else:
            gateways[hostname]["devices"].append(devname)

        devices[devname]              = dict()
        devices[devname]["channel"]   = channel
        devices[devname]["class_id"]  = class_id
        devices[devname]["omodemask"] = omodemask

        for _ in range(len(gateways[hostname]["channels"]), channel + 1):
            gateways[hostname]["channels"].append(None)

        # Make a copy of devices[devname] dict because later we will add 
        # the key "gateway", which we do not want to include in gateways dict
        gateways[hostname]["channels"][channel] = dict(devices[devname])
        devices[devname]["gateway"]             = hostname

def _parse_subdevice_file(filename, content):
    """[summary]
    
    [description]
    
    Arguments:
        filename {[type]} -- [description]
        fhandler {[type]} -- [description]
    
    Raises:
        ValueError -- [description]
        ValueError -- [description]
        ValueError -- [description]
        ValueError -- [description]
        ValueError -- [description]
        ValueError -- [description]
        ValueError -- [description]
        ValueError -- [description]
        ValueError -- [description]
    """
    if not content:
        return 

    global devices

    aliases = set()

    for linenum, line in enumerate(content.split("\n")):

        # Skip empty lines
        if not line.strip():
            continue

        device, channel, alias, *_ = line.split(":")

        # Check channel
        try:
            channel = int(channel)
        except:
            raise ValueError(f"{filename}(line {linenum}): Channel number '{channel}' is not an integer")

        if channel < 0 or channel > 255:
            raise ValueError(f"{filename}(line {linenum}): Channel number '{channel}' is not an integer >= 0 and <= 255")

        # Device name already exist
        if device not in devices:
            raise ValueError(f"{filename}(line {linenum}): Device '{device}' not defined")

        # Alias is not an existing device
        if alias in devices:
            raise ValueError(f"{filename}(line {linenum}): Alias '{alias}' is not unique. Another device exist with the same name")

        # Alias is not unique
        if alias in aliases:
            raise ValueError(f"{filename}(line {linenum}): Alias '{alias}' is not unique. Another alias exist with the same name")

        # Device does not exist for the given gateway

        global rdevname

        # Device format is correct
        if not rdevname.match(device):
            raise ValueError(f"{filename}(line {linenum}): Device '{device}' contains one or more characters different than 'A-Z0-9.-_'")

        if len(device) > fc.FGC_MAX_DEV_LEN:
            raise ValueError(f"{filename}(line {linenum}): Device '{device}' length is too long (> {fc.FGC_MAX_DEV_LEN})")

        # Alias format is correct        
        if not rdevname.match(alias):
            raise ValueError(f"{filename}(line {linenum}): Alias '{alias}' contains one or more characters different than 'A-Z0-9.-_'")

        if len(alias) > fc.FGC_MAX_DEV_LEN:
            raise ValueError(f"{filename}(line {linenum}): Alias '{alias}' length is too long (> {fc.FGC_MAX_DEV_LEN})")

        # Add alias to the list of alias
        aliases.add(alias)

        # Append sub_device
        if "sub_devices" not in devices[device]:
            devices[device]["sub_devices"] = []

        sub_device = dict()
        sub_device["alias"] = alias
        # if len(other) > 0:
        #     #TODO: timing_condition here -> confirm with spage: add it in groups and not here
        #     sub_device["timing_condition"] = other[0]
        
        for _ in range(len(devices[device]["sub_devices"]), channel+1):
            devices[device]["sub_devices"].append(None)      

        devices[device]["sub_devices"][channel] = sub_device

def _parse_group_file(filename, content):
    if not content:
        return
        
    global gateways

    for linenum, line in enumerate(content.split("\n")):
        if not line.strip():
            continue
        
        gw_host, timing_domain, groups_string = line.split(":")

        # Check that gateway is known
        try:
            gateways[gw_host]

        except KeyError:
            raise KeyError(f"{filename}(line {linenum}): Gateway '{gw_host}' found in group file but not in name file!")

        try:
            gw_group = gateways[gw_host]["group"]

        except KeyError:
            pass
        
        else:
            raise KeyError(f"{filename}(line {linenum}): Gateway '{gw_host}' found in group '{gw_group}'!")
        
        # Add timing domain to gateway
        gateways[gw_host]["timing_domain"] = timing_domain

        # Add gateways to groups
        global groups
        groups_temp = groups

        groups_list = groups_string.split("/")
        for g in groups_list:
            try:
                groups_temp[g]
            
            except KeyError:
                groups_temp[g] = dict()
            
            groups_temp = groups_temp[g]
        
        try:
            groups_temp["gateways"]
        
        except KeyError:
            groups_temp["gateways"] = list()

        groups_temp["gateways"].append(gw_host)

        # Add groups to gateways
        try:
            gateways[gw_host]["groups"]
        
        except KeyError:
            gateways[gw_host]["groups"] = groups_list

def _get_file_content(filename, last_time_stamp):
    if re.match("(http|https)://.*", filename):
        last_time_read_string = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(last_time_stamp))
        request = urllib.request.Request(filename, headers={"If-Modified-Since": last_time_read_string})

        try:
            req = urllib.request.urlopen(request)
            resp = req.read().decode("ascii")

        except urllib.error.HTTPError as e:
            #TODO: what to do here? Raise exception?
            if e.code == 304:
                # File does not have new content. Return None to keep previous content.
                return None

        except urllib.error.URLError:
            #TODO: raise the exception?
            return b""

        else:
            return resp

    if re.match("(file)://.*", filename):
        last_modif_file = os.path.getmtime(filename.split("://")[1])
        if last_modif_file > last_time_stamp:
            resp = urllib.request.urlopen(filename)
            return resp.read().decode("ascii")

        else:
            return b""

    if re.match("(ftp)://.*", filename):
        raise NotImplementedError()


if __name__ == "__main__":
    try:
        name_file_url = sys.argv[1]

    except IndexError:
        name_file_url = fc.FGC_NAME_FILE_URL

    try:
        subdevice_file_url = sys.argv[2]

    except IndexError:
        subdevice_file_url = fc.FGC_SUB_NAME_URL_BASE

    try:
        group_file_url = sys.argv[3]

    except IndexError:
        group_file_url = fc.FGC_GROUP_FILE_URL

    read_name_file(filename=name_file_url)
    read_subdevice_file(basepath=subdevice_file_url)
    read_group_file(filename=group_file_url)





