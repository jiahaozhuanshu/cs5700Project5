import sys
import os
import threading
import gzip
import socket
import urllib.request
import subprocess
from util import *

LIMIT_10MB = 10485760
PORT = int(sys.argv[2])
ORIGIN = sys.argv[4]
MY_CACHE_FOLDER = 'myCache'
MY_CACHE_FOLDER_PATH = 'myCache/'
NEWLINE = '\r\n\r\n'
HALFNEWLINE = '\r\n'
READBINARY = 'rb'
WRITEBINARY = 'wb'
TEMPFILE = '.temp'
HTTP200 = 'HTTP/1.1 200 OK'


def parsePort(port, origin):
    if port < 40000 or port > 65535:
        sys.exit('Wrong port number.')
    else:
        return True




class LocalCache:

    def __init__(self):

        self.lock = threading.Lock()
        self.cur_cache = self.generateCacheFolder()

    def generateCacheFolder(self):
        with self.lock:
            if not os.path.exists(MY_CACHE_FOLDER):
                return []
            else:
                return list(map(lambda x: (x, 1), os.listdir(MY_CACHE_FOLDER)))

    def visitLocalCache(self, path):
        with self.lock:

            for cache in self.cur_cache:

                if hashing_path(path) == cache[0]:
                    self.cur_cache.append((hashing_path(path), cache[1] + 1))
                    self.cur_cache.remove(cache)
                    try:
                        file = gzip.open(MY_CACHE_FOLDER_PATH + hashing_path(path), READBINARY).read()                        
                        gzip.open(MY_CACHE_FOLDER_PATH + hashing_path(path), READBINARY).close()
                        print('============================================')
                        print('cache found in local cache ', self.cur_cache)
                        print('============================================')
                        return file
                    except Exception as e:
                        print(e)
                        self.cur_cache.remove(cache)
                        os.remove(MY_CACHE_FOLDER_PATH + hashing_path(path))
                        return None

            return None

    def writeToLocalCache(self, path, data):
        with self.lock:

            write_file = gzip.open(hashing_path(path) + TEMPFILE, WRITEBINARY).write(data)
            
            gzip.open(hashing_path(path) + TEMPFILE, WRITEBINARY).close()
            get_size = os.path.getsize(hashing_path(path) + TEMPFILE)
            if get_size > LIMIT_10MB:
                os.remove(hashing_path(path) + TEMPFILE)
                return
            else:
                total_size = 0
                cache = os.listdir(MY_CACHE_FOLDER)
                for each_cache in cache:
                    total_size += os.path.getsize(MY_CACHE_FOLDER_PATH + each_cache)
                total_size += get_size

                while total_size >= LIMIT_10MB:
                    self.cur_cache.sort(key=lambda x: x[1])
                    file_to_remove = self.cur_cache.pop(0)[0]
                    os.remove(MY_CACHE_FOLDER_PATH + file_to_remove)

                os.remove(hashing_path(path) + TEMPFILE)
                temp_write = gzip.open(MY_CACHE_FOLDER_PATH + hashing_path(path), WRITEBINARY).write(data)
                gzip.open(MY_CACHE_FOLDER_PATH + hashing_path(path), WRITEBINARY).close()
                self.cur_cache.append((hashing_path(path), 1))
                print('============================================')
                print('changes made to local cache', self.cur_cache)
                print('============================================')





class HttpServer:
    def __init__(self):
        self.http_server = ''
        self.check_rtt = '/testing-'
        self.local_cache = LocalCache()

    def server_start(self, port, origin):
        self.http_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.http_server.bind(('', port))
        self.origin = origin

    def scamper_rtt(self, path):
        client_ip = path[len(self.check_rtt):]
        result = subprocess.check_output(["scamper", "-c", "ping -c 1", "-i", client_ip])

        return result

    def running_server(self):
        self.http_server.listen(1)
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        print('connection established')
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        while True:
            try:
                client_socket, address = self.http_server.accept()
                http_request = client_socket.recv(1024).decode('utf-8')
                if self.check_rtt not in getHttpPath(http_request):

                    a = self.local_cache.visitLocalCache(getHttpPath(http_request))
                    if a is None:
                        url = ORIGIN + ':8080' + getHttpPath(http_request)
                        print('******************************')
                        print('not found in local cache, pinging server...')
                        print('******************************')
                        
                        parsed_url = 'http://' + url

                        server_response = urllib.request.urlopen(parsed_url)

                        
                        if server_response.code != 200:
                            print('HTTP code != 200')

                        headers = HTTP200 + HALFNEWLINE + server_response.info().__str__()
                        content = server_response.read()
                        if content is None:
                            data = None

                        else:
                            self.local_cache.writeToLocalCache(getHttpPath(http_request), content)
                            data = (headers + HALFNEWLINE).encode('utf-8') + content
                        
                    else:
                        print('@@@@@@@@@@@@@@@@@@@@@@@@@@@')
                        print('fetched from local cache.')
                        print('@@@@@@@@@@@@@@@@@@@@@@@@@@@')
                        response_headers = HTTP200 + HALFNEWLINE + 'Content-Length: ' + str(len(a)) + NEWLINE
                        data = response_headers.encode('utf-8') + a

                    client_socket.sendall(data)
                    client_socket.close()


                else:
                    rtt = self.scamper_rtt(getHttpPath(http_request))
                    print('rtt', rtt)
                    client_socket.sendall(rtt)
                    print("rtt sent!!!!!********")
                    client_socket.close()

            except KeyboardInterrupt:
                self.http_server.close()
                return
            except Exception as e:
                print(e)


if __name__ == "__main__":
    input_port = int(sys.argv[2])
    input_origin = sys.argv[4]
    if parsePort(input_port, input_origin):
        if (os.path.exists(MY_CACHE_FOLDER)):
            server = HttpServer()
            server.server_start(input_port, input_origin)
            print('listening1...')
            server.running_server()
        else:
            os.mkdir(MY_CACHE_FOLDER)
            server = HttpServer()
            server.server_start(input_port, input_origin)
            print('listening1...')
            server.running_server()

    
    #  wget ec2-34-238-192-84.compute-1.amazonaws.com:50004/wiki/Main_Page