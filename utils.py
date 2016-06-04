import os


def is_windows():
    win = ['nt']
    if os.name in win:
        return True
    return False