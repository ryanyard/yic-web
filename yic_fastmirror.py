#!/usr/bin/python
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# (C) Copyright 2005 Luke Macken <lmacken@redhat.com>
# Modified 2012 by Ryan Yard <ryard@redhat.com>

import os
import sys
import time
import socket
import string
import urlparse
import datetime
import threading
import re

verbose = False
always_print_best_host = True
socket_timeout = 3
timedhosts = {}
hostfilepath = ''
maxhostfileage = 10
loadcache = False
maxthreads = 15
exclude = None
include_only = None
prefer = None
downgrade_ftp = True
done_sock_timeout = False
done_repos = set()
cachedir = "/tmp"

def clean():
    global hostfilepath
    if hostfilepath and hostfilepath[0] != '/':
        hostfilepath = cachedir + '/' + hostfilepath
    if os.path.exists(hostfilepath):
        print "Cleaning up list of fastest mirrors"
        try:
            os.unlink(hostfilepath)
        except Exception, e:
            print "Cleanup failed: %s" % (e)

# Get the hostname from a url, stripping away any usernames/passwords
host = lambda mirror: mirror.split('/')[2].split('@')[-1]

def can_write_results(fname):
    if not os.path.exists(fname):
        try:
            hostfile = file(hostfilepath, 'w')
            return True
        except:
            return False

    return os.access(fname, os.W_OK)

def reposetup():
    global loadcache, exclude, include_only, prefer, hostfilepath

    if hostfilepath and hostfilepath[0] != '/':
        hostfilepath = cachedir + '/' + hostfilepath
    # If the file hostfilepath exists and is newer than the maxhostfileage,
    # then load the cache.
    if os.path.exists(hostfilepath) and get_hostfile_age() < maxhostfileage:
        loadcache = True

    if done_repos:
        print "Checking for new repos for mirrors"
    elif loadcache:
        print "Loading mirror speeds from cached hostfile"
        read_timedhosts()
    else:
        print "Determining fastest mirrors"
    repomirrors = {}
    #repos = conduit.getRepos()
    repos = "fedora"
    print repos

    #  First do all of the URLs as one big list, this way we get as much
    # parallelism as possible (if we need to do the network tests).
    all_urls = []
    for repo in repos.listEnabled():
        if repo.id in done_repos:
            continue
        if len(repo.urls) == 1:
            continue
        all_urls.extend(repo.urls)
    all_urls = FastestMirror(all_urls).get_mirrorlist()

    #  This should now just be looking up the cached times.
    for repo in repos.listEnabled():
        if repo.id in done_repos:
            continue
        if len(repo.urls) == 1:
            continue
        if str(repo) not in repomirrors:
            repomirrors[str(repo)] = FastestMirror(repo.urls).get_mirrorlist()
        if include_only:
            def includeCheck(mirror):
                if filter(lambda exp: re.search(exp, host(mirror)),
                          include_only.replace(',', ' ').split()):
                    print "Including mirror: %s" % host(mirror)
                    return True
                return False
            repomirrors[str(repo)] = filter(includeCheck,repomirrors[str(repo)])
        else:
            if exclude:
                def excludeCheck(mirror):
                    if filter(lambda exp: re.search(exp, host(mirror)),
                              exclude.replace(',', ' ').split()):
                        print "Excluding mirror: %s" % host(mirror)
                        return False
                    return True
                repomirrors[str(repo)] = filter(excludeCheck,repomirrors[str(repo)])
        repo.urls = repomirrors[str(repo)]
        if len(repo.urls):
            lvl = 3
            if always_print_best_host:
                lvl = 2
            print " * %s: %s" % (str(repo), host(repo.urls[0]))
        repo.failovermethod = 'priority'
        repo.check()
        repo.setupGrab()
        done_repos.add(repo.id)
    if done_sock_timeout:
        socket.setdefaulttimeout(None)

    if not loadcache:
        write_timedhosts()

def read_timedhosts():
    global timedhosts
    try:
        hostfile = file(hostfilepath)
        for line in hostfile.readlines():
            host, time = line.split()
            timedhosts[host] = float(time)
        hostfile.close()
    except IOError:
        pass

