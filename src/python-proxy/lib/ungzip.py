__author__ = 'LuoCheng'

import gzip
import zlib


def ungzipFile(filepath):
    return gzip.GzipFile(filepath).read()

def ungzip(content):
    return zlib.decompress(content, zlib.MAX_WBITS+32)
