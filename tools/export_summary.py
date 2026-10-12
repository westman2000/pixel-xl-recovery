#!/usr/bin/env python3
"""Export a small allowlist of soak metrics, excluding raw logs, paths, serials and boot UUIDs."""
import argparse
import json
from pathlib import Path
from bootlib import require

def summary(r):
    require(r.get('schema')==1 and r.get('kind')=='soak','Unsupported private result format')
    require(type(r['passed']) is bool,'Invalid pass status')
    phases=[]
    for item in r['phases']:
        require(item['phase'] in ('hash','mixed'),'Unknown phase')
        phases.append({'phase':item['phase'],'correctness_checks':int(item['correctness_checks']),
                       'elapsed_seconds':float(item['elapsed_seconds']),
                       'iterations_by_core':{str(int(k)):int(v) for k,v in item['iterations_by_core'].items()}})
    # Deliberately do not export arbitrary device output or exception strings.
    return {'schema':1,'kind':'public-soak-summary','passed':r['passed'],'cores':[int(x) for x in r['cores']],
            'data_mib':int(r['data_mib']),'elapsed_seconds':float(r['elapsed_seconds']),
            'maximum_battery_c':max((int(x['BATTERY_TEMP_TENTHS_C'])/10 for x in r['samples']),default=None),
            'boot_continuity':r.get('boot_continuity') is True,'phases':phases,
            'scope':'One bounded software workload; not proof of hardware repair or long-term stability.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    require(not a.out.exists(),'Output already exists')
    result=summary(json.loads((a.run/'result.json').read_text()))
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(a.out)

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError) as exc:raise SystemExit('REFUSED: '+str(exc))
