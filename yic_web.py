import web
import yic

render = web.template.render('templates/')

urls = ('/list', 'list',
        '/get', 'get')
app = web.application(urls, globals())

class list:
    def GET(self):
        listFile = yic.listFile()
        return render.list(listFile)

class get:
    def GET(self):
        getFile = yic.getFile()
        return render.get(getFile)

if __name__=="__main__":
    web.internalerror = web.debugerror
    app.run()
