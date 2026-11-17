import math
import os
import sys
import time
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from location_studio_mac.engine import Engine, State, validate

@pytest.fixture(scope='session')
def app():
    return QApplication.instance() or QApplication([])

@pytest.mark.parametrize('args',[(math.nan,0,20),(0,math.inf,20),(91,0,20),(0,-181,20),(0,0,0),(0,0,3601)])
def test_invalid(args):
    with pytest.raises(ValueError): validate(*args)

def test_coordinates():
    assert validate('40.7128','-74.0060',180)==(40.7128,-74.006,180)

def test_ack_is_not_phone_verification():
    state=State()
    for event in ({'event':'identification_accepted'},{'event':'authentication_succeeded'},
                  {'event':'location_requested','sentences':[1,2]},
                  {'event':'location_link_acknowledged','count':50},
                  {'event':'finished','phone_location_verified':True}): state.consume(event)
    assert state.authenticated and state.subscribed and state.acks==50
    assert not state.map_verified and not state.restored
    state.consume({'event':'location_stopped'})
    assert not state.subscribed


def wait(app, predicate, seconds=8):
    end=time.monotonic()+seconds
    while time.monotonic()<end and not predicate():
        app.processEvents(); time.sleep(.01)
    assert predicate()


def test_worker_lifecycle_and_redaction(app,tmp_path):
    worker=tmp_path/'peer.py'
    worker.write_text('import json,time\nprint(json.dumps({"event":"authentication_succeeded"}),flush=True)\nprint(json.dumps({"event":"error","type":"Test","detail":"secret-device-id"}),flush=True)\ntime.sleep(60)\n')
    engine=Engine(); engine.command=lambda *args:[sys.executable,str(worker)]
    events=[]; engine.event.connect(events.append)
    engine.start('device')
    wait(app,lambda:any(x.get('event')=='error' for x in events))
    assert 'secret-device-id' not in str(events)
    with pytest.raises(ValueError): engine.start('device')
    engine.stop(); wait(app,lambda:not engine.running)
    assert any(x.get('event')=='process_exit' for x in events)


def test_gui_offline(app):
    from location_studio_mac.app import Window
    window=Window(); window.city.setCurrentText('东京 · Tokyo')
    assert float(window.lon.text())==139.6503
    assert not window.map_button.isEnabled()
    assert not window.restore.isEnabled()
    window.close()


def test_watchdog_cleans_authentication_child(app,tmp_path):
    pidfile=tmp_path/'child.pid'
    worker=tmp_path/'tree.py'
    worker.write_text('import subprocess,sys,time\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"])\nPath('+repr(str(pidfile))+').write_text(str(p.pid))\ntime.sleep(60)\n')
    engine=Engine();engine.command=lambda *args:[sys.executable,str(worker)]
    engine.start('device');wait(app,pidfile.exists)
    child=int(pidfile.read_text());engine.guard.start(20)
    wait(app,lambda:not engine.running)
    def gone():
        import subprocess
        result=subprocess.run(['ps','-p',str(child),'-o','stat='],capture_output=True,text=True)
        return result.returncode!=0 or result.stdout.strip().startswith('Z')
    wait(app,gone)
