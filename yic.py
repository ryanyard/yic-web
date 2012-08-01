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
# written by Ed Brand
#            Ryan Yard <ryard@redhat.com>

import os, sys, time, logging, inspect, json
sys.path.append("/usr/share/yum-cli")
import cli, yum
import yic_snapshot, yic_fastmirror
from subprocess import call
from optparse import OptionParser
import restful_lib, pymongo
from gridfs import GridFS

url = ""
datafile = {}
path = "/path/"
build = "build"
tmp_path = "/tmp/yic"
script_prefix = "/scripts/"
datafile_prefix = "/datafiles/"
snapshot_file = "/.snapshot"

mirrorlist = ["http://localhost/", "http://localhost/"]
#mirrorlist = ["http://mirror.overthewire.com.au/pub/epel/", "http://epel.mirrors.arminco.com/", "http://mirror.iprimus.com.au/epel/"]

db = pymongo.Connection().mydatabase
fs = GridFS(db)

log_file = "/var/log/yic/yic.log"
log_format = '%(asctime)s - %(name)s:%(levelname)s:%(message)s'
logging.basicConfig(format=log_format, filename=log_file, level=logging.DEBUG) 

def cleanup():
  # need to work on this
  return

def getFastestMirror():
  global url
  url = yic_fastmirror.FastestMirror(mirrorlist).get_mirrorlist()[0]
  return url

def funcname():
  return inspect.stack()[1][3]

def logit(function, log):
  logging.info('======================================================================')
  logging.info('Processing %s : %s', function, log)
  logging.info('======================================================================')

def snapShot():
  if os.path.exists(snapshot_file):
    snapshot_tag = "yic_" + time.strftime("%Y%m%d%H%M%S")
    volumes = yic_snapshot.get_volumes()
    for volume in volumes:
      yic_snapshot.create_lvm_snapshot(snapshot_tag, volume)
    return 
  else:
    logit(funcname(), "No Snapshot")
 
def processDataFile(file):
  logit(funcname(), file)
  try:
    install()
    #uninstall()
  except(), e:
     logging.debug('%s: Failure', funcname())
 
def parseDataFile(file):
  global datafile
  url = "http://localhost/documents/"
  conn = restful_lib.Connection(url)
  resp = conn.request_get(file, args={}, headers={'content-type':'application/json', 'accept':'application/json'})
  datafile = json.loads(resp[u'body'])
  return datafile

def getGridFile(file, output):
  gridfile = fs.get_last_version(file)
  if not os.path.exists(tmp_path + script_prefix):
    os.makedirs(tmp_path + script_prefix)
  if output == 0:
    with open(tmp_path + script_prefix + file, "w") as lfile:
      lfile.write(gridfile.read())
  else:
    with open(output, "w") as lfile:
      lfile.write(gridfile.read())

def install():
  processPreScripts(script_prefix)
  installRPMs()
  processPostScripts(script_prefix)

def uninstall():
  processPreUnScripts(script_prefix)
  removeRPMs()
  processPostUnScripts(script_prefix)

def processDataFiles(file):
  try:
    parseDataFile(file)
    processDataFile(file)
    if datafile['DATAFILES']:
      for rc in datafile['DATAFILES'].split(' '):
        parseDataFile(rc)
        processDataFile(rc)
        logit(funcname(), file)
  except(), e:
    logging.debug('%s: unable to process', funcname())
 
def processPreScripts(prefix):
  if datafile['PRE_INSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['PRE_INSTALL_SCRIPTS'].split(' '):
      getGridFile(sh, 0)
      runScript(sh)
      logit(funcname(), sh)
    
def processPreUnScripts(prefix):
  if datafile['PRE_UNINSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['PRE_UNINSTALL_SCRIPTS'].split(' '):
      getGridFile(sh, 0)
      runScript(sh)
      logit(funcname(), sh)
 
def processPostScripts(prefix):
  if datafile['POST_INSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['POST_INSTALL_SCRIPTS'].split(' '):
      getGridFile(sh, 0)
      runScript(sh)
      logit(funcname(), sh)
 
def processPostUnScripts(prefix):
  if datafile['POST_UNINSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['POST_UNINSTALL_SCRIPTS'].split(' '):
      getGridFile(sh, 0)
      runScript(sh)
      logit(funcname(), sh)
 
def runScript(file):
  script = tmp_path + script_prefix + file
  chmod = "/bin/chmod 755 " + script
  try:
    call(chmod, shell=True)
    call(script, shell=True)
  except(), e:
    logging.debug('%s: Failure', funcname()) 

def yumInstall(pkgname):
  ybc = cli.YumBaseCli()
  ybc.doConfigSetup()
  ybc.doTsSetup()
  ybc.doRpmDBSetup()
  ybc.installPkgs(pkgname)
  ybc.buildTransaction()
  ybc.doTransaction()

def yumRemove(pkgname):
  ybc = cli.YumBaseCli()
  ybc.doConfigSetup()
  ybc.doTsSetup()
  ybc.doRpmDBSetup()
  ybc.removePkgs(pkgname)
  ybc.buildTransaction()
  ybc.doTransaction()

def installRPMs():
  pkglist = []
  if datafile['RPMLIST']:
    try:
      for rpm in datafile['RPMLIST'].split(' '):
        pkglist.append(rpm)
      yumInstall(pkglist)
    except(), e:
      logging.debug('%s: Failure', funcname())

def removeRPMs():
  pkglist = []
  if datafile['RPMLIST']:
    try:
      for rpm in datafile['RPMLIST'].split(' '):
        pkglist.append(rpm)
      yumRemove(pkglist)
    except(), e:
      logging.debug('%s: Failure', funcname())
 
def main():
  usage = "usage: %prog [options] filename"
  parser = OptionParser(usage=usage)
  parser.add_option("-f", "--file", type="string", dest="filename",
                    help="datafile name", metavar="FILE")
  parser.add_option("-g", "--get", type="string", dest="gridfile",
                    help="get files", metavar="FILE")
  parser.add_option("-o", "--out", type="string", dest="outfile",
                    help="output dest", metavar="DEST")
  parser.add_option("-v", "--verbose",
                    action="store_true", dest="verbose")
  parser.add_option("-q", "--quiet",
                    action="store_false", dest="verbose")

  try:
    (options, args) = parser.parse_args()
    if options.gridfile:
      getGridFile(sys.argv[2], sys.argv[4])
      exit(0)
    if options.filename is None:
      parser.print_help()
      exit(-1)
    snapShot()
    processDataFiles(sys.argv[2])
  except(), e:
    print "Error: %s" %e
    sys.exit(1)
 
if __name__ == '__main__':
    main()
