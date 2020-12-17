from datetime import datetime
import pynput


class RecordError(Exception):
    """Couldn't inspect windows right now (is screen locked?)"""


class Window(object):
    id: int
    name: str
    active: bool

    def __init__(self, id: int, name: str, active: bool):
        self.id = id
        self.name = name
        self.active = active


class InputMonitor(object):
    last_input: datetime

    def __init__(self):
        self.last_input = datetime.utcnow()

    def on_input(self, *args, **kwargs):
        self.last_input = datetime.utcnow()


class PynputMonitor(InputMonitor):
    def __init__(self):
        super(PynputMonitor, self).__init__()
        self.mouse = pynput.mouse.Listener(
            on_move=self.on_input,
            on_click=self.on_input,
            on_scroll=self.on_input,
        )
        self.mouse.start()

        self.keyboard = pynput.keyboard.Listener(
            on_press=self.on_input,
            on_release=self.on_input,
        )
        self.keyboard.start()
