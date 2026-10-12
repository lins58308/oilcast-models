#!/usr/bin/env python3
"""Compile the existing Java model core on any JDK17 CPU runner."""
import argparse,base64,datetime,hashlib,json,os,pathlib,subprocess,tempfile,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
JSON_URL='https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar'
JSON_SHA='3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed'

def compile_sources(jar=None):
    build=ROOT/'build';build.mkdir(exist_ok=True)
    jar=pathlib.Path(jar) if jar else build/'json.jar'
    if not jar.exists():
        with urllib.request.urlopen(JSON_URL,timeout=45) as response:jar.write_bytes(response.read())
    if hashlib.sha256(jar.read_bytes()).hexdigest()!=JSON_SHA:raise RuntimeError('JSON dependency checksum mismatch')
    classes=build/'classes';classes.mkdir(exist_ok=True)
    subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','11','-encoding','UTF-8','-cp',str(jar),'-d',str(classes),*[str(p) for p in (ROOT/'core').glob('*.java')],*[str(p) for p in (ROOT/'src').glob('*.java')]],check=True)
    return str(classes)+os.pathsep+str(jar)

def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--as-of',default='2026-09-13T13:00:00Z');p.add_argument('--output',type=pathlib.Path,default=ROOT/'output');p.add_argument('--checkpoint',type=pathlib.Path,default=ROOT/'checkpoint.json');p.add_argument('--json-jar');p.add_argument('--signing-key',type=pathlib.Path);p.add_argument('--model-url',default='');a=p.parse_args()
    if a.live:a.as_of=datetime.datetime.now(datetime.timezone.utc).isoformat()
    cp=compile_sources(a.json_jar);secret=os.environ.get('MODEL_SIGNING_KEY_B64');key=a.signing_key;temporary=None
    try:
        if secret and not key:
            fd,temporary=tempfile.mkstemp(prefix='oilcast-key-');os.chmod(temporary,0o600)
            with os.fdopen(fd,'wb') as out:out.write(base64.b64decode(secret,validate=True))
            key=pathlib.Path(temporary)
        subprocess.run(['java','-cp',cp,'CloudTrainer',str(ROOT),str(a.output.resolve()),str(a.live).lower(),a.as_of,str(a.checkpoint.resolve()),str(key.resolve()) if key else '',a.model_url],check=True)
    finally:
        if temporary:os.unlink(temporary)

if __name__=='__main__':main()
