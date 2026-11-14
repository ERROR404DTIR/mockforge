#!/usr/bin/env python3
"""MockForge: a loopback-only JSON API mock server (Python standard library)."""
import argparse, json, re, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DEFAULT={"routes":[
 {"method":"GET","path":"/api/health","status":200,"body":{"ok":True,"service":"mockforge"}},
 {"method":"GET","path":"/api/users/{id}","status":200,"body":{"id":"{{id}}","name":"Demo User"}},
 {"method":"POST","path":"/api/echo","status":201,"body":{"received":"{{body}}"}}
]}
def load_config(path=None):
 data=json.loads(Path(path).read_text(encoding="utf-8")) if path else DEFAULT
 if not isinstance(data,dict) or not isinstance(data.get("routes"),list): raise ValueError("Config must contain a routes array")
 for i,r in enumerate(data["routes"]):
  if not isinstance(r,dict) or not isinstance(r.get("method"),str) or not isinstance(r.get("path"),str): raise ValueError(f"Invalid route {i}")
  if not r["path"].startswith("/") or ".." in r["path"].split("/"): raise ValueError(f"Unsafe path in route {i}")
  status=int(r.get("status",200))
  if not 100<=status<=599: raise ValueError(f"Invalid status in route {i}")
 return data
def match_route(routes,method,path):
 for route in routes:
  if route["method"].upper()!=method.upper(): continue
  names=re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}",route["path"])
  pattern="^"+re.sub(r"\{[A-Za-z_][A-Za-z0-9_]*\}",r"([^/]+)",route["path"])+"$"
  found=re.match(pattern,path)
  if found: return route,dict(zip(names,found.groups()))
 return None,{}
def render(value,params,body):
 if isinstance(value,dict): return {k:render(v,params,body) for k,v in value.items()}
 if isinstance(value,list): return [render(v,params,body) for v in value]
 if isinstance(value,str):
  if value=="{{body}}": return body
  for key,val in params.items(): value=value.replace("{{"+key+"}}",val)
 return value
def make_handler(config):
 class Handler(BaseHTTPRequestHandler):
  server_version="MockForge/1.0"
  def log_message(self,fmt,*args): print("[mockforge] "+(fmt%args))
  def do_OPTIONS(self):
   self.send_response(204); self.send_header("Access-Control-Allow-Origin","*"); self.send_header("Access-Control-Allow-Headers","Content-Type, Authorization"); self.send_header("Access-Control-Allow-Methods","GET,POST,PUT,PATCH,DELETE,OPTIONS"); self.end_headers()
  def _handle(self):
   path=urlparse(self.path).path
   route,params=match_route(config["routes"],self.command,path)
   if route is None: self._send(404,{"error":"No mock route matched","path":path}); return
   try:
    length=min(int(self.headers.get("Content-Length","0") or 0),1_000_000)
    raw=self.rfile.read(length) if self.command in ("POST","PUT","PATCH") else b""
    payload=json.loads(raw) if raw else None
   except (ValueError,json.JSONDecodeError):
    self._send(400,{"error":"Request body must be valid JSON"}); return
   time.sleep(max(0,min(int(route.get("delay_ms",0)),10000))/1000)
   self._send(int(route.get("status",200)),render(route.get("body",{}),params,payload),route.get("headers",{}))
  def _send(self,status,data,headers=None):
   blob=json.dumps(data,ensure_ascii=False).encode("utf-8")
   self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(blob))); self.send_header("Access-Control-Allow-Origin","*")
   for key,value in (headers or {}).items():
    if re.fullmatch(r"[A-Za-z0-9-]+",str(key)) and "\\r" not in str(value) and "\\n" not in str(value) and str(key).lower() not in ("content-length","transfer-encoding","connection"): self.send_header(str(key),str(value))
   self.end_headers(); self.wfile.write(blob)
  do_GET=_handle; do_POST=_handle; do_PUT=_handle; do_PATCH=_handle; do_DELETE=_handle
 return Handler
def main():
 p=argparse.ArgumentParser(description="Run a local mock JSON API")
 p.add_argument("--config"); p.add_argument("--host",default="127.0.0.1"); p.add_argument("--port",type=int,default=8787); args=p.parse_args()
 if args.host not in ("127.0.0.1","localhost","::1"): p.error("Safety default: bind to loopback only")
 try: config=load_config(args.config)
 except (OSError,ValueError,json.JSONDecodeError) as exc: p.error(str(exc))
 server=ThreadingHTTPServer((args.host,args.port),make_handler(config))
 print(f"MockForge listening at http://{args.host}:{args.port} (Ctrl+C to stop)")
 try: server.serve_forever()
 except KeyboardInterrupt: print("\\nStopping MockForge...")
 finally: server.server_close()
if __name__=="__main__": main()
