import pyfgc_name

def get_gws_for_group(group, start_group=pyfgc_name.groups):
    result = list()
    try:
        group_dict = start_group[group]

    except KeyError as ke:
        raise KeyError(f'Deployment group {group} does not exist') from ke

    for k, v in group_dict.items():
        if k == 'gateways' and isinstance(v, list):
            result += v

        if isinstance(v, dict):
            result += get_gws_for_group(k, start_group=group_dict)

    return result

def get_fgcs_for_group(group, start_group=pyfgc_name.groups, filterfunc=None):
    fgcs = set()
    gws = get_gws_for_group(group)

    for g in gws:
        fgcs |= set(pyfgc_name.gateways[g]['devices'])

    filtered_fgcs = dict(filter(filterfunc, pyfgc_name.devices.items()))
    filtered_fgcs_set = set(filtered_fgcs.keys())

    return fgcs & filtered_fgcs_set