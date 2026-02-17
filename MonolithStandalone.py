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
        uripath = self.path
        #POST /WebApi.ashx?req=Tree&xxxallowexception=1
        if uripath.lower().startswith("/webapi.ashx"):
            qs = parse_qs(urlparse(uripath).query)
            if 'req' in qs:
                qvar = qs['req'][0]
                # Set content type based on request type - must be done before writing
                if qvar in ['SaveAISettings', 'GetAISettings', 'AIChat', 'GetAIModels']:
                    self._set_headers('application/json')
                else:
                    self._set_headers('text/html')
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
                elif qvar == 'SaveAISettings':
                    try:
                        params = parse_qs(post_data)
                        provider = params.get('provider', [''])[0]
                        apikey = params.get('apikey', [''])[0]
                        model = params.get('model', [''])[0]
                        print(f"SaveAISettings: provider={provider}, model={model}, apikey={'***' if apikey else 'empty'}")
                        r = self.db.SaveAISettings(provider, apikey, model)
                        print(f"SaveAISettings response: {r}")
                        self.wfile.write(r.encode('utf-8'))
                    except Exception as ex:
                        error_response = json.dumps({'status': 'FAILED', 'message': str(ex)})
                        print(f"SaveAISettings error: {ex}")
                        self.wfile.write(error_response.encode('utf-8'))
                    return
                elif qvar == 'GetAISettings':
                    try:
                        r = self.db.GetActiveAISettings()
                        print(f"GetAISettings response: {r}")
                        self.wfile.write(r.encode('utf-8'))
                    except Exception as ex:
                        error_response = json.dumps({'status': 'FAILED', 'message': str(ex)})
                        print(f"GetAISettings error: {ex}")
                        self.wfile.write(error_response.encode('utf-8'))
                    return
                elif qvar == 'GetAIModels':
                    try:
                        params = parse_qs(post_data)
                        provider = params.get('provider', [''])[0]
                        apikey = params.get('apikey', [''])[0]
                        
                        if not provider or not apikey:
                            self.wfile.write(json.dumps({'status': 'FAILED', 'message': 'Provider and API key required'}).encode('utf-8'))
                            return
                        
                        models = []
                        if provider == 'openai':
                            try:
                                import openai
                                client = openai.OpenAI(api_key=apikey)
                                
                                # Fetch available models from OpenAI API
                                print(f"Fetching OpenAI models from API...")
                                models_response = client.models.list()
                                
                                # Filter for chat models (GPT models)
                                for model in models_response.data:
                                    model_id = model.id.lower()
                                    if 'gpt' in model_id:
                                        # Create friendly name
                                        name = model.id
                                        if 'gpt-4' in model_id:
                                            if 'turbo' in model_id:
                                                name = f"GPT-4 Turbo ({model.id})"
                                            elif 'vision' in model_id:
                                                name = f"GPT-4 Vision ({model.id})"
                                            else:
                                                name = f"GPT-4 ({model.id})"
                                        elif 'gpt-3.5' in model_id:
                                            name = f"GPT-3.5 ({model.id})"
                                        
                                        models.append({
                                            'id': model.id,
                                            'name': name,
                                            'created': model.created
                                        })
                                        print(f"  ✓ {model.id}")
                                
                                # Sort by creation date (newest first)
                                models.sort(key=lambda x: x['created'], reverse=True)
                                
                                if not models:
                                    self.wfile.write(json.dumps({'status': 'FAILED', 'message': 'No GPT models available with this API key'}).encode('utf-8'))
                                    return
                            except Exception as ex:
                                self.wfile.write(json.dumps({'status': 'FAILED', 'message': f'OpenAI error: {str(ex)}'}).encode('utf-8'))
                                return
                        elif provider == 'claude':
                            try:
                                import anthropic
                                client = anthropic.Anthropic(api_key=apikey)
                                
                                # Fetch available models from Claude API
                                print(f"Fetching Claude models from API...")
                                models_response = client.models.list()
                                
                                for model in models_response.data:
                                    models.append({
                                        'id': model.id,
                                        'name': model.display_name if hasattr(model, 'display_name') else model.id,
                                        'created': 0
                                    })
                                    print(f"  ✓ {model.id}")
                                
                                if not models:
                                    self.wfile.write(json.dumps({'status': 'FAILED', 'message': 'No Claude models available with this API key'}).encode('utf-8'))
                                    return
                            except Exception as ex:
                                self.wfile.write(json.dumps({'status': 'FAILED', 'message': f'Claude error: {str(ex)}'}).encode('utf-8'))
                                return
                        else:
                            self.wfile.write(json.dumps({'status': 'FAILED', 'message': 'Unknown provider'}).encode('utf-8'))
                            return
                        
                        self.wfile.write(json.dumps({'status': 'SUCCESS', 'models': models}).encode('utf-8'))
                    except Exception as ex:
                        error_response = json.dumps({'status': 'FAILED', 'message': str(ex)})
                        print(f"GetAIModels error: {ex}")
                        traceback.print_exc()
                        self.wfile.write(error_response.encode('utf-8'))
                    return
                elif qvar == 'AIChat':
                    params = parse_qs(post_data)
                    prompt = params.get('prompt', [''])[0]
                    code = params.get('code', [''])[0]
                    try:
                        settings_json = self.db.GetActiveAISettings()
                        settings = json.loads(settings_json)
                        if settings.get('status') != 'SUCCESS':
                            self.wfile.write(json.dumps({'status': 'FAILED', 'message': 'No AI settings configured'}).encode('utf-8'))
                            return
                        
                        provider = settings['provider']
                        apikey = settings['apikey']
                        model = settings['model']
                        
                        full_prompt = f"Here is the code:\n\n{code}\n\nUser request: {prompt}\n\nPlease provide the refactored code. Return ONLY the code without explanations."
                        
                        if provider == 'openai':
                            import openai
                            client = openai.OpenAI(api_key=apikey)
                            response = client.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": "You are a code refactoring assistant. Return only code without explanations or markdown formatting."},
                                    {"role": "user", "content": full_prompt}
                                ]
                            )
                            result = response.choices[0].message.content
                        elif provider == 'claude':
                            import anthropic
                            client = anthropic.Anthropic(api_key=apikey)
                            response = client.messages.create(
                                model=model,
                                max_tokens=4096,
                                messages=[
                                    {"role": "user", "content": full_prompt}
                                ]
                            )
                            result = response.content[0].text
                        else:
                            self.wfile.write(json.dumps({'status': 'FAILED', 'message': 'Unknown provider'}).encode('utf-8'))
                            return
                        
                        # Clean up code blocks if present
                        if '```' in result:
                            lines = result.split('\n')
                            code_lines = []
                            in_code = False
                            for line in lines:
                                if line.strip().startswith('```'):
                                    in_code = not in_code
                                    continue
                                if in_code or not any(line.strip().startswith(x) for x in ['```']):
                                    code_lines.append(line)
                            result = '\n'.join(code_lines).strip()
                        
                        self.wfile.write(json.dumps({'status': 'SUCCESS', 'code': result}).encode('utf-8'))
                    except Exception as ex:
                        error_msg = str(ex) + "\n" + traceback.format_exc()
                        self.wfile.write(json.dumps({'status': 'FAILED', 'message': error_msg}).encode('utf-8'))
                    return
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

