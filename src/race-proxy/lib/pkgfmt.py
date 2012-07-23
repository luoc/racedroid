
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
        <content encode="False">
        </content>
    </package>
</log>
"""

from lxml import etree
from binascii import b2a_hex

def Log():
    return  etree.Element(r"log")

def Info(**infos):
    """
    info element, describe package info
    """
    _info = etree.Element('info')
    for sec in infos:
        exec '_%s = etree.Element(\'%s\')' %(sec, sec)
        exec '_%s.text = infos[sec]' %(sec)
        exec '_info.append(_%s)' %sec
    return _info

def Content(content):
    try:
        _content = etree.Element('content', encode='False')
        _content.text = content
    except ValueError:
        _content = etree.Element('content', encode='True')
        _content.text = b2a_hex(content)
    return _content

def Package(content, **info):
    _package = etree.Element("package")
    _package.append(Info(**info))
    _package.append(Content(content))
    return _package

def _test_():
    print etree.tostring(Log(), pretty_print=True)
    print etree.tostring(Info(time='Iamtime', client='Iamclient', target='Iamtarget'), pretty_print=True)
    print etree.tostring(Content('content'), pretty_print=True)
    print etree.tostring(Package('content', client='I am client'), pretty_print=True)

if __name__ == '__main__':
    _test_()