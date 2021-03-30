import pytest
import re

import pyfgc_name

@pytest.fixture
def r_name_file():
    pyfgc_name.read_name_file()

def test_data_structures_have_minimum_content():
    pyfgc_name.read_name_file()
    pyfgc_name.read_subdevice_file()
    pyfgc_name.read_group_file()
    assert len(pyfgc_name.gateways) > 200
    assert len(pyfgc_name.devices)  > 4000
    assert len(pyfgc_name.groups) > 50
    
    gw_set_from_groups = set()
    for v in pyfgc_name.groups.values():
        for g in v["gateways"]:
            gw_set_from_groups.add(g)

    assert len(pyfgc_name.gateways) == len(gw_set_from_groups)

def test_devices_can_be_read_from_default_name_file_parameter():
    pyfgc_name.read_name_file()
    assert len(pyfgc_name.devices) != 0

def test_devices_can_be_read_by_passing_name_file_absolute_path():
    pyfgc_name.read_name_file("/user/pclhc/etc/fgcd/name")
    assert len(pyfgc_name.devices) != 0

def test_devices_can_be_read_by_passing_name_file_url():
    pyfgc_name.read_name_file("file:///user/pclhc/etc/fgcd/name")
    assert len(pyfgc_name.devices) != 0

def test_devices_can_be_read_by_passing_http_url():
    pyfgc_name.read_name_file("http://cs-ccr-www1.cern.ch/~pclhc/etc/fgcd/name")
    assert len(pyfgc_name.devices) != 0

def test_non_existing_file():
    with pytest.raises(FileNotFoundError):
        pyfgc_name.read_name_file("/a/b/c/ddddsdf/s/321423/5/6c")
    
def test_build_device_set_from_simple_regex(r_name_file):
    fgcs = pyfgc_name.build_device_set("rpzes.866.15.eth1")
    assert len(fgcs) ==  1

def test_build_device_set_from_regex(r_name_file):
    fgcs = pyfgc_name.build_device_set("rpz.*400.*rch.*")
    assert len(fgcs) == 31

def test_build_device_with_suffix(r_name_file):
    fgcs_0 = pyfgc_name.build_device_set("RPCEK.361.BT.RBHZ10")
    fgcs_1 = pyfgc_name.build_device_set("RPCEK.361.BT.RBHZ10.SP")
    assert len(fgcs_0) == 1
    assert len(fgcs_1) == 1
    assert fgcs_0.pop() != fgcs_1.pop()

def test_build_device_set_from_device_list(r_name_file):
    fgcs = pyfgc_name.build_device_set(['RFNA.866.01.ETH1', 'RFNA.866.02.ETH1'])
    assert len(fgcs) == 2

def test_build_device_set_from_filter_func(r_name_file):
    def my_filter(key, value):
            return value["channel"] == 10 and value["class_id"] == 91

    fgcs = pyfgc_name.build_device_set(my_filter)
    assert len(fgcs) ==  20

def test_build_device_set_from_filter_func_with_regex(r_name_file):
    def my_filter_regex(key, value):
        ba1s = re.compile("^.*BA1.*")
        return value["class_id"] == 91 and ba1s.match(key)

    fgcs = pyfgc_name.build_device_set(my_filter_regex)
    assert len(fgcs) == 77

# TODO: [Test] build_device_tset()
# TODO: [Test] invalid arguments for build_device_set() and build_device_tset() 
# TODO: [Test] upper case conversion in build_device_set() and build_device_tset() 
# TODO: [Test] KeyError in build_device_tset() 
# TODO: [Fix] tests using callback functions

def test_devices_gateways_consistency():
    pyfgc_name.read_name_file()

    # Filter function
    def filter_fgcs(dev_dict):
        return dev_dict["gateway"] == "cfc-866-reth7"
    
    # Get devices controlled by certain gateway
    target_devices = list(filter(filter_fgcs, pyfgc_name.devices.values()))

    # Add one to the gateways list because the gateway is not included
    assert len(pyfgc_name.gateways["cfc-866-reth7"]["devices"]) + 1 == len(target_devices)
