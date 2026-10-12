#!/usr/bin/env python3
"""Reproduce the two supported case-study images offline. Never invokes ADB or fastboot."""
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from bootlib import BootV0, cap_fdt, digest, require


def build(source, profile, variant, lz4='lz4'):
    require(digest(source)==profile['source_boot_sha256'],'Input SHA256 is not supported by this profile. Do not transplant its offsets.')
    require(len(source)==profile['source_boot_bytes'],'Input size mismatch')
    boot=BootV0(source)
    require(boot.page==profile['page_size'],'Page size mismatch')
    layout=profile['layout']
    require(boot.kernel_size==layout['kernel_size'] and boot.ramdisk_size==layout['ramdisk_size'],'Payload layout mismatch')
    require('androidboot.hardware=marlin' in boot.cmdline.split(),'Profile requires marlin hardware command line')
    require(not source[608:1632].strip(b'\0'),'Profile expects an empty extra command line')
    cmd=boot.cmdline
    require(not any(x.startswith(('nr_cpus=','maxcpus=','clock_cpu_8996.')) for x in cmd.split()),'Input already contains experiment options')
    details={'variant':variant,'source_sha256':digest(source),'profile_id':profile['id'],'ramdisk_sha256':digest(boot.ramdisk)}
    if variant=='rescue':
        out=bytearray(source)
        BootV0.set_cmdline(out,cmd+' nr_cpus=2 maxcpus=2')
        result=bytes(out)
        require(result[boot.page:]==source[boot.page:],'Rescue altered payload')
        details['change']='Header command line only; original header ID and all payloads preserved'
    else:
        require(variant=='stable','Unknown variant')
        exe=shutil.which(lz4)
        require(exe is not None,'LZ4 CLI is required for stable builds; tested version is 1.10.0')
        version=subprocess.check_output([exe,'--version'],text=True,stderr=subprocess.STDOUT).strip()
        details['lz4_version']=version
        frame_end=layout['dtbs'][0][0]
        frame=boot.kernel[:frame_end]
        require(frame[:7].hex()==profile['lz4_frame_header_hex'],'Unexpected source LZ4 frame header')
        with tempfile.TemporaryDirectory(prefix='pixel-boot-build-') as td:
            td=Path(td); compressed=td/'source.lz4'; rawfile=td/'Image'; patched=td/'Image.patched'; encoded=td/'patched.lz4'; roundtrip=td/'roundtrip'
            compressed.write_bytes(frame)
            subprocess.run([exe,'-d','-f',str(compressed),str(rawfile)],check=True,capture_output=True)
            raw=rawfile.read_bytes()
            require(len(raw)==profile['raw_kernel_bytes'] and digest(raw)==profile['raw_kernel_sha256'],'Uncompressed kernel does not match profile')
            require(raw[56:60]==b'ARM\x64','Expected ARM64 Image magic')
            changed=bytearray(raw)
            for patch in profile['kernel_data_patches']:
                offset=patch['field_offset']
                require(offset==patch['symbol_image_offset']+32,'Unexpected alpha_pll_clk field offset')
                require(struct.unpack_from('<III',raw,offset-4)==(9,256,0x4001051b),'Kernel data structure fingerprint mismatch')
                struct.pack_into('<I',changed,offset,patch['new'])
            require(sum(a!=b for a,b in zip(raw,changed))==2,'Expected exactly two changed kernel data bytes')
            require(digest(changed)==profile['patched_raw_kernel_sha256'],'Patched raw kernel hash mismatch')
            patched.write_bytes(changed)
            subprocess.run([exe,'-12','-B7','-f',str(patched),str(encoded)],check=True,capture_output=True)
            subprocess.run([exe,'-d','-f',str(encoded),str(roundtrip)],check=True,capture_output=True)
            require(roundtrip.read_bytes()==changed,'LZ4 roundtrip mismatch')
            newframe=encoded.read_bytes()
            require(newframe[:7]==frame[:7],'LZ4 frame options changed')
        tail=bytearray(boot.kernel[frame_end:]); changes=[]; next_offset=frame_end
        for index,(offset,size) in enumerate(layout['dtbs']):
            require(offset==next_offset,'Appended DTB sequence has gaps or overlaps')
            blob=boot.kernel[offset:offset+size]
            new,delta=cap_fdt(blob,profile['caps_hz'])
            tail[offset-frame_end:offset-frame_end+size]=new
            changes.extend(dict(dtb_index=index,**row) for row in delta)
            next_offset=offset+size
        require(next_offset==len(boot.kernel),'Unexplained data after final DTB')
        require(len(changes)==120,'Expected 120 frequency tables across 20 DTBs')
        kernel=newframe+bytes(tail)
        cmd+=' nr_cpus=4 maxcpus=4 clock_cpu_8996.use_alt_pll=1 clock_cpu_8996.enable_acd=0'
        result=boot.repack(kernel,cmd)
        details.update(change='Two kernel data bytes, clock options and both cluster DT frequency caps',dtb_changes=changes,raw_kernel_sha256=digest(changed),compressed_kernel_bytes=len(newframe),legacy_header_id_recomputed=True)
    expected=profile['expected_outputs'][variant]
    require(digest(result)==expected,'Output differs from the validated case image. Check profile/tool version; no output will be written.')
    details.update(output_sha256=digest(result),expected_output_sha256=expected,size_bytes=len(result),boot=BootV0(result).describe(),status='Offline reconstruction validated; no phone accessed')
    return result,details


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boot',required=True,type=Path)
    parser.add_argument('--profile',required=True,type=Path)
    parser.add_argument('--variant',required=True,choices=['rescue','stable'])
    parser.add_argument('--out',required=True,type=Path,help='New directory; existing directories are refused')
    parser.add_argument('--lz4',default='lz4')
    args=parser.parse_args()
    require(not args.out.exists(),'Output directory exists; choose a new one')
    require(args.boot.stat().st_size<=128*1024*1024,'Input unexpectedly large')
    image,manifest=build(args.boot.read_bytes(),json.loads(args.profile.read_text()),args.variant,args.lz4)
    args.out.mkdir(parents=True)
    name='boot-'+args.variant+'.img'
    (args.out/name).write_bytes(image)
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'image':str(args.out/name),'sha256':digest(image),'status':manifest['status']},indent=2))


if __name__=='__main__':
    try: main()
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        raise SystemExit('REFUSED: '+str(exc))
