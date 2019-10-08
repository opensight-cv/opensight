import os.path


# dir is a directory (ending with '/') or a file
# if dir is a file, will use parent directory of that file
def join(dir, file):
    return os.path.realpath(os.path.join(os.path.dirname(dir), file))
