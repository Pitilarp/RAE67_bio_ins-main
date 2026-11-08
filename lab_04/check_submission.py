"""Public self-check, not a security sandbox or a full 20-point grade."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

WORKER = '''import importlib.util,json,math,sys
spec=importlib.util.spec_from_file_location("candidate",sys.argv[1]); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
results=[]
def case(name,fn):
    try: fn(); results.append({"case":name,"passed":True})
    except Exception as e: results.append({"case":name,"passed":False,"error":type(e).__name__+": "+str(e)})
def eq(a,b):
    assert math.isclose(a,b,abs_tol=1e-10), (a,b)
def state(h,s,p,c,b,expected):
    d=m.step(h,s,.05,p,c,b)
    for k,v in expected.items(): eq(d[k],v)
case("receptor normalization",lambda:eq(m.receptor(.2,.1,.5),.25))
case("receptor lower clamp",lambda:eq(m.receptor(-.1),0))
case("receptor upper clamp",lambda:eq(m.receptor(2),1))
def invalid_range():
    try: m.receptor(.2,.5,.5)
    except ValueError: return
    raise AssertionError("expected ValueError")
case("invalid receptor range",invalid_range)
case("first on update",lambda:state(0,1,.8,.6,.2,{"h":.04,"r":.04,"p":.8,"c":0,"b":0,"fault":0}))
case("second on update uses old state",lambda:state(.04,1,.8,.6,.2,{"h":.0784,"c":.024,"b":.008}))
case("off update",lambda:state(.2,0,.8,.6,.2,{"h":.192,"raw":.192}))
case("upper clamp preserves raw",lambda:state(.99,1,5,.6,.2,{"h":1,"raw":1.2004}))
case("no binding",lambda:state(.2,1,.8,.6,0,{"h":.234,"b":0}))
for value in [float("nan"),float("inf"),-.1,1.1]:
    case("fault "+str(value),lambda v=value:state(.7,v,.8,.6,.2,{"h":0,"r":0,"raw":0,"p":0,"c":0,"b":0,"fault":1}))
print(json.dumps(results));sys.exit(0 if all(r["passed"] for r in results) else 1)
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student-file",default="student_hormone.py")
    args=parser.parse_args()
    source=Path(args.student_file).resolve()
    # Scrub inherited application secrets. Isolation/timeout is not an OS sandbox.
    environment={k:v for k,v in os.environ.items() if k.upper() in {"SYSTEMROOT","WINDIR","PATH"}}
    with tempfile.TemporaryDirectory(prefix="lab04-check-") as temp:
        environment.update(TEMP=temp,TMP=temp)
        try:
            result=subprocess.run([sys.executable,"-I","-c",WORKER,str(source)],cwd=temp,
                                  env=environment,capture_output=True,text=True,timeout=10)
        except subprocess.TimeoutExpired:
            print("FAIL: timeout (10 s)"); return 1
    if result.stdout: print(result.stdout)
    if result.stderr: print(result.stderr,file=sys.stderr)
    return result.returncode

if __name__=="__main__": sys.exit(main())
