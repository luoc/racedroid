__author__ = 'LuoCheng'

import pkgfmt
import os.path
from http_parser.pyparser import HttpParser
from lxml import etree
from binascii import a2b_hex

class Xmllog(object):

    def __init__(self, file):
        self.file = file
        self.path, self.fname = os.path.split(file)
        self.xml = etree.parse(self.file)

    def save_to_xml(self):
        new_xml_file = os.path.join(self.path, '_'+self.fname)
        with open(new_xml_file, 'wb+') as fp:
            fp.write(etree.tostring(self.xml, pretty_print=True))

    def save_to_log(self):
        pname, ext = os.path.splitext(self.fname)
        new_log_file = os.path.join(self.path, '_'+pname+'.log')
        with open(new_log_file, 'wb+') as fp:
            fp.write(self._get_decode_xml())


    # this function is preliminary of save* function
    def merge(self):
        logger = pkgfmt.Log()
        hparser = HttpParser()
        html = list()
        st = None
        et = None
        for pkg in self.xml.iter(tag='package'):
            data = self._pkg_get_content(pkg, decode=True)
            nparsed = hparser.execute(data, len(data))
            assert nparsed == len(data)

            if hparser.is_headers_complete():
                html.append(hparser.get_first_line() +
                            self._format_header(hparser.get_headers()))
                st = self._pkg_get_time(pkg)
            if hparser.is_partial_body():
                html.append(hparser.recv_body())
            if hparser.is_message_complete():
                et = self._pkg_get_time(pkg)
                logger.append(pkgfmt.Package(''.join(html), start_time=st, end_time=et,
                                             client=self._pkg_get_client(pkg),
                                             target=self._pkg_get_target(pkg)))
                hparser = HttpParser() # a new parser
                html = []
        self.xml = logger # new xml is a _Element object, not _ElementTree object
        return True

    def _format_header(self, header):
        _header = ''
        for hd in iter(header):
            _header = '%s\r\n%s: %s' %(_header, hd, header[hd])
        return _header.lstrip()

    def _get_decode_xml(self):
        log = list()
        for pkg in self.xml.iter(tag='package'):
            pkg_text = list()
            for item in pkg.getiterator():
                if item.tag == 'content':
                    if item.get('encode') == 'False':
                        pkg_text.append('%s: %s'%(item.tag, item.text))
                    elif item.get('encode') == 'True':
                        pkg_text.append('%s: %s'%(item.tag, a2b_hex(item.text)))
                elif item.text:
                    pkg_text.append('%s: %s'%(item.tag, item.text))
            log.append('\r\n'.join(pkg_text))
        return '\r\n\r\n'.join(log)

    def _pkg_get_time(self, elem):
        return elem.xpath(r'./info/time')[0].text

    def _pkg_get_client(self, elem):
        return elem.xpath(r'./info/client')[0].text

    def _pkg_get_target(self, elem):
        return elem.xpath(r'./info/target')[0].text

    def _pkg_get_content(self, elem, decode=False):
        _content = None
        if not decode:
            _content = elem.xpath(r'./content')[0].text
        elif elem.xpath(r'./content')[0].get('encode') == 'False':
            _content = elem.xpath(r'./content')[0].text
        elif elem.xpath(r'./content')[0].get('encode') == 'True':
            _content = a2b_hex(elem.xpath(r'./content')[0].text)
        return _content

    def _format_item(self, item):
        return '%s: %s'%(item.tag, item.text)