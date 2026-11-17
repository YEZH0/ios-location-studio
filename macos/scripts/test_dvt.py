"""Opt-in DVT location experiment. Requires an already mounted developer image."""
import argparse
import asyncio
import json
import logging
import signal
from pymobiledevice3.usbmux import list_devices
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.remote.userspace_tunnel import UserspaceRsdTunnel
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
from location_studio_mac.engine import validate

def emit(event,**fields): print(json.dumps({'event':event,**fields}),flush=True)

async def experiment(args):
    devices=[d for d in await list_devices() if str(d.connection_type)=='USB']
    if len(devices)!=1: raise ValueError('RequireExactlyOneUSBDevice')
    phone=await create_using_usbmux(connection_type='USB',autopair=False)
    serial=phone.identifier
    await phone.close()
    stop=asyncio.Event();loop=asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM): loop.add_signal_handler(sig,stop.set)
    async with UserspaceRsdTunnel(serial=serial,autopair=False) as rsd:
        emit('dvt_tunnel_connected')
        async with DvtProvider(rsd) as dvt:
            async with LocationSimulation(dvt) as simulation:
                try:
                    await simulation.set(args.latitude,args.longitude)
                    emit('dvt_set_sent',phone_location_verified=False)
                    try: await asyncio.wait_for(stop.wait(),args.duration)
                    except TimeoutError: pass
                finally:
                    try:
                        await asyncio.wait_for(simulation.clear(),10)
                        emit('dvt_clear_sent',phone_restoration_verified=False)
                    except Exception as e:
                        emit('dvt_clear_error',type=type(e).__name__)
    emit('dvt_session_closed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--latitude',type=float,required=True)
    parser.add_argument('--longitude',type=float,required=True)
    parser.add_argument('--duration',type=int,required=True)
    args=parser.parse_args()
    validate(args.latitude,args.longitude,args.duration)
    if args.duration>180: parser.error('实验会话最长 180 秒')
    logging.disable(logging.CRITICAL)
    try: asyncio.run(asyncio.wait_for(experiment(args),args.duration+60))
    except Exception as e:
        emit('dvt_error',type=type(e).__name__)
        raise SystemExit(1)
