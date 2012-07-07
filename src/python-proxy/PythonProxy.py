# -*- coding: cp1252 -*-
# <PythonProxy.py>
#
#Copyright (c) <2009> <Fábio Domingues - fnds3000 in gmail.com>
#
#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:
#
#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.

"""\
Copyright (c) <2009> <Fábio Domingues - fnds3000 in gmail.com> <MIT Licence>

                  **************************************
                 *** Python Proxy - A Fast HTTP proxy ***
                  **************************************

Neste momento este proxy é um Elie Proxy.

Suporta os métodos HTTP:
 - OPTIONS;
 - GET;
 - HEAD;
 - POST;
 - PUT;
 - DELETE;
 - TRACE;
 - CONENCT.

Suporta:
 - Conexões dos cliente em IPv4 ou IPv6;
 - Conexões ao alvo em IPv4 e IPv6;
 - Conexões todo o tipo de transmissão de dados TCP (CONNECT tunneling),
     p.e. ligações SSL, como é o caso do HTTPS.

A fazer:
 - Verificar se o input vindo do cliente está correcto;
   - Enviar os devidos HTTP erros se não, ou simplesmente quebrar a ligação;
 - Criar um gestor de erros;
 - Criar ficheiro log de erros;
 - Colocar excepções nos sítios onde é previsível a ocorrência de erros,
     p.e.sockets e ficheiros;
 - Rever tudo e melhorar a estrutura do programar e colocar nomes adequados nas
     variáveis e métodos;
 - Comentar o programa decentemente;
 - Doc Strings.

Funcionalidades futuras:
 - Adiconar a funcionalidade de proxy anónimo e transparente;
 - Suportar FTP?.


(!) Atenção o que se segue só tem efeito em conexões não CONNECT, para estas o
 proxy é sempre Elite.

Qual a diferença entre um proxy Elite, Anónimo e Transparente?
 - Um proxy elite é totalmente anónimo, o servidor que o recebe não consegue ter
     conhecimento da existência do proxy e não recebe o endereço IP do cliente;
 - Quando é usado um proxy anónimo o servidor sabe que o cliente está a usar um
     proxy mas não sabe o endereço IP do cliente;
     É enviado o cabeçalho HTTP "Proxy-agent".
 - Um proxy transparente fornece ao servidor o IP do cliente e um informação que
     se está a usar um proxy.
     São enviados os cabeçalhos HTTP "Proxy-agent" e "HTTP_X_FORWARDED_FOR".

"""

import sys
sys.path.append('lib')
import socket
import thread
import select
import ssl
import random
import pkgfmt
import logging
from urlparse import urlparse
from CertUtil import CertUtil
from time import strftime, localtime, time
from lxml import etree


__version__ = '0.2.0'
BUFLEN = 8192
VERSION = 'Python Proxy/'+__version__
HTTPVER = 'HTTP/1.1'
__DEBUG__ = False



