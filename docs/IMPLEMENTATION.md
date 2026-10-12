# Boot image implementation

## Two outputs from one original

The public builder reproduces the rescue and retained four-core images directly from the unmodified original. It does not reproduce every intermediate experiment. Intermediate hashes remain in the evidence ledger so a reader can distinguish which result belongs to which image.

The two supported variants are:

- `rescue`: append `nr_cpus=2 maxcpus=2`; preserve all payload bytes and the original legacy header ID.
- `stable`: patch the two alternate-PLL divider fields, cap both cluster frequency tables, add the four-core alternate-PLL options, recompress and repack, and recompute the legacy header ID.

The builder checks the complete input hash before interpreting the profile's raw kernel offsets. It then checks the decompressed kernel hash, field-adjacent constants, number of changed bytes, patched raw hash, compression roundtrip, device-tree structure, unrelated properties, ramdisk identity, and complete output hash. The output hash is the final gate before writing the candidate file.

## Observed legacy layout

| Field | Original image | Retained image |
| --- | ---: | ---: |
| Total image bytes | 33,554,432 | 33,554,432 |
| Header version | 0 | 0 |
| Page size | 4,096 | 4,096 |
| Kernel payload bytes | 21,889,992 | 21,845,692 |
| Ramdisk bytes | 9,274,872 | 9,274,872 |
| Ramdisk offset | 21,897,216 | 21,852,160 |
| Appended DTB count | 20 | 20 |
| Second-stage payload | Empty | Empty |

The kernel-size field includes the compressed kernel frame and the appended DTBs. The ramdisk starts after page-aligning that combined payload. The remaining partition-dump trailer was all zeros. This observation allowed the case-specific repack; it is not a license to discard nonzero trailers in other images.

