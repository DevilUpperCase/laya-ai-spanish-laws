from pathlib import Path
import time
import pytest
from scripts import local_stack as stack


class Process:
    def __init__(self,args,name='python.exe',cwd=None):self.args=args;self.exe=name;self.directory=cwd or stack.ROOT
    def cwd(self):return str(self.directory)
    def cmdline(self):return self.args
    def name(self):return self.exe


def test_python_data_argument_cannot_establish_process_ownership():
    assert not stack.owned(Process(['python','other_job.py',str(stack.ROOT/'scripts/run_api.py')]),'api')
    assert not stack.owned(Process(['python',str(stack.ROOT/'other/scripts/run_api.py')]),'api')
    assert stack.owned(Process(['python',str(stack.ROOT/'scripts/run_api.py')]),'api')
    assert stack.owned(Process(['python','-m','services.api.app.jobs']),'worker')
    assert not stack.owned(Process(['python','other_job.py','services.api.app.jobs']),'worker')


def test_next_data_argument_cannot_establish_process_ownership():
    script=str(stack.ROOT/'apps/web/node_modules/next/dist/bin/next')
    assert not stack.owned(Process(['node','other.js',script,'start'],'node.exe',stack.ROOT/'apps/web'),'web')
    assert not stack.owned(Process(['node',script,'dev'],'node.exe',stack.ROOT/'apps/web'),'web')
    assert stack.owned(Process(['node',script,'start','--hostname','127.0.0.1'],'node.exe',stack.ROOT/'apps/web'),'web')


@pytest.mark.parametrize('code',[0,7])
def test_background_exit_status_survives_process_disappearance(code):
    process=stack.spawn([stack.sys.executable,'-c',f'raise SystemExit({code})'],stack.ROOT)
    for _ in range(100):
        if not stack.alive(process):break
        time.sleep(.02)
    assert stack.exit_code(process)==code
    assert stack.exit_code(process)==code
