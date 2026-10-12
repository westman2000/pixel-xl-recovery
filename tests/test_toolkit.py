"""Host tests. Device transport is simulated; these are not hardware soak results."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from bootlib import BootV0, cap_fdt, critical_kernel_lines, digest, fdt_properties
from build_boot import build
from device import Device, cpus_from_list
from export_summary import summary
from flash_plan import getvar, validate_files
import soak


def synthetic_boot():
    out=bytearray(16384);out[:8]=b'ANDROID!'
    for offset,value in [(8,100),(16,100),(36,4096)]:struct.pack_into('<I',out,offset,value)
    out[4096:4196]=b'K'*100;out[8192:8292]=b'R'*100
    BootV0.set_cmdline(out,'androidboot.hardware=marlin console=test')
    return bytes(out)


def synthetic_fdt():
    names=['model']+['qcom,perfcl-speedbin%d-v0'%x for x in range(3)]
    strings=b''; offsets={}
    for name in names:offsets[name]=len(strings);strings+=name.encode()+b'\0'
    def node(name):
        text=name.encode()+b'\0';return struct.pack('>I',1)+text.ljust((len(text)+3)//4*4,b'\0')
    def prop(name,value):return struct.pack('>III',3,len(value),offsets[name])+value.ljust((len(value)+3)//4*4,b'\0')
    body=node('')+prop('model',b'synthetic\0')+node('soc')+node('clock@0')
    for name in names[1:]:body+=prop(name,b''.join(struct.pack('>II',100000000*i,i+3) for i in range(1,13)))
    body+=struct.pack('>IIII',2,2,2,9)
    start=56;total=start+len(body)+len(strings)
    return struct.pack('>10I',0xd00dfeed,total,start,start+len(body),40,17,16,0,len(strings),len(body))+b'\0'*16+body+strings


class BootTests(unittest.TestCase):
    def test_sections(self):
        boot=BootV0(synthetic_boot());self.assertEqual(boot.kernel,b'K'*100);self.assertEqual(boot.ramdisk,b'R'*100)
    def test_modern_header_refused(self):
        b=bytearray(synthetic_boot());struct.pack_into('<I',b,40,4)
        with self.assertRaises(ValueError):BootV0(bytes(b))
    def test_nonzero_trailer_refused(self):
        b=bytearray(synthetic_boot());b[-4:]=b'AVBf'
        with self.assertRaises(ValueError):BootV0(bytes(b))
    def test_truncated_payload_refused(self):
        with self.assertRaises(ValueError):BootV0(synthetic_boot()[:7000])
    def test_invalid_page_refused(self):
        b=bytearray(synthetic_boot());struct.pack_into('<I',b,36,3000)
        with self.assertRaises(ValueError):BootV0(bytes(b))
    def test_repack_preserves_ramdisk_and_updates_id(self):
        b=BootV0(synthetic_boot());new=BootV0(b.repack(b'NEW'*2100,b.cmdline+' nr_cpus=4'))
        self.assertEqual(new.ramdisk,b.ramdisk);self.assertTrue(new.describe()['legacy_id_matches']);self.assertEqual(len(new.data),len(b.data))
    def test_repack_overflow_refused(self):
        b=BootV0(synthetic_boot())
        with self.assertRaises(ValueError):b.repack(b'x'*20000,b.cmdline)
    def test_input_hash_gate(self):
        with self.assertRaisesRegex(ValueError,'SHA256'):build(b'bad',{'source_boot_sha256':'0'*64},'stable')
    def test_rescue_payload_invariant(self):
        source=synthetic_boot();b=bytearray(source);BootV0.set_cmdline(b,BootV0(source).cmdline+' nr_cpus=2 maxcpus=2')
        profile={'id':'synthetic','source_boot_sha256':digest(source),'source_boot_bytes':len(source),'page_size':4096,'layout':{'kernel_size':100,'ramdisk_size':100},'expected_outputs':{'rescue':digest(b)}}
        out,manifest=build(source,profile,'rescue');self.assertEqual(out[4096:],source[4096:]);self.assertEqual(digest(out),digest(b))


class FdtTests(unittest.TestCase):
    def test_cap_preserves_unrelated_properties_and_corners(self):
        b=synthetic_fdt();out,changes=cap_fdt(b,{'perfcl':800000000})
        before=fdt_properties(b);after=fdt_properties(out)
        self.assertEqual(len(b),len(out));self.assertEqual(len(changes),3)
        for key in before:
            expected=before[key][2][:8*8] if 'speedbin' in key[1] else before[key][2]
            self.assertEqual(after[key][2],expected)
    def test_too_low_cap_refused(self):
        with self.assertRaises(ValueError):cap_fdt(synthetic_fdt(),{'perfcl':100000000})
    def test_bad_fdt_size_refused(self):
        with self.assertRaises(ValueError):fdt_properties(synthetic_fdt()[:-1])
    def test_missing_cluster_refused(self):
        with self.assertRaises(ValueError):cap_fdt(synthetic_fdt(),{'pwrcl':800000000})


class LogAndInputTests(unittest.TestCase):
    def test_ramoops_is_not_oops(self):self.assertEqual(critical_kernel_lines('[1.2] ramoops: attached'),[])
    def test_real_oops_detected(self):self.assertEqual(len(critical_kernel_lines('[3.0] Internal error: Oops: 96000004')),1)
    def test_panic_detected(self):self.assertTrue(critical_kernel_lines('[3.1] Kernel panic - not syncing'))
    def test_cpu_lists(self):self.assertEqual(cpus_from_list('0-3'),{0,1,2,3});self.assertEqual(cpus_from_list('0,2'),{0,2})
    def test_bad_cpu_refused(self):
        with self.assertRaises(ValueError):cpus_from_list('0-7')
    def test_serial_injection_refused(self):
        with self.assertRaises(ValueError):Device('phone; rm -rf /')
    def test_export_excludes_identifiers(self):
        r={'schema':1,'kind':'soak','passed':True,'cores':[0,1],'data_mib':8,'elapsed_seconds':5,'samples':[{'BATTERY_TEMP_TENTHS_C':'370','BOOT_ID':'PRIVATE_UUID'}],'phases':[{'phase':'hash','correctness_checks':2,'elapsed_seconds':5,'iterations_by_core':{'0':1},'secret':'PRIVATE_PATH'}],'serial':'PRIVATE_SERIAL','initial':{'secret':'PRIVATE_USERNAME'}}
        text=json.dumps(summary(r));self.assertNotIn('PRIVATE',text);self.assertNotIn('serial',text)
    def test_flash_file_gate(self):
        profile={'source_boot_sha256':digest(b'aaaa'),'expected_outputs':{'rescue':digest(b'bbbb'),'stable':digest(b'cccc')},'source_boot_bytes':4}
        self.assertEqual(validate_files(profile,b'aaaa',b'cccc',b'bbbb'),digest(b'cccc'))
        with self.assertRaises(ValueError):validate_files(profile,b'xxxx',b'cccc',b'bbbb')
        with self.assertRaises(ValueError):validate_files(profile,b'aaaa',b'xxxx',b'bbbb')
    def test_fastboot_stderr(self):
        from types import SimpleNamespace
        with patch('flash_plan.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='',stderr='(bootloader) current-slot: a\nFinished.')):
            self.assertEqual(getvar('fastboot','TEST','current-slot'),'a')


class SoakOrchestrationTests(unittest.TestCase):
    def scenario(self,mode):
        class FakeDevice:
            calls=0;data_hash='';cleaned=False
            def __init__(self,*args):pass
            def require_marlin(self,root=False):return 'marlin'
            def command(self,*args,**kwargs):
                if args[0]=='push' and args[-1].endswith('data.bin'):self.data_hash=digest(Path(args[1]).read_bytes())
            def shell(self,cmd,**kwargs):
                if cmd.startswith('getprop ro.boot.slot_suffix'):return '_a'
                if cmd.startswith('sha256sum /dev/block'):return 'a'*64+'  boot_a'
                if cmd.startswith('sha256sum /dev/pixel'):return self.data_hash+'  data.bin'
                if cmd=='dmesg':return '[ 1.0] ramoops: attached\n'
                if cmd.startswith('command -v'):return '\n'.join('/system/bin/'+x for x in ['taskset','sha256sum','sha512sum','gzip','timeout'])
                if cmd.startswith('rm -rf'):FakeDevice.cleaned=True
                return ''
            def telemetry(self):
                self.calls+=1
                return {'BOOT_ID':'changed' if mode=='reboot' and self.calls>1 else 'same','UPTIME':'100.0 20.0','ONLINE':'0-3','BATTERY_TEMP_TENTHS_C':'405' if mode=='hot' and self.calls>1 else '370','THERMAL_ENGINE':'running','CAPACITY':'80','FREQ0':'1593600','FREQ2':'902400'}
        class FakeProcess:
            def __init__(self,args,stdout,stderr):
                self.stream=args[-1]=='dmesg -w';self.returncode=None if self.stream else (6 if mode=='mismatch' else 0)
                if self.stream:stdout.write(b'[ 1.0] ramoops: attached\n')
                else:
                    parts=args[-1].split();idx=parts.index('sh');core,phase=parts[idx+3:idx+5]
                    stdout.write(f'PASS core={core} phase={phase} iteration=1\nCOMPLETE core={core} phase={phase} iterations=1\n'.encode())
            def poll(self):return self.returncode
            def terminate(self):self.returncode=-15
            def kill(self):self.returncode=-9
            def wait(self,timeout=None):return self.returncode
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            argv=['soak.py','--serial','TEST','--out',str(out),'--expected-boot-sha256','a'*64,'--data-mib','8','--seconds-per-phase','5']
            with patch.object(sys,'argv',argv),patch.object(soak,'Device',FakeDevice),patch.object(soak.subprocess,'Popen',FakeProcess),contextlib.redirect_stdout(io.StringIO()):
                if mode=='success':soak.main()
                else:
                    with self.assertRaises(ValueError):soak.main()
            result=json.loads((out/'result.json').read_text());self.assertEqual(result['passed'],mode=='success');self.assertTrue(FakeDevice.cleaned)
            self.assertFalse((out/'data.bin').exists())
            if mode=='success':self.assertEqual(sum(x['correctness_checks'] for x in result['phases']),10)
    def test_success(self):self.scenario('success')
    def test_temperature_stop(self):self.scenario('hot')
    def test_unexpected_reboot_stop(self):self.scenario('reboot')
    def test_worker_error_stop(self):self.scenario('mismatch')


@unittest.skipUnless(os.environ.get('PIXEL_ORIGINAL_BOOT'),'Set PIXEL_ORIGINAL_BOOT for byte-for-byte reconstruction checks')
class RealInputTests(unittest.TestCase):
    def test_exact_profile_outputs(self):
        source=Path(os.environ['PIXEL_ORIGINAL_BOOT']).read_bytes();profile=json.loads((ROOT/'profiles/marlin-lineage22-case1.json').read_text())
        for variant in ['rescue','stable']:
            out,manifest=build(source,profile,variant);self.assertEqual(digest(out),profile['expected_outputs'][variant])
        bad=bytearray(source);bad[5000]^=1
        with self.assertRaises(ValueError):build(bytes(bad),profile,'stable')

if __name__=='__main__':unittest.main()
