__author__ = 'LuoCheng'

import sys
sys.path.append('lib')
import xmllog

xml = xmllog.Xmllog('2012-07-12-8864.xml')
if xml.merge():
    xml.save_to_log()
    xml.save_to_xml()

