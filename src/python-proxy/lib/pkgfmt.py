
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
import base64

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

def Header(header):
    _header = etree.Element('header', base64='True')
    _header.text = base64.encodestring(header)
    return _header

def Content(content):
    _content = etree.Element('content', base64='True')
    _content.text = base64.encodestring(content)
    return _content

def Package(time, client, target, header, content):
    _package = etree.Element("package")
    _package.append(Info(time, client, target))
    _package.append(Header(header))
    _package.append(Content(content))
    return _package

def _test_():
    print etree.tostring(Log(), pretty_print=True)
    print etree.tostring(Info('time', 'client', 'target'), pretty_print=True)
    print etree.tostring(Header('header'), pretty_print=True)
    print etree.tostring(Content('content'), pretty_print=True)
    print etree.tostring(Package('time', 'client', 'target', 'header', 'content'), pretty_print=True)

if __name__ == '__main__':
    _test_()