from datetime import datetime
import re

def camel_to_snake(text):
    text = text.split('_')
    return text[0] + ''.join([i.capitalize() for i in text[1:]])

def get_arguments():
    from inspect import getargvalues, stack
    return {k: v for k, v in getargvalues(stack()[1][0])[-1:][0].items() \
            if k != 'self'}

def iso_str_to_epoch(iso_str):
    try:
        iso_str = iso_str.strip()
        if not re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt\s](?:[0-9]{2}:?){3}',
                iso_str):
            raise ValueError

        _date, _time = re.split(r'[Tt\s]', iso_str)
        year, month, day = [int(i) for i in _date.strip().split('-')]
        hh, mm, ss = [int(i.strip()) for i in _time.strip().split(':')]

        dtime = datetime(year, month, day, hh, mm, ss)

        return int((dtime - datetime(1970, 1, 1)).total_seconds())

    except Exception:
        raise ValueError('Unable to parse "{}". Use the following ISO ' \
            'format: YYYY-MM-DD HH:MM:SS'.format(iso_str))

def format_mac_addr(mac_addr):
    if len(mac_addr) != 12:
        return 'ffffffffffff'
    return ':'.join(re.search(r'(..)(..)(..)(..)(..)(..)',
        mac_addr).groups()).lower()

def tz_shift(target_utc_s_offset, epoch_sec):
    return epoch_sec - target_utc_s_offset

def parse_gmt_offset(gmt_hhmm):
    '''Parse UTC offset as reported by UniFi Video

    Arguments:
        gmt_hhmm (str):
            UTC offset from /bootstrap JSON
            (``settings.systemSettings.gmtOffset``)

    Returns
        int: UTC offset in seconds
    '''

    valid = re.match(r'gmt([+-])([0-9]{1,2})(?::([0-9]{1,2}))?', gmt_hhmm, re.I)

    if not valid:
        raise ValueError('"{}" is not a valid GMT-offset string'.format(
            gmt_hhmm))

    seconds = [
        i[0](i[1])
        for i in zip(
            [
                lambda x: 44 - ord(x),
                lambda x: int(x or 0) * 3600,
                lambda x: int(x or 0) * 60,
            ],
            valid.groups())
    ]

    return seconds[0] * sum(seconds[1:])
