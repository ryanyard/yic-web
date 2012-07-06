import json
from restful_lib import Connection

base_url = "http://localhost:8080/documents/"
conn = Connection(base_url)

def getRest():
  resp = conn.request_get("CORE.rc", args={}, headers={'content-type':'application/json', 'accept':'application/json'})
  results = json.loads(resp[u'body'])
  print results['DESCRIPTION']

def main():
  getRest()

if __name__ == '__main__':
    main()