class ConnectionHandler:
    def __init__(self, connection, address, timeout):
        self.client = connection
        self.target = None
        self.client_buffer = ''
        self.timeout = timeout
        self.sock_info = {'client':None,
                          'target':None}
        self._start_logger()
        self.method, self.path, self.protocol = self.get_base_header()
        self.host = self._find_host(self.path)
        if self.method=='CONNECT':
            self.method_CONNECT()
        elif self.method in ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT',
                             'DELETE', 'TRACE'):
            self.method_others()
        self.client.close()
        self.target.close()

    #return a tuple (method, path, protocol)
    #e.g: (GET, /, HTTP/1.1)
    def get_base_header(self):
        while 1:
            self.client_buffer += self.client.recv(BUFLEN)
            end = self.client_buffer.find('\n')
            if end!=-1:
                break
        self._handle_pkg(self.client_buffer) #racedroid patch
        print '%s'%self.client_buffer[:end]
        data = (self.client_buffer[:end+1]).split()
        self.client_buffer = self.client_buffer[end+1:]
        return data

    def method_CONNECT(self): #https protocol here
        self._connect_target(self.path)
        self.client.send(HTTPVER+' 200 Connection established\n'+
                         'Proxy-agent: %s\n\n'%VERSION)
        #after send the proxy hello message, we wrap the socket with ssl module
        self._wrap_sock(self.host) #racedroid patch
        self.client_buffer = ''
        self._read_write()

    def method_others(self):
        self.path = self.path[7:]
        i = self.path.find('/')
        host = self.path[:i]        
        path = self.path[i:]
        self._connect_target(host)
        self.target.send('%s %s %s\n'%(self.method, path, self.protocol)+
                         self.client_buffer)
        self.client_buffer = ''
        self._read_write()

    def _connect_target(self, host):
        i = host.find(':')
        if i!=-1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 80
        (soc_family, _, _, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family)
        self.target.connect(address)

    def _wrap_sock(self, host):
        try:
            if self.target != None:
                self.target = ssl.wrap_socket(self.target)
            if self.client != None:
                if CertUtil.checkCA():
                    self.key_file, self.cert_file = CertUtil.getCertificate(host)#stupid bug
                self.client = ssl.wrap_socket(self.client, keyfile=self.key_file,
                                              certfile=self.cert_file, server_side=True)
        except Exception, e:
            print '%s' %e

    def _read_write(self):
        #TODO: fix log module bugs, multi connect cause file confusion
        time_out_max = self.timeout/3
        socs = [self.client, self.target]
        count = 0
        while 1:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    data = in_.recv(BUFLEN)
                    if in_ is self.client:
                        out = self.target
                    else:
                        out = self.client
                    if data:
                        out.send(data)
                        count = 0
                    if len(data): #racedroid patch
                        self._handle_pkg(data)
            if count == time_out_max:
                break
        if len(self.xmllog) != 0:
            self._write_xml()

    def _start_logger(self, lvl='NOTSET'): #racedroid patch
        logname = '%s-%.4d'%(strftime('%Y-%m-%d', localtime()),
                                 random.randint(0, 9999))
        formatter = '%(asctime)s - %(target)s - %(client)s:\n%(message)s'
        logging.basicConfig(filename=logname+'.log', filemode='ab',
                            format=formatter, level=lvl)
        self.logger = logging.getLogger('Race')
        self.xmllog = pkgfmt.Log()
        self.xmlfile = open(logname + '.xml', 'ab')

    def _write_xml(self):
        if self.xmlfile != None:
            self.xmlfile.write(etree.tostring(self.xmllog, pretty_print=True))
            self.xmlfile.close()
        else:
            print 'write logger error!, logger is None!'

    def _handle_pkg(self, pkg): #racedroid patch
        #one .log file and multiple .xml file, each .xml file represent one connection
        #logging
        self.sock_info['client'] = (self.client, self.client.getsockname(),
                                    self.client.getpeername()) if self.client != None else None
        self.sock_info['target'] = (self.target, self.target.getsockname(),
                                    self.target.getpeername()) if self.target != None else None
        #getnameinfo seems take long time, so we could translate address in log function
        self.logger.info(pkg, extra=self.sock_info)
        #xml log
        time = self._get_time()
        client = str(self.sock_info['client'])
        target = str(self.sock_info['target'])
        self.xmllog.append(pkgfmt.Package(time, client, target, pkg))

    def _get_time(self):
        ct = time()
        msecs = (ct - long(ct))*1000
        t = strftime("%Y-%m-%d %H:%M:%S", localtime(ct))
        s = "%s,%03d" % (t, msecs)
        return s

    def _find_host(self, url):
        #Now only works for https, maybe need modification in the future
        if r'://' in url:
            host =  urlparse(url).hostname
        else:
            host = urlparse(r'https://' + url).hostname
        return host

def start_server(host='localhost', port=8080, IPv6=False, timeout=60, # for debug
                  handler=ConnectionHandler):
    if IPv6==True:
        soc_type=socket.AF_INET6
    else:
        soc_type=socket.AF_INET
    if __DEBUG__:
        socket.setdefaulttimeout(3600)
        timeout = 3600
    soc = socket.socket(soc_type)
    soc.bind((host, port))
    print "Serving on %s:%d."%(host, port)#debug
    soc.listen(0)
    while 1:
        thread.start_new_thread(handler, soc.accept()+(timeout,))

if __name__ == '__main__':
    start_server()
