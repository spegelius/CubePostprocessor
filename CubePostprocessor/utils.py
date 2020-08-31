import os
import platform

def is_windows():
    win = ['nt']
    if os.name in win:
        return True
    return False

def is_wsl():
    if "microsoft" in platform.uname().release:
        return True
    return False