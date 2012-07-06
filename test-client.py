from restful_lib import Connection

# Should also work with https protocols
base_url = "http://localhost:8080/documents"
conn = Connection(base_url)
result0 = conn.request_get("CORE.rc", args={}, headers={'Accept':'text/json'})
result1 = conn.request_get("IDMAPD.rc", args={}, headers={'Accept':'text/json'})
print result0
print result1
