#!/usr/bin/env python
# micropython SOCKS server by Kost
# https://github.com/kost/micropython-socks

import socket
import _thread
import sys

from gc import collect
from time import sleep_ms

# constant definitions
_SO_REGISTER_HANDLER = const(20)
_CLIENT_TIMEOUT = const(300)
_REMOTE_TIMEOUT = const(100)
_CHUNK_SIZE = const(0x1000)

socks_client_list = []
socks_started = False
verbose_l=1
server_socket=None

class SOCKS_client:
    SOCKS_VERSION = 5

    ERROR_VERSION = "[-] Client version error!"
    ERROR_METHOD = "[-] Client method error!"

    ERROR_CMD = "[e] Error in command!"

    # ALLOWED_METHOD = [0, 2]
    ALLOWED_METHOD = [0]

    CONNECT = 1
    BIND = 2
    UDP_ASSOCIATE = 3

    IPV4 = 1
    DOMAINNAME = 3
    IPV6 = 4

    CONNECT_SUCCESS = 0

    RSV = 0
    BNDADDR = "\x00" * 4
    BNDPORT = "\x00" * 2

    def __init__(self, srvsocket):
        self.remote_socket = None
        self.local_socket, self.local_address = srvsocket.accept()
        log_msg(2, '[2] Got connection from [%s:%s]' % (self.local_address[0], self.local_address[1]))
        self.local_socket.settimeout(_CLIENT_TIMEOUT)
        self.result = self.socks_selection(self.local_socket)
        if not self.result[0]:
            log_msg(1, "[1] Socks election error")
            socks_close_client(socket)
        else:
            self.local_socket.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, self.handleconn)

    def close_remote(self, cl):
        cl.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, None)
        cl.close()

    def transfer_fromlocal(self, src):
        buffer = src.recv(_CHUNK_SIZE)
        if not buffer:
            log_msg(2, "[2] No data received from local! Closing...")
            socks_close_client(src)
            self.close_remote(self.remote_socket)
        try:
            self.remote_socket.send(SOCKS_client.handle(buffer))
        except Exception as err:
            log_msg(2, "[2] Error sending fromlocal(): {}".format(err))
            socks_close_client(src)
            self.close_remote(self.remote_socket)

    def transfer_fromremote(self, src):
        buffer = src.recv(_CHUNK_SIZE)
        if not buffer:
            log_msg(2, "[2] No data received from remote! Closing...")
            self.close_remote(src)
            socks_close_client(self.local_socket)
        try:
            self.local_socket.send(SOCKS_client.handle(buffer))
        except Exception as err:
            log_msg(2, "[2] Error sending fromremote(): {}".format(err))
            self.close_remote(src)
            socks_close_client(self.local_socket)

    def socks_selection(self, socket):
        client_version = ord(socket.recv(1))
        log_msg(3, "[3] client version : %d" % (client_version))
        if not client_version == SOCKS_client.SOCKS_VERSION:
            socks_close_client(socket)
            return (False, SOCKS_client.ERROR_VERSION)
        support_method_number = ord(socket.recv(1))
        log_msg(3, "[3] Client Supported method number : %d" % (support_method_number))
        support_methods = []
        for i in range(support_method_number):
            method = ord(socket.recv(1))
            log_msg(3, "[3] Client Method : %d" % (method))
            support_methods.append(method)
        selected_method = None
        for method in SOCKS_client.ALLOWED_METHOD:
            if method in support_methods:
                selected_method = 0
        if selected_method == None:
            socks_close_client(socket)
            return (False, SOCKS_client.ERROR_METHOD)
        log_msg(3, "[3] Server select method : %d" % (selected_method))
        response = chr(SOCKS_client.SOCKS_VERSION) + chr(selected_method)
        socket.send(response.encode())
        return (True, socket)

    def handle(buffer):
        return buffer

    def handleconn(self, srvsocket):
        try:
            collect()
            self.socks_request(srvsocket)
        except:
            pass

    # This part is based on SOCKS implementation by WangYihang
    def socks_request(self, local_socket):
        client_version = ord(local_socket.recv(1))
        log_msg(3, "[3] client version : %d" % (client_version))
        if not client_version == SOCKS_client.SOCKS_VERSION:
            socks_close_client(local_socket)
            return (False, SOCKS_client.ERROR_VERSION)
        cmd = ord(local_socket.recv(1))
        if cmd == SOCKS_client.CONNECT:
            log_msg(3, "[3] CONNECT request from client")
            rsv  = ord(local_socket.recv(1))
            if rsv != 0:
                socks_close_client(local_socket)
                return (False, SOCKS_client.ERROR_RSV)
            atype = ord(local_socket.recv(1))
            if atype == SOCKS_client.IPV4:
                dst_address = ("".join(["%d." % (i) for i in local_socket.recv(4)]))[0:-1]
                log_msg(3, "[3] IPv4 : %s" % (dst_address))
                dst_port = ord(local_socket.recv(1)) * 0x100 + ord(local_socket.recv(1))
                log_msg(3, "[3] Port : %s" % (dst_port))
                self.remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.remote_socket.settimeout(_REMOTE_TIMEOUT)
                try:
                    log_msg(3, "[3] Connecting : %s:%s" % (dst_address, dst_port))
                    self.remote_socket.connect((dst_address, dst_port))
                    response = ""
                    response += chr(SOCKS_client.SOCKS_VERSION)
                    response += chr(SOCKS_client.CONNECT_SUCCESS)
                    response += chr(SOCKS_client.RSV)
                    response += chr(SOCKS_client.IPV4)
                    response += SOCKS_client.BNDADDR
                    response += SOCKS_client.BNDPORT
                    local_socket.send(response.encode())
                    log_msg(2, "[2] Tunnel connected! Tranfering data...")
                    local_socket.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, self.transfer_fromlocal)
                    self.remote_socket.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, self.transfer_fromremote)
                    return (True, (local_socket, self.remote_socket))
                except socket.error as e:
                    print(e)
                    socks_close_client(local_socket)
                    self.close_remote(self.remote_socket)
            elif atype == SOCKS_client.DOMAINNAME:
                domainname_length = ord(local_socket.recv(1))
                domainname = ""
                for i in range(domainname_length):
                    domainname += (local_socket.recv(1).decode("ascii"))
                log_msg(3, "[3] Domain name: %s" % (domainname))
                dst_port = ord(local_socket.recv(1)) * 0x100 + ord(local_socket.recv(1))
                log_msg(3, "[3] Port: %s" % (dst_port))
                self.remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.remote_socket.settimeout(_REMOTE_TIMEOUT)
                try:
                    log_msg(3, "[3] Connecting : %s:%s" % (domainname, dst_port))
                    self.remote_socket.connect((domainname, dst_port))
                    response = ""
                    response += chr(SOCKS_client.SOCKS_VERSION)
                    response += chr(SOCKS_client.CONNECT_SUCCESS)
                    response += chr(SOCKS_client.RSV)
                    response += chr(SOCKS_client.IPV4)
                    response += SOCKS_client.BNDADDR
                    response += SOCKS_client.BNDPORT
                    local_socket.send(response.encode())
                    log_msg(2, "[2] Tunnel connected! Tranfering data...")
                    local_socket.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, self.transfer_fromlocal)
                    self.remote_socket.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, self.transfer_fromremote)
                    return (True, (local_socket, self.remote_socket))
                except socket.error as e:
                    print(e)
                    socks_close_client(local_socket)
                    self.close_remote(self.remote_socket)
            elif atype == SOCKS_client.IPV6:
                dst_address = int(local_socket.recv(4).encode("hex"), 16)
                log_msg(2, "[2] IPv6 : %x" % (dst_address))
                dst_port = ord(local_socket.recv(1)) * 0x100 + ord(local_socket.recv(1))
                log_msg(2, "[2] Port: %s" % (dst_port))
                self.remote_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                self.remote_socket.connect((dst_address, dst_port))
                socks_close_client(local_socket)
                self.close_remote(self.remote_socket)
                return (False, "Client address error!")
            else:
                socks_close_client(local_socket)
                return (False, "Client address error!")
        elif cmd == SOCKS_client.BIND:
            # Not implemented
            socks_close_client(local_socket)
            return (False, SOCKS_client.ERROR_CMD)
        elif cmd == SOCKS_client.UDP_ASSOCIATE:
            # Not implemented
            socks_close_client(local_socket)
            return (False, SOCKS_client.ERROR_CMD)
        else:
            socks_close_client(local_socket)
            return (False, SOCKS_client.ERROR_CMD)
        return (True, local_socket)

