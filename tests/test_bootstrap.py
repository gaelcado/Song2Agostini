"""Installer contract checks; synthetic files only, no musical reference."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/bootstrap.py'
spec=importlib.util.spec_from_file_location('installer',SCRIPT)
installer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

def test_dry_run_does_not_create_runtime(tmp_path):
    target=tmp_path/'not-created'
    run=subprocess.run([sys.executable,str(SCRIPT),'--dry-run','--only','app','--runtime-root',str(target)],capture_output=True,text=True)
    assert run.returncode==0
    assert json.loads(run.stdout)['engines']==['app']
    assert not target.exists()

def test_existing_corrupt_model_is_never_overwritten(tmp_path):
    target=tmp_path/'weights';target.write_bytes(b'corrupt')
    with pytest.raises(RuntimeError,match='Hash invalide'):
        installer.download('https://example.invalid/unused',target,'0'*64)
    assert target.read_bytes()==b'corrupt'

def test_absent_runtime_is_not_ready(tmp_path):
    config=json.loads((SCRIPT.parents[1]/'configs/install/runtime.json').read_text())
    result=installer.doctor(SCRIPT.parents[1],tmp_path,['app'],config)
    assert not result['ready']
    assert not result['engines']['app']['installed']


def test_windows_cp1252_console_outputs_utf8_diagnostic(tmp_path):
    import os
    code=("import importlib.util,sys; from pathlib import Path; "
          "s=importlib.util.spec_from_file_location('installer',sys.argv[1]); "
          "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
          "m.configure_output(); m.execute([sys.executable,'-c','print(1)'],Path(sys.argv[2]))")
    run=subprocess.run([sys.executable,'-c',code,str(SCRIPT),str(tmp_path/'log')],capture_output=True,env={**os.environ,'PYTHONIOENCODING':'cp1252'})
    assert run.returncode==0,run.stderr.decode('utf-8')
    assert '→' in run.stdout.decode('utf-8')
    assert (tmp_path/'log').read_text()=='1\n'
