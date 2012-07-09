#! /usr/bin/python
from twisted.internet import reactor
import socks 

if '__main__' == __name__:
    reactor.listenTCP(1080,socks.SOCKSv4Factory("./socks.log"))
    reactor.run()