from __future__ import print_function, unicode_literals
from datetime import datetime, timedelta
import re

def dt_resolvable_to_ms(resolvable, utc_offset=0, resolution=6e4):
    '''Convert datetime resolvable to milliseconds since the Unix epoch.

    Args:
        resolvable (datetime or int or str):
            Object that is resolvable to a date and time (see below)

        utc_offset (int):
            UTC offset in seconds

        resolution (int):
            Max resolution (in ms) for the returned timestamp. Default is to
            mimic UniFi Video frontend in providing at most minute granularity.

    Returns:
        int: Milliseconds since the Unix epoch

    On *datetime* resolvables
        The type of the ``resolvable`` parameter will affect the return value.

        *datetime*: Naive *datetime* values are offset by ``utc_offset``
        while TZ aware *datetime* values are offset by whatever
        :class:`~datetime.timedelta` their
        :attr:`datetime.datetime.utcoffset()` returns.

        *str*: Strings are treated as naive *datetime* values and should
        follow ISO8601 in including at least the ``YYYY``, ``MM``, and ``DD``
        parts in either ``YYYY-MM-DD`` or ``YYYYMMDD``.

        *int*: Ints are assumed to be UNIX timestamps; only ms conversion
        and granularity changes will be applied.

    '''

    if isinstance(resolvable, str):
        iso8601_match = re.match(
            (
                r'([0-9]{4})-*([0-9]{2})-*([0-9]{2})[Tt\s]*'
                r'(?:([0-9]{2}):*){0,1}'
                r'(?:([0-9]{2}):*){0,1}'
                r'(?:([0-9]{2}):*){0,1}'
            ),
            resolvable)
        try:
            return dt_resolvable_to_ms(
                datetime(*[
                    int(i) for i in iso8601_match.groups()
                    if i is not None]),
                utc_offset,
                resolution)
        except (ValueError, AttributeError) as e:
            raise ValueError(
                'Unable to parse date and time from "{}"'.format(resolvable))
    elif isinstance(resolvable, datetime):
        if resolvable.tzinfo and resolvable.tzinfo.utcoffset(resolvable):
            utc_offset = resolvable.utcoffset().total_seconds()
        ts = int(resolvable.strftime('%s'))
        local_td = datetime.fromtimestamp(ts) - datetime.utcfromtimestamp(ts)
        ms = (ts + local_td.total_seconds()) * 1000
    elif isinstance(resolvable, (int, float)):
        utc_offset = 0
        ms = resolvable * 1000
    else:
        raise TypeError('Datetime resolvable cannot be of type {}'.format(
            type(resolvable)))

    return int(ms - (ms % resolution) + (-1 * (utc_offset * 1000)))

def format_mac_addr(mac_addr):
    if len(mac_addr) != 12:
        return 'ffffffffffff'
    return ':'.join(re.search(r'(..)(..)(..)(..)(..)(..)',
        mac_addr).groups()).lower()

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
