"""Independent deterministic supervisor CLI; never imports the engine/model."""
import argparse
import asyncio
import json
from pathlib import Path
from . import Guardian
from .service import atomic
from ..config import ROOT
from ..development.worker_runner import health


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['activate','recover','status'])
    parser.add_argument('--release')
    parser.add_argument('--result')
    args=parser.parse_args();g=Guardian(ROOT)
    try:
        if args.action=='activate':result=asyncio.run(g.activate(args.release,health))
        elif args.action=='recover':result=asyncio.run(g.recover(health))
        else:result=g.status()
    except Exception as exc:result={'state':'failed','error':type(exc).__name__+': '+str(exc)[:1000],'recovery_required':True}
    if args.result:
        output=Path(args.result).resolve()
        if output.parent!=g.control:raise ValueError('Result must remain in guardian control directory')
        atomic(output,result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
