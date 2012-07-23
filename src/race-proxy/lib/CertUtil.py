import OpenSSL
import threading
import os
import hashlib
import time


class CertUtil(object):
    '''CertUtil module, based on WallProxy 0.4.0'''

    CA = None #This may cause error!!
    CALock = threading.Lock()
    subj_alts =\
    'DNS: twitter.com, DNS: facebook.com, \
 DNS: *.twitter.com, DNS: *.twimg.com, \
 DNS: *.akamaihd.net, DNS: *.google.com, \
 DNS: *.facebook.com, DNS: *.ytimg.com, \
 DNS: *.appspot.com, DNS: *.google.com, \
 DNS: *.youtube.com, DNS: *.googleusercontent.com, \
 DNS: *.gstatic.com, DNS: *.live.com, \
 DNS: *.ak.fbcdn.net, DNS: *.ak.facebook.com, \
 DNS: *.android.com, DNS: *.fbcdn.net'

    @staticmethod
    def _dir_exists(dir):
        if not os.path.exists(dir):
            os.mkdir(dir)
        else:
            if not os.path.isdir(dir):
                os.remove(dir)
                os.mkdir(dir)

    @staticmethod
    def readFile(filename):
        content = None
        with open(filename, 'rb') as fp:
            content = fp.read()
        return content

    @staticmethod
    def writeFile(filename, content):
        with open(filename, 'wb') as fp:
            fp.write(str(content))

    @staticmethod
    def createKeyPair(type=None, bits=1024):
        if type is None:
            type = OpenSSL.crypto.TYPE_RSA
        pkey = OpenSSL.crypto.PKey()
        pkey.generate_key(type, bits)
        return pkey

    @staticmethod
    def createCertRequest(pkey, digest='sha1', **subj):
        req = OpenSSL.crypto.X509Req()
        subject = req.get_subject()
        for k,v in subj.iteritems():
            setattr(subject, k, v)
        req.set_pubkey(pkey)
        req.sign(pkey, digest)
        return req

    @staticmethod
    def createCertificate(req, (issuerKey, issuerCert), serial, (notBefore,
    notAfter), digest='sha1', host=None):
        cert = OpenSSL.crypto.X509()
        cert.set_version(3)
        cert.set_serial_number(serial)
        cert.gmtime_adj_notBefore(notBefore)
        cert.gmtime_adj_notAfter(notAfter)
        cert.set_issuer(issuerCert.get_subject())
        cert.set_subject(req.get_subject())
        cert.set_pubkey(req.get_pubkey())
        alts = CertUtil.subj_alts
        if host is not None:
            alts += ", DNS: %s" % host
        cert.add_extensions([OpenSSL.crypto.X509Extension("subjectAltName",
                                                          True, alts)])
        cert.sign(issuerKey, digest)
        return cert

    @staticmethod
    def loadPEM(pem, type):
        handlers = ('load_privatekey', 'load_certificate_request', 'load_certificate')
        return getattr(OpenSSL.crypto, handlers[type])(OpenSSL.crypto.FILETYPE_PEM, pem)

    @staticmethod
    def dumpPEM(obj, type):
        handlers = ('dump_privatekey', 'dump_certificate_request', 'dump_certificate')
        return getattr(OpenSSL.crypto, handlers[type])(OpenSSL.crypto.FILETYPE_PEM, obj)

    @staticmethod
    def makeCA():
        pkey = CertUtil.createKeyPair(bits=2048)
        subj = {'countryName': 'CN', 'stateOrProvinceName': 'Internet',
                'localityName': 'Cernet', 'organizationName': 'GUCAS',
                'organizationalUnitName': 'NCNIPC', 'commonName': 'racedroid'}
        req = CertUtil.createCertRequest(pkey, **subj)
        cert = CertUtil.createCertificate(req, (pkey, req), 0, (0, 60*60*24*7305))  #20 years
        return (CertUtil.dumpPEM(pkey, 0), CertUtil.dumpPEM(cert, 2))

    @staticmethod
    def makeCert(host, (cakey, cacrt), serial):
        pkey = CertUtil.createKeyPair()
        subj = {'countryName': 'CN', 'stateOrProvinceName': 'Internet',
                'localityName': 'Cernet', 'organizationName': host,
                'organizationalUnitName': 'RaceDroid Branch', 'commonName': host}
        req = CertUtil.createCertRequest(pkey, **subj)
        cert = CertUtil.createCertificate(req, (cakey, cacrt), serial, (0,
                                                                        60*60*24*7305), host=host)
        return (CertUtil.dumpPEM(pkey, 0), CertUtil.dumpPEM(cert, 2))

    # racedroid Patch
    @staticmethod
    def getCertificate(host):
        CertUtil._dir_exists('certs')
        basedir = os.getcwd()
        keyFile = os.path.join(basedir, 'certs\\%s.key' % host)
        crtFile = os.path.join(basedir, 'certs\\%s.crt' % host)
        if os.path.exists(keyFile):
            return (keyFile, crtFile)
        if OpenSSL is None:
            keyFile = os.path.join(basedir, 'certs\\CA.key')
            crtFile = os.path.join(basedir, 'certs\\CA.crt')
            return (keyFile, crtFile)
        if not os.path.isfile(keyFile):
            with CertUtil.CALock:
                if not os.path.isfile(keyFile):
                    print 'CertUtil getCertificate for %r' %host
                    # FIXME: howto generate a suitable serial number?
                    for serial in (int(hashlib.md5(host).hexdigest(), 16), int(time.time()*100)):
                        try:
                            key, crt = CertUtil.makeCert(host, CertUtil.CA, serial)
                            CertUtil.writeFile(crtFile, crt)
                            CertUtil.writeFile(keyFile, key)
                            break
                        except Exception:
                            print 'CertUtil.makeCert failed: host=%r, serial=%r' %(host, serial)
                    else:
                        keyFile = os.path.join(basedir, 'certs\\CA.key')
                        crtFile = os.path.join(basedir, 'certs\\CA.crt')
        return (keyFile, crtFile)

    @staticmethod
    def checkCA():
        #Check CA exists
        CertUtil._dir_exists('certs')
        basedir = os.getcwd()
        keyFile = os.path.join(basedir, 'certs\\CA.key')
        crtFile = os.path.join(basedir, 'certs\\CA.crt')
        if not os.path.exists(keyFile):
            if not OpenSSL:
                print 'CA.crt is not exist and OpenSSL is disabled, ABORT!'
                return False
            key, crt = CertUtil.makeCA()
            CertUtil.writeFile(keyFile, key)
            CertUtil.writeFile(crtFile, crt)
            [os.remove(os.path.join('certs', x)) for x in os.listdir('certs')]
        if OpenSSL:
            keyFile = os.path.join(basedir, 'certs\\CA.key')
            crtFile = os.path.join(basedir, 'certs\\CA.crt')
            cakey = CertUtil.readFile(keyFile)
            cacrt = CertUtil.readFile(crtFile)
            CertUtil.CA = (CertUtil.loadPEM(cakey, 0), CertUtil.loadPEM(cacrt, 2))
            return True