def write_timedhosts():
    global timedhosts
    try:
        hostfile = file(hostfilepath, 'w')
        for host in timedhosts:
            hostfile.write('%s %s\n' % (host, timedhosts[host]))
        hostfile.close()
    except IOError:
        pass

def get_hostfile_age():
    global hostfilepath
    timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(hostfilepath))
    return (datetime.datetime.now() - timestamp).days

class FastestMirror:

    def __init__(self, mirrorlist):
        self.mirrorlist = mirrorlist
        self.results = {}
        self.threads = []

    # If we don't spawn any threads, we don't need locking...
    def _init_lock(self):
        if not hasattr(self, '_results_lock'):
            self._results_lock = threading.Lock()
            global done_sock_timeout
            done_sock_timeout = True
            socket.setdefaulttimeout(socket_timeout)

    def _acquire_lock(self):
        if hasattr(self, '_results_lock'):
            self._results_lock.acquire()
    def _release_lock(self):
        if hasattr(self, '_results_lock'):
            self._results_lock.release()

    def get_mirrorlist(self):
        self.poll_mirrors()
        if not downgrade_ftp:
            mirrors = [(v, k) for k, v in self.results.items()]
        else:
            # False comes before True
            mirrors = [(k.startswith("ftp"), v, k) for k, v in
                       self.results.items()]
        mirrors.sort()
        return [x[-1] for x in mirrors]

    def poll_mirrors(self):
        global maxthreads
        for mirror in self.mirrorlist:
            if len(self.threads) > maxthreads:
                if self.threads[0].isAlive():
                    self.threads[0].join()
                del self.threads[0]

            if mirror.startswith("file:"):
                mhost = "127.0.0.1"
            else:
                mhost = host(mirror)

            if mhost in timedhosts:
                result = timedhosts[mhost]
                if verbose:
                    print "%s already timed: %s" % (mhost, result)
                self.add_result(mirror, mhost, result)
            elif mhost in ("127.0.0.1", "::1", "localhost", prefer):
                self.add_result(mirror, mhost, 0)
            else:
                # No cached info. so spawn a thread and find the info. out
                self._init_lock()
                pollThread = PollThread(self, mirror)
                pollThread.start()
                self.threads.append(pollThread)
        while len(self.threads) > 0:
            if self.threads[0].isAlive():
                self.threads[0].join()
            del self.threads[0]

    def add_result(self, mirror, host, time):
        global timedhosts
        self._acquire_lock()
        if verbose: print " * %s : %f secs" % (host, time)
        self.results[mirror] = time
        timedhosts[host] = time
        self._release_lock()

class PollThread(threading.Thread):

    def __init__(self, parent, mirror):
        threading.Thread.__init__(self)
        self.parent = parent
        self.mirror = mirror
        self.host = host(mirror)
        uService = urlparse.urlparse(mirror)[0]
        if uService == "http":
            self.port = 80
        elif uService == "https":
            self.port = 443
        elif uService == "ftp":
            self.port = 21
        elif uService == "file":
            self.host = "127.0.0.1"
        else:
            self.port = -2

    def run(self):
        try:
            if self.host in timedhosts:
                result = timedhosts[self.host]
                if verbose:
                    print "%s already timed: %s" % (self.host, result)
            else:
                if self.host in ("127.0.0.1", "::1", "localhost", prefer):
                    result = 0
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    uPort = string.find(self.host,":")
                    if uPort > 0:
                        self.port = int(self.host[uPort+1:])
                        self.host = self.host[:uPort]
                    time_before = time.time()
                    sock.connect((self.host, self.port))
                    result = time.time() - time_before
                    sock.close()
            self.parent.add_result(self.mirror, self.host, result)
        except:
            if verbose:
                print " * %s : dead" % self.host
            self.parent.add_result(self.mirror, self.host, 99999999999)

def main():
    global verbose
    verbose = True

    if len(sys.argv) == 1:
        print "Usage: %s <mirror1> [mirror2] ... [mirrorN]" % sys.argv[0]
        sys.exit(-1)

    mirrorlist = sys.argv[1:]
    print "Result: " + str(FastestMirror(mirrorlist).get_mirrorlist()[0])

if __name__ == '__main__':
    main()
