import ctypes
from ctypes import wintypes

EnumWindows = ctypes.windll.user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
)
GetWindowText = ctypes.windll.user32.GetWindowTextW
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
GetClassName = ctypes.windll.user32.GetClassNameW
IsWindowVisible = ctypes.windll.user32.IsWindowVisible
GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
GetWindowRect = ctypes.windll.user32.GetWindowRect

class RECT(ctypes.Structure):
    _fields_ = [
        ('left', wintypes.ULONG),
        ('top', wintypes.ULONG),
        ('right', wintypes.ULONG),
        ('bottom', wintypes.ULONG),
    ]
    
    def __repr__(self):
        return '<Rect left=%d top=%d right=%d bottom=%d>' % (
            self.left,
            self.top,
            self.right,
            self.bottom,
        )

def get_window_name(hwnd):
    length = GetWindowTextLength(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    GetWindowText(hwnd, buff, length + 1)
    return buff.value

def get_window_class_name(hwnd):
    buff = ctypes.create_unicode_buffer(80)
    GetClassName(hwnd, buff, 80)
    return buff.value
    
def get_window_rect(hwnd):
    rect = RECT()
    GetWindowRect(hwnd, ctypes.byref(rect))
    return rect

def foreach_window(hwnd, lParam):
    if IsWindowVisible(hwnd):
        name = get_window_name(hwnd)
        class_ = get_window_class_name(hwnd)
        rect = get_window_rect(hwnd)
        print("class=%r name=%r %r" % (class_, name, rect))
    return True
    
EnumWindows(EnumWindowsProc(foreach_window), 0)

top_window = GetForegroundWindow()
print('top: %s' % repr(get_window_name(top_window)))
