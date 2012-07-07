
"""
This file define the package format, looks like below:
<log>
    <package>
        <info>
            <id/>
            <time/>
            <client/>
            <target/>
        </info>
        <header>
            <Location/>
            <.../>
        </header>
        <content base64="False">
        </content>
    </package>
</log>
"""

from lxml import etree
from binascii import b2a_hex

def Log():
    return  etree.Element(r"log")

def Info(time, client, target):
    """
    info element, describe package info
    """
    _info = etree.Element('info')
    section = ['time', 'client', 'target']
    for sec in section:
        exec '_%s = etree.Element(\'%s\')' %(sec, sec)
        exec '_%s.text = %s' %(sec, sec)
        exec '_info.append(_%s)' %sec
    return _info

#not used now
def Header(header):
    try:
        _header = etree.Element('header')
        _header.text = header
    except ValueError:
        _header = etree.Element('header', encode='True')
        _header.text = b2a_hex(header)
    return _header

def Content(content):
    try:
        _content = etree.Element('content')
        _content.text = content
    except ValueError:
        _content = etree.Element('content', encode='True')
        _content.text = b2a_hex(content)
    return _content

def Package(time, client, target, content):
    _package = etree.Element("package")
    _package.append(Info(time, client, target))
    _package.append(Content(content))
    return _package

def _test_():
    print etree.tostring(Log(), pretty_print=True)
    print etree.tostring(Info('time', 'client', 'target'), pretty_print=True)
    #print etree.tostring(Header('header'), pretty_print=True)
    print etree.tostring(Content('content'), pretty_print=True)
    print etree.tostring(Package('time', 'client', 'target', 'content'), pretty_print=True)

if __name__ == '__main__':
    _test_()