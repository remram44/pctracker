import subprocess
import typing

from .base import RecordError, Window


def _parse_number(s):
    if s.startswith('0x'):
        return int(s[2:], 16)
    else:
        return int(s, 10)


def _get_active_window():
    try:
        output = subprocess.check_output(['xdotool', 'getactivewindow'])
    except subprocess.CalledProcessError:
        raise RecordError
    return _parse_number(output.decode('utf-8').strip())


def _get_window_name(window_id):
    try:
        output = subprocess.check_output(['xdotool', 'getwindowname', str(window_id)])
    except subprocess.CalledProcessError:
        raise ValueError
    return output.decode('utf-8').rstrip('\r\n')


def get_windows() -> typing.List[Window]:
    active_id = _get_active_window()

    try:
        output = subprocess.check_output(['xprop', '-root'])
    except subprocess.CalledProcessError:
        raise RecordError
    output = output.decode('utf-8')
    for line in output.splitlines():
        if line.startswith('_NET_CLIENT_LIST_STACKING(WINDOW)'):
            pos = line.find('0x')
            ids = line[pos:].split(',')
            ids = [_parse_number(id.strip()) for id in ids]
            windows = []
            for id in ids:
                try:
                    name = _get_window_name(id)
                except ValueError:
                    # Window was gone before we could get its name, that's fine
                    continue
                windows.append(Window(id, name, active_id == id))
            return windows

    raise RuntimeError("xprop didn't provide active windows")
