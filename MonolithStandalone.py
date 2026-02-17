from http.server import BaseHTTPRequestHandler
import socketserver
import json
from dbhelper import dbhelper
from urllib.parse import urlparse, parse_qs
import traceback
import os
import re

PORT=8000 

class MonolithHandler(BaseHTTPRequestHandler):
    editorhtml = 0
    db = dbhelper()

    def preload(self):
        if not self.editorhtml:
            f = open('WebEditor/Editor.html','r', encoding='utf-8')
            l = f.read()
            f.close()
            self.editorhtml = l

    def _set_headers(self,mimetype='text/html'):
        self.send_response(200)
        self.send_header('Content-type', mimetype)
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers()

    def do_GET(self):
        uripath = self.path
        self.preload()        
        if uripath == '/':
            self._set_headers()
            self.wfile.write(self.editorhtml.encode('utf-8'))
        else:
            a = urlparse(uripath)
            fn = a.path[1:]
            fpath = "WebEditor/" + fn
            if os.path.exists(fpath):
                f = open(fpath,mode='rb')
                l = f.read()
                f.close()
                mimetype = 'text/html'
                if '.js' in fpath: mimetype = 'text/javascript'
                elif '.css' in fpath: mimetype = 'text/css'
                elif '.woff' in fpath: mimetype = 'application/font-woff'
                elif '.ttf' in fpath: mimetype = 'application/x-font-ttf'
                elif '.eot' in fpath: mimetype = 'application/vnd.ms-fontobject'
                elif '.otf' in fpath: mimetype = 'application/x-font-opentype'
                elif '.svg' in fpath: mimetype = 'image/svg+xml'
                elif '.woff2' in fpath: mimetype = 'application/font-woff2'
                self._set_headers(mimetype)
                self.wfile.write(l)
            else:
                self.send_error(404,'File not found ' + fpath)

    def do_HEAD(self):
        self._set_headers()
        
    def do_POST(self):
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length).decode('utf-8') # <--- Gets the data itself
        self._set_headers()
        uripath = self.path
        #POST /WebApi.ashx?req=Tree&xxxallowexception=1
        if uripath.lower().startswith("/webapi.ashx"):
            qs = parse_qs(urlparse(uripath).query)
            if 'req' in qs:
                qvar = qs['req'][0]
                if qvar == 'Tree':
                    r = self.db.GetTreePath(None)
                    self.wfile.write(r.encode('utf-8'))
                elif qvar == 'Code':
                    #url: "WebApi.ashx?req=Code&id=" + id + '&xxxallowexception=1',
                    codeid = qs['id'][0]
                    r = self.db.GetCode(codeid)
                    self.wfile.write(r.encode('utf-8'))
                elif qvar == 'SaveCode':
                    code = parse_qs(post_data)['code'][0]
                    codeid = qs['codeid'][0]
                    r = self.db.SaveCode(codeid,code)
                    self.wfile.write(r.encode('utf-8'))
                elif qvar == 'RenameCode':
                    pid = qs['pid'][0]
                    codename = qs['codename'][0]
                    r = self.db.RenameCode(pid,codename)
                    self.wfile.write(r.encode('utf-8'))
                elif qvar == 'NewScope':
                    pid = qs['pid'][0]
                    scopename = qs['scopename'][0]
                    issystem = qs['issystem'][0]
                    r = self.db.NewScope(pid,scopename,issystem)
                    self.wfile.write(r.encode('utf-8'))
                elif qvar == 'NewCode':
                    pid = qs['pid'][0]
                    codename = qs['codename'][0]
                    issystem = qs['issystem'][0]
                    codetype = qs['codetype'][0]
                    isversioned = qs['isversioned'][0]
                    r = self.db.NewCode(pid,codename,issystem,codetype,isversioned)
                    self.wfile.write(r.encode('utf-8'))
                elif qvar == 'MoveCode':
                    codeID = qs['codeID'][0]
                    newScopeID = qs['newScopeID'][0]
                    r = self.db.MoveCode(codeID,newScopeID)
                    self.wfile.write(r.encode('utf-8'))
                elif qvar == 'CodeHistory':
                    codeid = qs['codeid'][0]
                    r = self.db.CodeHistory(codeid)
                    self.wfile.write(r.encode('utf-8'))
                elif qvar == 'CodeDemo':
                    code = parse_qs(post_data)['code'][0]
                    try:
                        compile(code,'codedemo','exec')
                    except Exception as ex:
                        m = str(ex) + "\n" + traceback.format_exc()    
                        self.wfile.write(m.encode('utf-8'))
                    if not 'def Test():' in code:
                        return 'Code is missing test function!'
                    try:
                        newcode = code + "\n" + "a = Test()"
                        from PythonRunner import PythonRunner
                        mod = PythonRunner.PythonRunDict('test',newcode)
                        self.wfile.write(str(mod.__dict__.get('a','FAILED')).encode('utf-8'))
                    except Exception as ex:
                        m = str(ex) + "\n" + traceback.format_exc()    
                        #print 'CodeDemo Exception ' + str(m)
                        self.wfile.write(('EXCEPTION: ' + str(m)).encode('utf-8'))
                elif qvar == 'EvaluateCode':
                    code = parse_qs(post_data)['code'][0]
                    try:
                        compile(code,'evaluatecode','exec')                    
                        d = { 'Text': 'SUCCESS' }
                        r = json.dumps(d)
                        #print 'EvaluateCode success ' + r
                        self.wfile.write(r.encode('utf-8'))
                    except Exception as ex:
                        import sys
                        tbm = traceback.format_exc()
                        linenum = re.findall(r'File "evaluatecode", line (\d+)',tbm)[0]
                        ret = {
                            "Span": { "Start" : { "Column": "1", "Line": str(linenum) }, "End": { "Column": "2", "Line": str(linenum) } },
                            "Text": str(ex)
                            }
                        jret = json.dumps(ret)
                        self.wfile.write(jret.encode('utf-8'))
                else:
                    print ('Unknown request ' + str(qs['req']))
            else:
                print ('Missing request ' + str(qs))
            #print '/WebApi.ashx: ' + uripath + ' QS: ' + str(qs)
        else:
            print ('POST unknown path ' + uripath)

# Note this requires a request after you press cntrl-C
class StoppableHTTPServer(socketserver.TCPServer):
    def run(self):
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            print ('Calling close')
            # Clean-up server (close socket, etc.)
            self.server_close()

def Run():
    httpd = StoppableHTTPServer(('127.0.0.1', PORT), MonolithHandler)
    print ('Starting httpd... http://localhost:' + str(PORT))
    httpd.run()

Run()

