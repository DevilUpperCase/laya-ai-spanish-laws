"""Project-owned local services. Commands: start, serve, status, stop."""
import argparse,json,os,socket,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
import psutil,httpx
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.runtime_lock import RuntimeLock

RUNTIME=ROOT/'private-data/runtime'
SPECS={
 'api':([sys.executable,str(ROOT/'scripts/run_api.py')],ROOT,8000),
 'laya':([sys.executable,str(ROOT/'scripts/serve_laya.py')],ROOT,8001),
 'web':(['node',str(ROOT/'apps/web/node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1'],ROOT/'apps/web',3000),
 'worker':([sys.executable,'-m','services.api.app.jobs'],ROOT,None),
 'indexer':([sys.executable,str(ROOT/'scripts/embed_corpus.py'),'--include-history'],ROOT,None),
 'dogc':([sys.executable,str(ROOT/'scripts/sync_dogc.py'),'--all','--skip-existing'],ROOT,None),
}


def spawn(command,cwd):
    env=os.environ.copy();env.update({'LANGSMITH_TRACING':'false','LANGCHAIN_TRACING_V2':'false','PYTHONUNBUFFERED':'1','HF_HUB_DISABLE_TELEMETRY':'1'})
    child=subprocess.Popen(command,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    process=psutil.Process(child.pid)
    process._laya_child=child  # Retain the OS handle/return code after the process disappears.
    return process


def exit_code(process):
    child=getattr(process,'_laya_child',None)
    if child is not None:return child.poll()
    try:return process.wait(timeout=0)
    except psutil.Error:return None


def owned(process,name):
    """Exact working directory and known script, including venv child wrappers."""
    try:
        cwd=Path(process.cwd()).resolve();cmd=process.cmdline()
        expected=SPECS[name]
        if cwd!=expected[1].resolve():return False
        if name=='web':
            return process.name().lower() in {'node.exe','node'} and len(cmd)>=3 and Path(cmd[1]).resolve()==(ROOT/'apps/web/node_modules/next/dist/bin/next').resolve() and cmd[2]=='start'
        if process.name().lower() not in {'python.exe','pythonw.exe','python','python3','python3.12'}:return False
        if name=='worker':return len(cmd)>=3 and cmd[1:3]==['-m','services.api.app.jobs']
        target=ROOT/'scripts'/{'api':'run_api.py','laya':'serve_laya.py','indexer':'embed_corpus.py','dogc':'sync_dogc.py'}[name]
        return len(cmd)>=2 and not cmd[1].startswith('-') and Path(cmd[1]).resolve()==target.resolve()
    except (psutil.Error,OSError):return False


def alive(process):
    try:return process.is_running() and process.status()!=psutil.STATUS_ZOMBIE
    except psutil.Error:return False


def terminate_owned(process,name):
    if not alive(process) or not owned(process,name):return
    try:
        children=process.children(recursive=True)
        for child in reversed(children):
            try:child.terminate()
            except psutil.Error:pass
        process.terminate()
        _,remaining=psutil.wait_procs(children+[process],timeout=5)
        for item in remaining:
            try:item.kill()
            except psutil.Error:pass
    except psutil.Error:pass


def bootstrap_containers():
    files=['compose.yaml','auth.compose.yaml','ops.compose.yaml']
    command=['docker','compose','--env-file',str(ROOT/'private-data/auth.env')]
    for file in files:
        if (ROOT/'infra'/file).exists():command+=['-f',str(ROOT/'infra'/file)]
    command+=['up','-d','--wait','--no-recreate']
    # Docker Desktop owns its own engine; launch its GUI in the background only if absent.
    probe=subprocess.run(['docker','info'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
    if probe.returncode and os.name=='nt':
        desktop=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Docker/Docker/Docker Desktop.exe'
        if desktop.exists():
            subprocess.Popen([str(desktop)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(30):
        result=subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=180)
        if result.returncode==0:return
        time.sleep(10)
    raise RuntimeError('Local containers did not become ready')


def serve():
    RUNTIME.mkdir(parents=True,exist_ok=True)
    with RuntimeLock(RUNTIME/'supervisor.lock'):
        (RUNTIME/'stop').unlink(missing_ok=True)
        bootstrap_containers()
        processes={};failures={};restart_at={};complete=set();sync=None;next_sync=0
        # Adopt only demonstrably project-owned existing services; never launch duplicates.
        for name in SPECS:
            matches=[p for p in psutil.process_iter() if owned(p,name)]
            if matches:
                # Keep the outer venv wrapper when both wrapper and child are present.
                ids={p.pid for p in matches};processes[name]=next((p for p in matches if p.ppid() not in ids),matches[0])
        try:
            while not (RUNTIME/'stop').exists():
                now=time.monotonic();services={}
                for name,(command,cwd,port) in SPECS.items():
                    process=processes.get(name)
                    if name in {'api','worker'} and (RUNTIME/'maintenance').is_file():
                        if process:terminate_owned(process,name);processes.pop(name,None)
                        services[name]={'state':'paused','pid':None,'restarts':failures.get(name,0)};continue
                    if process and not alive(process):
                        if name in {'indexer','dogc'}:
                            # Zero exit means no missing work. Recheck after daily ingestion.
                            code=exit_code(process)
                            if code==0:complete.add(name)
                        processes.pop(name,None);failures[name]=failures.get(name,0)+1
                        restart_at[name]=now+min(300,5*2**min(failures[name],6));process=None
                    if not process and name not in complete and now>=restart_at.get(name,0):
                        if port:
                            with socket.socket() as check:
                                try:check.bind(('127.0.0.1',port))
                                except OSError:
                                    services[name]={'state':'port_in_use_by_unowned_process'};continue
                        processes[name]=process=spawn(command,cwd)
                    services[name]={'state':'running' if process else ('complete' if name in complete else 'backoff'),'pid':process.pid if process else None,'restarts':failures.get(name,0)}
                if sync and not alive(sync):
                    code=exit_code(sync)
                    next_sync=now+(86400 if code==0 else 600);sync=None;complete.discard('indexer')
                if not sync and now>=next_sync:sync=spawn([sys.executable,str(ROOT/'scripts/daily_document_check.py')],ROOT)
                status={'generated_at':datetime.now(timezone.utc).isoformat(),'supervisor_pid':os.getpid(),'services':services,'daily_boe_sync':'running' if sync else 'scheduled','release_ready':False}
                temp=RUNTIME/'status.tmp';temp.write_text(json.dumps(status,indent=2)+'\n');temp.replace(RUNTIME/'status.json')
                time.sleep(5)
        finally:
            if sync and alive(sync):
                for p in reversed(sync.children(recursive=True)):
                    try:p.terminate()
                    except psutil.Error:pass
                try:sync.terminate()
                except psutil.Error:pass
            for name,process in processes.items():terminate_owned(process,name)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['start','serve','status','stop','pause','resume']);args=parser.parse_args();RUNTIME.mkdir(parents=True,exist_ok=True)
    if args.command=='serve':serve()
    elif args.command=='stop':(RUNTIME/'stop').write_text('stop');print('Stop requested for project-owned services. Database containers are retained.')
    elif args.command=='pause':(RUNTIME/'maintenance').write_text('maintenance');print('Pausing API and document worker for a consistent private-storage snapshot.')
    elif args.command=='resume':(RUNTIME/'maintenance').unlink(missing_ok=True);print('Local API and document worker will resume.')
    elif args.command=='start':
        try:
            with RuntimeLock(RUNTIME/'supervisor.lock'):spawn([sys.executable,str(Path(__file__).resolve()),'serve'],ROOT)
            print('Local supervisor starting; inspect status with local_stack.py status.')
        except RuntimeError:print('Local supervisor already running.')
    else:
        path=RUNTIME/'status.json';status=json.loads(path.read_text()) if path.exists() else {'state':'not_started'}
        if 'supervisor_pid' in status:
            try:status['supervisor_running']=psutil.Process(status['supervisor_pid']).is_running()
            except psutil.Error:status['supervisor_running']=False
        print(json.dumps(status,indent=2))


if __name__=='__main__':main()
