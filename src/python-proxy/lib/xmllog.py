"""
xmllog define xml format log class and some function to process the log file
"""

from lxml import etree
from binascii import b2a_hex, a2b_hex

class Xmllog(Object):
    def __init__(self, file):
        self.file = file
        self.xml = etree.parse(self.file)

    def merge(self):
        for hd in self.xml.iter(tag='header'):
            if hd.text == '':
                hd.getprevious()
        pass

    def ungzip(self):
        pass
