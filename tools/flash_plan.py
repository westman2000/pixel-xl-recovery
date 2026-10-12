#!/usr/bin/env python3
"""Validate files and a device already in fastboot, then PRINT commands. Never flashes or reboots."""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
from bootlib import digest, require

def getvar(exe,serial,key):
    r=subprocess.run([exe,'-s',serial,'getvar',key],capture_output=True,text=True,timeout=15)
    text=r.stdout+'\n'+r.stderr
    require(r.returncode==0,'fastboot getvar failed: '+text.strip())
    match=re.search(r'(?:^|\n)(?:\(bootloader\)\s*)?'+re.escape(key)+r':\s*([^\r\n]+)',text)
    require(match is not None,'Cannot parse fastboot variable '+key)
    return match.group(1).strip()

def validate_files(profile,source,image,rollback):
    require(digest(source)==profile['source_boot_sha256'],'Source backup is not the profiled build')
    candidate=digest(image)
    require(candidate in profile['expected_outputs'].values(),'Candidate is not a validated profile output')
    require(digest(rollback)==profile['expected_outputs']['rescue'],'Rollback is not the profiled rescue image')
    require(len(source)==len(image)==len(rollback)==profile['source_boot_bytes'],'Image size mismatch')
    return candidate

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['profile','source-backup','image','rollback']:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--serial',required=True);p.add_argument('--fastboot',default='fastboot')
    a=p.parse_args();profile=json.loads(a.profile.read_text())
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]*',a.serial) is not None,'Invalid device serial')
    sha=validate_files(profile,a.source_backup.read_bytes(),a.image.read_bytes(),a.rollback.read_bytes())
    product=getvar(a.fastboot,a.serial,'product');slot=getvar(a.fastboot,a.serial,'current-slot')
    require(product==profile['product']=='marlin','Wrong fastboot product')
    require(slot in ('a','b'),'Unknown active slot')
    require(getvar(a.fastboot,a.serial,'unlocked').lower()=='yes','Bootloader is not reported unlocked')
    size=int(getvar(a.fastboot,a.serial,'partition-size:boot_'+slot),0)
    require(size>=a.image.stat().st_size,'Candidate is larger than boot partition')
    base=[a.fastboot,'-s',a.serial]
    print(json.dumps({'mode':'PLAN ONLY','product':product,'slot':slot,'candidate_sha256':sha,'partition_bytes':size,'unverified_condition':'The supplied original backup must belong to the currently installed system/vendor build and this active slot. Fastboot variables cannot establish that.','commands':{'install':shlex.join(base+['flash','boot_'+slot,str(a.image.resolve())]),'reboot':shlex.join(base+['reboot']),'rollback':shlex.join(base+['flash','boot_'+slot,str(a.rollback.resolve())])}},indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.SubprocessError) as exc:raise SystemExit('REFUSED: '+str(exc))
