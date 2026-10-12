"""Strict offline readers and transformations for the documented legacy boot case.

Copyright 2026 Pixel XL Clock Recovery Kit contributors. MIT License.
No device access. No offset guessing. No support for AVB signing or modern headers.
"""
import hashlib
import struct
from dataclasses import dataclass


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def align(value, page):
    return (value + page - 1) // page * page


@dataclass
class BootV0:
    data: bytes

    def __post_init__(self):
        require(len(self.data) >= 1632, 'Truncated Android boot header')
        require(self.data[:8] == b'ANDROID!', 'Expected raw Android boot image; unpack ZIP/payload first')
        self.version = struct.unpack_from('<I', self.data, 40)[0]
        require(self.version == 0, 'Only legacy boot header version 0 is supported')
        self.page = struct.unpack_from('<I', self.data, 36)[0]
        require(2048 <= self.page <= 65536 and self.page & (self.page-1) == 0, 'Invalid page size')
        self.kernel_size = struct.unpack_from('<I', self.data, 8)[0]
        self.ramdisk_size = struct.unpack_from('<I', self.data, 16)[0]
        require(struct.unpack_from('<I', self.data, 24)[0] == 0, 'Second-stage payload is unsupported')
        require(self.kernel_size > 0 and self.ramdisk_size > 0, 'Empty kernel or ramdisk')
        self.ramdisk_offset = self.page + align(self.kernel_size, self.page)
        self.end = self.ramdisk_offset + align(self.ramdisk_size, self.page)
        require(self.end <= len(self.data), 'Payload extends beyond image')
        require(not any(self.data[self.end:]), 'Nonzero trailer: signed/AVB/unknown data; refusing to rewrite')
        require(not any(self.data[self.page+self.kernel_size:self.ramdisk_offset]), 'Nonzero kernel padding')
        require(not any(self.data[self.ramdisk_offset+self.ramdisk_size:self.end]), 'Nonzero ramdisk padding')
        self.cmdline = (self.data[64:576].split(b'\0')[0] + self.data[608:1632].split(b'\0')[0]).decode('ascii')

    @property
    def kernel(self):
        return self.data[self.page:self.page+self.kernel_size]

    @property
    def ramdisk(self):
        return self.data[self.ramdisk_offset:self.ramdisk_offset+self.ramdisk_size]

    def legacy_id(self, kernel=None):
        h = hashlib.sha1()
        for part in [self.kernel if kernel is None else kernel, self.ramdisk, b'']:
            h.update(part)
            h.update(struct.pack('<I', len(part)))
        return h.digest().ljust(32, b'\0')

    def describe(self):
        return dict(size_bytes=len(self.data), sha256=digest(self.data), header_version=0,
                    page_size=self.page, kernel_size=self.kernel_size, ramdisk_size=self.ramdisk_size,
                    ramdisk_offset=self.ramdisk_offset, cmdline=self.cmdline,
                    stored_legacy_id=self.data[576:608].hex(),
                    calculated_legacy_id=self.legacy_id().hex(),
                    legacy_id_matches=self.data[576:608] == self.legacy_id(),
                    kernel_sha256=digest(self.kernel), ramdisk_sha256=digest(self.ramdisk),
                    trailing_bytes=len(self.data)-self.end, trailing_bytes_all_zero=True)

    @staticmethod
    def set_cmdline(image, cmdline):
        encoded = cmdline.encode('ascii')
        require(len(encoded) < 512, 'This profile requires command line to fit the primary 512-byte field')
        image[64:576] = encoded.ljust(512, b'\0')
        image[608:1632] = b'\0'*1024

    def repack(self, kernel, cmdline):
        out = bytearray(len(self.data))
        out[:self.page] = self.data[:self.page]
        struct.pack_into('<I', out, 8, len(kernel))
        out[self.page:self.page+len(kernel)] = kernel
        new_offset = self.page + align(len(kernel), self.page)
        require(new_offset+align(self.ramdisk_size,self.page) <= len(out), 'Repacked image would exceed partition dump size')
        out[new_offset:new_offset+self.ramdisk_size] = self.ramdisk
        self.set_cmdline(out, cmdline)
        out[576:608] = self.legacy_id(kernel)
        result = bytes(out)
        require(len(result) == len(self.data), 'Unexpected image size change')
        check = BootV0(result)
        require(check.ramdisk == self.ramdisk and check.kernel == kernel, 'Payload validation failed')
        require(check.describe()['legacy_id_matches'], 'Legacy header checksum validation failed')
        return result


