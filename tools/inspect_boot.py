#!/usr/bin/env python3
"""Inspect a supported legacy raw boot image without modifying it."""
import argparse
import json
from pathlib import Path
from bootlib import BootV0, require

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('image',type=Path); a=p.parse_args()
    require(a.image.stat().st_size<=128*1024*1024,'Input unexpectedly large')
    print(json.dumps(BootV0(a.image.read_bytes()).describe(),indent=2))

if __name__=='__main__':
    try: main()
    except (ValueError,OSError) as exc: raise SystemExit('REFUSED: '+str(exc))
