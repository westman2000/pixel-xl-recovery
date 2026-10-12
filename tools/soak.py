#!/usr/bin/env python3
"""Bounded, per-core correctness load. Does not flash, alter clocks, or disable thermal services."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import time
import uuid
from bootlib import critical_kernel_lines, require
from device import Device, Journal, cpus_from_list

WORKER='''#!/system/bin/sh
set -eu
dir=$1; core=$2; phase=$3; seconds=$4; expected256=$5; expected512=$6; limit=$7
data=$dir/data.bin; base=$dir/work-$core; pidfile=$dir/pid-$phase-$core
echo $$ > "$pidfile"
trap 'rm -f "$base.gz" "$base.raw" "$pidfile"' EXIT HUP INT TERM
read up rest < /proc/uptime
deadline=$(( ${up%%.*} + seconds )); n=0
while :; do
 read up rest < /proc/uptime
 [ "${up%%.*}" -lt "$deadline" ] || break
 [ ! -e "$dir/STOP" ] || exit 3
 temp=$(cat /sys/class/power_supply/battery/temp)
 [ "$temp" -lt "$limit" ] || { echo TEMPERATURE_STOP; exit 4; }
 if [ "$phase" = mixed ]; then
  gzip -1 -c "$data" > "$base.gz"
  gzip -dc "$base.gz" > "$base.raw"
  actual=$(sha256sum "$base.raw"); actual=${actual%% *}
  [ "$actual" = "$expected256" ] || { echo MISMATCH-gzip; exit 5; }
 fi
 actual=$(sha256sum "$data"); actual=${actual%% *}
 [ "$actual" = "$expected256" ] || { echo MISMATCH-sha256; exit 6; }
 actual=$(sha512sum "$data"); actual=${actual%% *}
 [ "$actual" = "$expected512" ] || { echo MISMATCH-sha512; exit 7; }
 n=$((n+1)); echo PASS core=$core phase=$phase iteration=$n
done
echo COMPLETE core=$core phase=$phase iterations=$n
'''


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial',required=True);p.add_argument('--adb',default='adb');p.add_argument('--out',required=True,type=Path)
    p.add_argument('--expected-boot-sha256',required=True)
    p.add_argument('--cores',default='0,1',help='Explicit CPU list, for example 0,1,2,3')
    p.add_argument('--seconds-per-phase',type=int,default=30)
    p.add_argument('--data-mib',type=int,default=32,choices=[8,16,32,64])
    p.add_argument('--battery-stop-c',type=float,default=40.0)
    p.add_argument('--max-freq0-khz',type=int);p.add_argument('--max-freq2-khz',type=int)
    return p


def main():
    a=parser().parse_args();cores=sorted(cpus_from_list(a.cores))
    require(re.fullmatch('[0-9a-f]{64}',a.expected_boot_sha256) is not None,'Expected a lowercase SHA256')
    require(5<=a.seconds_per_phase<=900,'Use 5 to 900 seconds per phase')
    require(30<=a.battery_stop_c<=40,'Battery cutoff may be lowered; maximum supported cutoff is 40 C')
    d=Device(a.serial,a.adb);d.require_marlin(root=True)
    slot=d.shell('getprop ro.boot.slot_suffix').removeprefix('_');require(slot in ('a','b'),'Unknown active slot')
    actual=d.shell('sha256sum /dev/block/by-name/boot_'+slot).split()[0]
    require(actual==a.expected_boot_sha256,'Installed boot hash differs from requested test configuration')
    initial=d.telemetry();require(set(cores)<=cpus_from_list(initial['ONLINE']),'Requested CPU is offline/not present')
    require(initial['THERMAL_ENGINE']=='running','Expected vendor.thermal-engine running; inspect ROM configuration instead of disabling this check')
    limit=int(a.battery_stop_c*10);require(int(initial['BATTERY_TEMP_TENTHS_C'])<limit,'Battery already at cutoff; let it cool')
    commands=d.shell('command -v taskset sha256sum sha512sum gzip timeout').splitlines()
    require(len(commands)==5,'Required taskset/hash/gzip/timeout utilities are missing')
    j=Journal(a.out);j.event('soak_started',serial=a.serial,cores=cores,seconds_per_phase=a.seconds_per_phase,boot_sha256=actual)
    result={'schema':1,'kind':'soak','passed':False,'boot_sha256':actual,'cores':cores,'data_mib':a.data_mib,'initial':initial,'samples':[],'phases':[]}
    half=a.data_mib*1024*1024//2
    data=random.Random(8996).randbytes(half)+bytes(range(256))*(half//256)
    h256=hashlib.sha256(data).hexdigest();h512=hashlib.sha512(data).hexdigest()
    result.update(data_sha256=h256,data_sha512=h512)
    local=a.out/'data.bin';local.write_bytes(data);script=a.out/'worker.sh';script.write_text(WORKER)
    remote='/dev/pixel-lab-'+uuid.uuid4().hex[:12]
    processes=[];handles=[];stream=None;stream_file=None;start=time.monotonic()
    try:
        d.shell('mkdir -m 700 '+remote)
        d.command('push',str(local),remote+'/data.bin',timeout=30)
        d.command('push',str(script),remote+'/worker.sh')
        require(d.shell('sha256sum '+remote+'/data.bin').split()[0]==h256,'Test data transfer mismatch')
        initial_log=d.shell('dmesg',timeout=30)
        (a.out/'initial-dmesg.txt').write_text(initial_log)
        require(not critical_kernel_lines(initial_log),'Existing critical kernel messages require review before starting load')
        pll_before=sum('PLL ' in x and "didn't lock" in x for x in initial_log.splitlines())
        stream_file=(a.out/'live-dmesg.txt').open('wb',buffering=0)
        stream=subprocess.Popen([a.adb,'-s',a.serial,'shell','dmesg -w'],stdout=stream_file,stderr=subprocess.STDOUT)
        for phase in ['hash','mixed']:
            processes=[];handles=[];phase_start=time.monotonic();j.event('phase_started',phase=phase)
            for core in cores:
                handle=(a.out/(phase+'-cpu'+str(core)+'.txt')).open('wb',buffering=0);handles.append(handle)
                cmd=f'timeout {a.seconds_per_phase+30} taskset {1<<core:x} sh {remote}/worker.sh {remote} {core} {phase} {a.seconds_per_phase} {h256} {h512} {limit}'
                processes.append(subprocess.Popen([a.adb,'-s',a.serial,'shell',cmd],stdout=handle,stderr=subprocess.STDOUT))
            while True:
                sample=d.telemetry();sample.update(phase=phase,elapsed_seconds=round(time.monotonic()-start,2))
                result['samples'].append(sample);j.event('sample',**sample)
                require(sample['BOOT_ID']==initial['BOOT_ID'],'Device rebooted during load')
                require(set(cores)<=cpus_from_list(sample['ONLINE']),'A tested CPU went offline')
                require(sample['THERMAL_ENGINE']=='running','Thermal service stopped')
                require(int(sample['BATTERY_TEMP_TENTHS_C'])<limit,'Conservative battery temperature stop; this alone does not prove a CPU fault')
                for core,cap in [(0,a.max_freq0_khz),(2,a.max_freq2_khz)]:
                    if cap is not None:require(int(sample['FREQ'+str(core)])<=cap,'Observed frequency exceeds requested cap')
                require(stream.poll() is None,'Live kernel-log capture stopped unexpectedly')
                require(all(p.poll() in (None,0) for p in processes),'A correctness worker failed; inspect its private log')
                print(json.dumps({k:sample[k] for k in ['elapsed_seconds','phase','ONLINE','BATTERY_TEMP_TENTHS_C']}),flush=True)
                if all(p.poll()==0 for p in processes):break
                require(time.monotonic()-phase_start<a.seconds_per_phase+45,'Host watchdog expired')
                time.sleep(3)
            counts={}
            for core in cores:
                text=(a.out/(phase+'-cpu'+str(core)+'.txt')).read_text()
                require(f'COMPLETE core={core} phase={phase} ' in text and 'MISMATCH' not in text,'Worker did not finish correctly')
                counts[str(core)]=text.count('PASS core=')
                require(counts[str(core)]>0,'No checks completed on a requested core')
            record={'phase':phase,'elapsed_seconds':round(time.monotonic()-phase_start,2),'iterations_by_core':counts,'correctness_checks':sum(counts.values())*(3 if phase=='mixed' else 2)}
            result['phases'].append(record);j.event('phase_passed',**record)
            for f in handles:f.close()
            handles=[]
        final=d.telemetry();require(final['BOOT_ID']==initial['BOOT_ID'],'Unexpected reboot at end of test')
        final_log=d.shell('dmesg',timeout=30);(a.out/'final-dmesg.txt').write_text(final_log)
        live=(a.out/'live-dmesg.txt').read_text(errors='replace')
        require(not critical_kernel_lines(live+final_log),'Critical kernel message needs review')
        # dmesg -w begins by printing the existing buffer on the tested toybox.
        # Independently inspect timestamps so a ring-buffer turnover cannot hide new failures.
        started_uptime=float(initial['UPTIME'].split()[0])
        new_pll=[]
        for line in live.splitlines():
            if 'PLL ' in line and "didn't lock" in line:
                timestamp=re.search(r'\[\s*([0-9.]+)\]',line)
                if not timestamp or float(timestamp.group(1))>=started_uptime:new_pll.append(line)
        require(not new_pll,'New PLL lock failure during test')
        result.update(passed=True,final=final,boot_continuity=True,new_pll_lock_messages=0,initial_pll_lock_messages=pll_before)
        j.event('soak_passed',checks=sum(x['correctness_checks'] for x in result['phases']))
    except BaseException as exc:
        result['error']=str(exc) or type(exc).__name__;j.event('soak_stopped',error=result['error'])
        raise
    finally:
        result['elapsed_seconds']=round(time.monotonic()-start,2)
        try:d.shell('touch '+remote+'/STOP',timeout=4)
        except Exception:pass
        # Give workers a chance to finish the current bounded operation and observe STOP.
        deadline=time.monotonic()+8
        while any(p.poll() is None for p in processes) and time.monotonic()<deadline:time.sleep(0.2)
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=2)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
        if stream is not None:
            stream.terminate()
            try:stream.wait(timeout=2)
            except subprocess.TimeoutExpired:stream.kill();stream.wait()
        for f in handles:f.close()
        if stream_file is not None:stream_file.close()
        try:
            d.shell('rm -rf '+remote,timeout=5)
            result['device_temporary_files_removed']=True
        except Exception:
            result['device_temporary_files_removed']=False
            result['cleanup_path']=remote
        local.unlink(missing_ok=True)
        j.result('result',result)
    print('PASS:',sum(x['correctness_checks'] for x in result['phases']),'verified checks; private results:',a.out)

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as exc:raise SystemExit('STOPPED: '+str(exc))