def fdt_properties(blob):
    """Return {(node_path, property): (length_field_offset, value_offset, bytes)}."""
    require(len(blob) >= 40, 'Truncated FDT header')
    magic,total,pos,strings,mem,version,compat,cpu,strsize,stsize = struct.unpack_from('>10I',blob)
    require(magic == 0xd00dfeed and total == len(blob) and version == 17, 'Unsupported FDT header')
    end = pos+stsize
    require(40 <= pos <= end <= total and strings+strsize <= total, 'FDT bounds are invalid')
    stack, result = [], {}
    while pos < end:
        require(pos+4 <= end, 'Truncated FDT token')
        token = struct.unpack_from('>I',blob,pos)[0]; pos += 4
        if token == 1:
            stop = blob.find(b'\0',pos,end)
            require(stop >= pos, 'Unterminated FDT node')
            stack.append(blob[pos:stop].decode('ascii')); pos = align(stop+1,4)
        elif token == 2:
            require(bool(stack), 'Unbalanced FDT node end'); stack.pop()
        elif token == 3:
            require(pos+8 <= end and bool(stack), 'Invalid FDT property')
            length_at = pos
            size,nameoff = struct.unpack_from('>II',blob,pos); pos += 8
            require(pos+size <= end and nameoff < strsize, 'FDT property bounds are invalid')
            stop = blob.find(b'\0',strings+nameoff,strings+strsize)
            require(stop >= strings+nameoff, 'Unterminated FDT property name')
            name = blob[strings+nameoff:stop].decode('ascii')
            key = ('/'.join(stack) or '/', name)
            require(key not in result, 'Duplicate FDT property')
            result[key] = (length_at,pos,blob[pos:pos+size]); pos = align(pos+size,4)
        elif token == 4:
            pass
        elif token == 9:
            require(not stack and pos == end, 'FDT structure did not end cleanly')
            return result
        else:
            raise ValueError('Unknown FDT token {}'.format(token))
    raise ValueError('Missing FDT_END')


def cap_fdt(blob, caps):
    """Shorten existing frequency/voltage pairs; preserve retained pairs and every other property."""
    before = fdt_properties(blob)
    out, touched, changes = bytearray(blob), set(), []
    for key,(length_at,value_at,value) in before.items():
        cluster = next((c for c in caps if key[1].startswith('qcom,'+c+'-speedbin')),None)
        if cluster is None:
            continue
        require(len(value)%8 == 0 and len(value)>0, 'Frequency table is not frequency/voltage pairs')
        pairs = list(struct.iter_unpack('>II',value))
        require(all(a[0] < b[0] for a,b in zip(pairs,pairs[1:])), 'Frequency table not strictly increasing')
        kept = [pair for pair in pairs if pair[0] <= caps[cluster]]
        require(len(kept)>=8 and kept == pairs[:len(kept)], 'Unexpected low-frequency table layout')
        new = b''.join(struct.pack('>II',*pair) for pair in kept)
        struct.pack_into('>I',out,length_at,len(new))
        out[value_at:value_at+len(value)] = new + struct.pack('>I',4)*((len(value)-len(new))//4)
        touched.add(key)
        changes.append(dict(node=key[0],property=key[1],old_max_hz=pairs[-1][0],new_max_hz=kept[-1][0],retained_pairs=len(kept)))
    require(len(touched)==3*len(caps),'Expected three speed-bin tables per cluster in every DTB')
    after=fdt_properties(bytes(out))
    require(before.keys()==after.keys(),'FDT property set changed')
    for key in before:
        if key not in touched:
            require(before[key][2]==after[key][2],'Unrelated FDT property changed')
    require(len(out)==len(blob),'DTB byte length changed')
    return bytes(out), changes


def critical_kernel_lines(text):
    # The word boundary is essential: "ramoops:" is not an "Oops:" event.
    pattern=re_compile_critical()
    return [line for line in text.splitlines() if pattern.search(line)]


def re_compile_critical():
    import re
    return re.compile(r'\b(?:Kernel panic|Oops:|BUG: unable|watchdog[^\n]*bite|Unhandled fault)',re.I)
