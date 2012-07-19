import json
import bottle
from bottle import route, run, request, abort
from pymongo import Connection

connection = Connection('localhost', 27017)
db = connection.mydatabase

@route('/documents', method='PUT')
def put_document():
	data = request.body.readline()
	if not data:
		abort(400, 'No data received')
	entity = json.loads(data)
	if not entity.has_key('_id'):
		abort(400, 'No _id specified')
	try:
		db['documents'].save(entity)
	except ValidationError as ve:
		abort(400, str(ve))
	
@route('/documents/:id', method='GET')
def get_document(id):
	entity = db['documents'].find_one({'_id':id})
	if not entity:
		abort(404, 'No document with id %s' % id)
	return entity

@route('/documents/:id/datafiles', method='GET')
def get_document(id):
        entity = db['documents'].find_one({'_id':id})
        datafiles = entity['DATAFILES'].split(' ')
        if not entity:
                abort(404, 'No document with id %s' % id)
        return datafiles

@route('/documents/:id/prescripts', method='GET')
def get_document(id):
        entity = db['documents'].find_one({'_id':id})
	processPreScripts = entity['PRE_INSTALL_SCRIPTS'].split(' ')
        if not entity:
                abort(404, 'No document with id %s' % id)
        return processPreScripts

@route('/documents/:id/postscripts', method='GET')
def get_document(id):
        entity = db['documents'].find_one({'_id':id})
	processPostScripts = entity['POST_INSTALL_SCRIPTS'].split(' ')
        if not entity:
                abort(404, 'No document with id %s' % id)
        return processPostScripts

@route('/documents/:id/preunscripts', method='GET')
def get_document(id):
        entity = db['documents'].find_one({'_id':id})
        processPreUnScripts = entity['PRE_UNINSTALL_SCRIPTS'].split(' ')
        if not entity:
                abort(404, 'No document with id %s' % id)
        return processPreUnScripts

@route('/documents/:id/postunscripts', method='GET')
def get_document(id):
        entity = db['documents'].find_one({'_id':id})
        processPostUnScripts = entity['POST_UNINSTALL_SCRIPTS'].split(' ')
        if not entity:
                abort(404, 'No document with id %s' % id)
        return processPostUnScripts

run(host='0.0.0.0', port=8080)