def log_msg(level, *args):
    global verbose_l
    if verbose_l >= level:
      print(*args)

def socks_close_client(cl):
    log_msg(5, "[5] Closing socket on client")

    cl.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, None)
    cl.close()

    for i, client in enumerate(socks_client_list):
        if client.local_socket == cl:
            del socks_client_list[i]
            break

    log_msg(5, "[5] Closed socket on client")

def accept_socks_connect(local_socket):
    try:
        socks_client_list.append(SOCKS_client(local_socket))
    except Exception as err:
        log_msg(1, "[1] Error adding new client: {}".format(err))
        try:
            temp_client, temp_addr = local_socket.accept()
            temp_client.close()
        except:
            pass

def start(lhost="0.0.0.0", lport=1080, verbose=1, max_connection=16):
    global verbose_l
    global server_socket
    global socks_started

    verbose_l = verbose

    if socks_started:
        log_msg(1, '[1] Server already started')
        return

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((lhost, lport))
        server_socket.listen(max_connection)
        server_socket.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, accept_socks_connect)

        log_msg(1, '[1] Server started [%s:%d]' % (lhost, lport))
        socks_started = True
    except:
        log_msg(0, '[0] Error starting server [%s:%d]' % (lhost, lport))

def stop():
    global verbose_l
    global socks_client_list
    global server_socket
    global socks_started

    log_msg(2, '[2] Performing shutdown')
    for client in socks_client_list:
        client.local_socket.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, None)
        client.local_socket.close()
        if client.remote_socket is not None:
            client.remote_socket.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, None)
            client.remote_socket.close()

    del socks_client_list
    socks_client_list = []

    if server_socket is not None:
        server_socket.setsockopt(socket.SOL_SOCKET, _SO_REGISTER_HANDLER, None)
        server_socket.close()

    socks_started = False
    log_msg(1, '[1] Server shutdown')

def restart(lhost="0.0.0.0", lport=1080, verbose=1, max_connection=16):
    stop()
    sleep_ms(200)
    start(lhost, lport, verbose, max_connection)

def help():
    print("socks - simple SOCKS server for micropython")
    print("import socks")
    print("socks.start()")
    print('socks.start(lhost="0.0.0.0", lport=1080, verbose=10, max_connection=16)')
    print("socks.stop()")

#start()
#collect()
