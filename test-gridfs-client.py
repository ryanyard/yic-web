from pymongo import Connection
from gridfs import GridFS

def getGridFile():
  db = Connection().mydatabase
  fs = GridFS(db)
  version = fs.get_last_version(filename="IDMAPD_post.sh")
  print version.read()

def main():
  getGridFile()

if __name__ == '__main__':
    main()