The reader rejects other header versions, unsupported second-stage payloads, nonzero padding, nonzero trailers, invalid sizes, and out-of-bounds data. It is not an AVB or boot-signature tool. The [AOSP boot-image header reference](https://source.android.com/docs/core/architecture/bootloader/boot-image-header) is the format reference; this implementation intentionally handles only a subset.

## Command line and legacy ID

The original primary command-line field contained the board and boot-device arguments and `lpm_levels.sleep_disabled=1`. Its extra command-line field was empty. The toolkit preserves the existing primary arguments, requires the added text to fit the primary 512-byte field, and retains an empty extra field.

The original stored legacy ID did not equal the SHA-1 recomputed from its payloads. The investigation did not determine why. The rescue output preserves it exactly because only the command line changed and the successful rescue image is the reference result.

For the stable repack, the SHA-1 input consists of kernel bytes plus their little-endian length, ramdisk bytes plus their length, and the empty second-stage payload plus its zero length. The digest is stored with the remaining ID bytes padded with zero. Recomputing this legacy field is not signing the image and does not make it acceptable to a locked verified-boot chain.

## Kernel decompression and offset validation

The original LZ4 frame occupied 13,470,216 bytes at the start of the kernel payload. Its first seven bytes were:

```text
04 22 4d 18 64 70 b9
```

Decompression produced a 29,104,160-byte ARM64 Image. The public profile records these hashes:

```text
Original raw kernel
b604388da1159bfe628c7456d19f30eec1f977acd517a56e1193965c34c718b9

Patched raw kernel
060e28dee64a273399c292770efdb4bf7c0517d0af98eb112a64df8b2e84a44f
```

Live symbols observed during the private experiment located the two alternate-PLL structures relative to `_text`. The offsets below apply only to that validated Image:

| Structure | Structure offset | Field offset | Old value | New value |
| --- | ---: | ---: | ---: | ---: |
| `pwrcl_alt_pll` | 28,305,168 | 28,305,200 | 256 | 0 |
| `perfcl_alt_pll` | 28,305,776 | 28,305,808 | 256 | 0 |

The field was at structure offset +32. Three adjacent 32-bit little-endian values were checked as `(9, 256, 0x4001051b)` before each write. This is an additional consistency check after the full image hashes, not a signature search that makes arbitrary kernels compatible.

Exactly two bytes differ between the original and patched raw images. All other bytes, including the instruction bytes, remain equal. Recompression changes many bytes of the compressed representation, so “two-byte kernel data patch” must not be shortened to “only two bytes in boot.img changed.”

Do not paste these offsets into a hex editor for another kernel. Compiler, configuration, link layout, source changes, and even unrelated data can move the structures. A port needs evidence for its own layout or, preferably, a controlled source build.

## Device-tree caps

The parser walks the FDT structure tokens and string table. It identifies `qcom,pwrcl-speedbin*-v0` and `qcom,perfcl-speedbin*-v0` properties, each containing frequency/voltage-corner pairs. For the retained case, it keeps frequencies at or below 1,593,600,000 Hz for `pwrcl` and 902,400,000 Hz for `perfcl`.

The actual DTB may use a lower supported step: some variants retain 883.2 MHz in the performance table. The cap is an upper bound, not an invented operating point. The runtime table on the case phone was separately checked.

Removed pairs are replaced with FDT NOP tokens after shortening the property length. Each DTB keeps its original total size. The parser then verifies that the set of property names is unchanged and that every unrelated property value is identical. Retained voltage-corner values are copied exactly.

There are three tables per cluster in each of twenty DTBs, so the final transformation handles 120 tables. The profile records the original DTB offsets and sizes; the builder checks that the sequence is contiguous and accounts for the entire tail of the kernel payload.

During the original campaign, independent upstream `libfdt` tooling checked the 60 performance tables and, later, the 60 efficient tables. The public builder's own parser is supplemented by tests and by the final byte-for-byte output hash. For an independent port, use another parser such as `fdtget` as well; two implementations agreeing is more informative than one implementation reading its own output.

## Repacking and independent verification

The modified raw kernel was compressed using:

```sh
lz4 -12 -B7 -f Image.patched kernel.patched.lz4
```

The builder decompresses that result and compares all bytes with the intended raw image. It also checks the frame header. The capped DTB tail is appended, the new kernel size is written, and the unchanged ramdisk is placed at the new aligned offset.

The result is padded to the original 32 MiB partition-dump size and its legacy ID recomputed. An independent AOSP unpacker was used during the device campaign. The public package does not redistribute that script; its upstream source is linked in [References](REFERENCES.md).

LZ4 output can depend on implementation/version choices. The public builder therefore refuses to write a final image if the complete SHA-256 differs from the validated result, even if a decompression roundtrip passed. Use the recorded tool version or investigate the difference explicitly. Removing the final hash check would change the scope of the tool.

## Runtime checks that static image checks cannot replace

An image can be structurally valid and still fail on a phone. The campaign separately checked the installed partition hash, boot completion, CPU availability, actual mux parents, module options, frequency tables, hardware clock measurements under load, correctness workloads, display transitions, and repeated boots.

Reported `scaling_cur_freq` and clock `rate` values were insufficient to detect the initial divide-by-two behavior. The debug clock `measure` interface exposed the difference under load. Conversely, a low measurement while idle was not treated as evidence of a broken frequency setting.

The public soak tool does not modify frequency minimums to perform clock measurements. If a researcher does so manually, record the original settings first, use only supported values, restore them reliably, and continue to respect thermal restrictions. The original campaign restored both cluster minimums to 307,200 kHz.

## Why a clean source implementation is still useful

The binary method made a small, auditable intervention possible when the exact compiled source provenance was unknown. A source-built implementation could express the workaround as a deliberate configuration option, document its constraints, and avoid per-build data offsets.

That does not automatically make a rebuilt kernel equivalent. A proper source experiment needs a control build, matching configuration/toolchain, boot and ramdisk compatibility checks, and the same runtime validation. The [research plan](RESEARCH-PLAN.md) describes that next step without claiming it has already been completed.
