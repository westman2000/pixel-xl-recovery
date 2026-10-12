"""Bounded command transport and private, durable experiment logging."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
from bootlib import require


class Device:
    def __init__(self, serial, adb='adb'):
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]*',serial) is not None,'Invalid explicit device serial')
        self.serial,self.adb=serial,adb

    def command(self, *args, timeout=15, check=True):
        r=subprocess.run([self.adb,'-s',self.serial,*args],capture_output=True,timeout=timeout)
        if check and r.returncode:
            raise RuntimeError(r.stderr.decode(errors='replace') or r.stdout.decode(errors='replace'))
        return r

    def shell(self, script, timeout=15):
        return self.command('shell',script,timeout=timeout).stdout.decode(errors='replace').strip()

    def require_marlin(self, root=False):
        product=self.shell('getprop ro.product.device')
        require(product=='marlin','Connected Android/recovery product is not marlin: '+repr(product))
        if root:
            require(self.shell('id -u')=='0','Root ADB shell required; this tool never enables root itself')
        return product

    def telemetry(self):
        script='''echo BOOT_ID=$(cat /proc/sys/kernel/random/boot_id)
echo UPTIME=$(cat /proc/uptime)
echo ONLINE=$(cat /sys/devices/system/cpu/online)
echo BATTERY_TEMP_TENTHS_C=$(cat /sys/class/power_supply/battery/temp)
echo THERMAL_ENGINE=$(getprop init.svc.vendor.thermal-engine)
echo CAPACITY=$(cat /sys/class/power_supply/battery/capacity)
for c in 0 1 2 3; do
 p=/sys/devices/system/cpu/cpu$c/cpufreq/scaling_cur_freq
 if [ -f "$p" ]; then echo FREQ$c=$(cat "$p"); fi
done
'''
        out=self.shell(script)
        data=dict(line.split('=',1) for line in out.splitlines() if '=' in line)
        require(bool(data.get('BOOT_ID')),'Missing boot identity')
        temp=int(data['BATTERY_TEMP_TENTHS_C'])
        require(-200<=temp<=1000,'Battery temperature units/value not supported; verify the sensor manually')
        return data


class Journal:
    def __init__(self, directory):
        self.path=Path(directory)
        self.path.mkdir(parents=True,exist_ok=False)
        (self.path/'PRIVATE.txt').write_text('Local diagnostic data may contain device identifiers. Do not publish this directory without manual review.\n')

    def event(self, kind, **fields):
        row=dict(utc=datetime.now(timezone.utc).isoformat(),event=kind,**fields)
        with (self.path/'journal.jsonl').open('a') as f:
            f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())

    def result(self, name, data):
        path=self.path/(name+'.json');temp=path.with_suffix('.tmp')
        with temp.open('w') as f:
            f.write(json.dumps(data,indent=2)+'\n');f.flush();os.fsync(f.fileno())
        temp.replace(path)


def cpus_from_list(text):
    cpus=set()
    for part in text.strip().split(','):
        if '-' in part:
            lo,hi=map(int,part.split('-'));require(0<=lo<=hi<=3,'Unexpected CPU range');cpus.update(range(lo,hi+1))
        else:
            value=int(part);require(0<=value<=3,'Unexpected CPU index');cpus.add(value)
    require(bool(cpus),'Empty CPU list')
    return cpus
