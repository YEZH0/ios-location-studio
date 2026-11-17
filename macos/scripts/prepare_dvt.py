"""Opt-in DVT preparation through Apple's devicectl and locally installed Xcode."""
import argparse
import asyncio
import json
import logging
import shutil
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.usbmux import list_devices


def summarize(result):
    # Never include deviceIdentifier, ECID, ticket or raw tool logs.
    try:
        data=json.loads(result.stdout)
        return {'event':'developer_image_preparation','exit_code':result.returncode,
                'ddi_metadata_available':bool(data.get('result',{}).get('ddiMetadata')),
                'error_code':data.get('error',{}).get('code')}
    except (ValueError,TypeError):
        return {'event':'developer_image_preparation','exit_code':result.returncode,
                'ddi_metadata_available':False}


async def prepare():
    devices=[d for d in await list_devices() if str(d.connection_type)=='USB']
    if len(devices)!=1: raise ValueError('RequireExactlyOneUSBDevice')
    if not shutil.which('xcrun'): raise ValueError('XcodeRequired')
    phone=await create_using_usbmux(connection_type='USB',autopair=False)
    try:
        serial=phone.identifier
        if not await phone.get_developer_mode_status():
            raise ValueError('DeveloperModeRequired')
    finally:
        await phone.close()
    proc=await asyncio.create_subprocess_exec('xcrun','devicectl','device','info','ddiServices',
        '--device',serial,'--auto-mount-ddis','--timeout','60','--json-output','-',
        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    try:
        stdout,stderr=await asyncio.wait_for(proc.communicate(),75)
    except BaseException:
        if proc.returncode is None:
            proc.terminate();await proc.wait()
        raise
    from types import SimpleNamespace
    report=summarize(SimpleNamespace(returncode=proc.returncode,stdout=stdout))
    print(json.dumps(report),flush=True)
    return proc.returncode

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--allow-apple-ticket',action='store_true',required=True,
        help='Consent to Apple developer image personalization using device identifiers')
    p.parse_args();logging.disable(logging.CRITICAL)
    try: raise SystemExit(asyncio.run(prepare()))
    except Exception as e:
        print(json.dumps({'event':'preparation_error','type':type(e).__name__}),flush=True)
        raise SystemExit(1)
