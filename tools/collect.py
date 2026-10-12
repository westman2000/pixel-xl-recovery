#!/usr/bin/env python3
"""Read diagnostics from an explicitly selected Pixel XL. Output is private by default."""
import argparse
import json
import subprocess
from pathlib import Path
from bootlib import digest, require, critical_kernel_lines
from device import Device, Journal

SNAPSHOT='''id
for key in ro.product.device ro.product.model ro.build.version.release ro.lineage.version ro.boot.slot_suffix sys.boot_completed; do echo "$key=$(getprop $key)"; done
uname -a
echo CMDLINE; cat /proc/cmdline
echo UPTIME; cat /proc/uptime
echo PRESENT; cat /sys/devices/system/cpu/present
echo ONLINE; cat /sys/devices/system/cpu/online
for c in 0 1 2 3; do
 for f in cpuinfo_max_freq scaling_min_freq scaling_max_freq scaling_cur_freq scaling_available_frequencies; do
  p=/sys/devices/system/cpu/cpu$c/cpufreq/$f
  if [ -f "$p" ]; then echo "$p=$(cat $p)"; fi
 done
done
for f in use_alt_pll enable_acd; do p=/sys/module/clock_cpu_8996/parameters/$f; if [ -f "$p" ]; then echo "$p=$(cat $p)"; fi; done
for c in pwrcl perfcl; do
 for f in ${c}_hf_mux/parent ${c}_clk/rate; do p=/sys/kernel/debug/clk/$f; if [ -f "$p" ]; then echo "$p=$(cat $p)"; fi; done
done
echo BATTERY; cat /sys/class/power_supply/battery/uevent
echo BMS; cat /sys/class/power_supply/bms/uevent
echo THERMAL_SERVICE; getprop init.svc.vendor.thermal-engine
echo CPUSETS
for g in top-app foreground background system-background application system; do p=/dev/cpuset/$g/cpus; if [ -f "$p" ]; then echo "$p=$(cat $p)"; fi; done
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial',required=True);p.add_argument('--adb',default='adb');p.add_argument('--out',required=True,type=Path)
    p.add_argument('--include-pstore',action='store_true',help='Also read console-ramoops-0; may contain sensitive identifiers')
    p.add_argument('--backup-boot',action='store_true',help='Read and hash the currently active boot partition; requires root')
    a=p.parse_args();d=Device(a.serial,a.adb);d.require_marlin(root=a.backup_boot);j=Journal(a.out)
    j.event('collection_started',serial=a.serial,phone_writes=False)
    for name,command in [('snapshot',SNAPSHOT),('dmesg','dmesg')]:
        r=d.command('shell',command,check=False,timeout=30)
        text=r.stdout.decode(errors='replace')+r.stderr.decode(errors='replace')
        (a.out/(name+'.txt')).write_text(text);j.event('capture',name=name,returncode=r.returncode)
        if name=='dmesg' and r.returncode==0:
            j.result('kernel-log-summary',{'critical_candidates':critical_kernel_lines(text),'perfcl_lock_messages':sum('PLL perfcl_pll' in x and "didn't lock" in x for x in text.splitlines()),'note':'Candidates require context review; counts are only for the captured buffer.'})
    if a.include_pstore:
        r=d.command('exec-out','cat','/sys/fs/pstore/console-ramoops-0',check=False,timeout=30)
        if r.returncode==0:(a.out/'console-ramoops-0.txt').write_bytes(r.stdout)
        j.event('pstore_capture',returncode=r.returncode)
    if a.backup_boot:
        slot=d.shell('getprop ro.boot.slot_suffix').removeprefix('_')
        require(slot in ('a','b'),'Cannot establish active slot; refusing backup selection')
        part='/dev/block/by-name/boot_'+slot
        content=d.command('exec-out','cat',part,timeout=60).stdout
        require(0<len(content)<=128*1024*1024,'Unexpected boot partition size')
        remote=d.shell('sha256sum '+part).split()[0]
        require(digest(content)==remote,'Local backup does not match device hash')
        (a.out/'boot-original.img').write_bytes(content)
        j.result('backup',{'serial':a.serial,'product':'marlin','active_slot':slot,'sha256':remote,'bytes':len(content),'lineage_version':d.shell('getprop ro.lineage.version')})
        j.event('boot_backup_verified',slot=slot,sha256=remote)
    j.event('collection_finished')
    print('Private diagnostics saved to',a.out)

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as exc:raise SystemExit('STOPPED: '+str(exc))
