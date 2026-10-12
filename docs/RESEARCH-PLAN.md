# Reproduction and research plan

## Aim and present baseline

The immediate outcome is a documented operating configuration for one Pixel XL, with a tested two-core fallback and an exact-input offline builder. The next aim is to determine how reproducible the result is, improve the tools' device validation, and separate competing explanations for the failing clock path.

This plan describes future work. None of the uncompleted rows below should be presented as an achieved result. Stability remains the priority for the recovered phone; reopening a known-failing configuration is a separate research decision.

## Priority order and completion evidence

| Priority | Work | Evidence required to call it complete |
| --- | --- | --- |
| 1 | Exercise the public collector and soak wrapper on a suitable device | Private journal, installed hash, short and longer successful runs, cleanup checks, and a reviewed public summary |
| 2 | Observe retained configuration over normal use | Dated uptime/reboot record, representative application use, charging conditions, failure logs, and standby observations |
| 3 | Reproduce on a second consenting owner's `marlin` | Independent baseline, source hash/provenance, rollback verification, exact change record, and correctness tests |
| 4 | Establish controlled kernel source provenance | Source commit, config, toolchain, reproducible build instructions, unmodified control build, and image layout validation |
| 5 | Separate clock-parent and ACD effects | A compatible experimental matrix with one-factor comparisons and explicit treatment of unsupported combinations |
| 6 | Assess wider frequency and power behavior | Measured clocks, temperatures, energy/standby observations, repeated load and transition checks at each justified configuration |
| 7 | Prepare a maintainable community implementation | Reviewed source option, compatibility matrix, regression tests, documented limitations, and a release process |

Priorities 1–3 provide useful evidence without requiring higher frequencies or renewed testing of the failing normal path. A second negative report, with good identification and logs, is as useful as a success report.

## Validate the public refactor first

When a suitable phone is available, compare a new collector snapshot with manually read product, boot hash, slot, online CPUs, and temperature. Verify that requested pstore is captured or its absence is recorded. Check that the boot backup matches the remote hash and remains unchanged.

Run a short public soak on an already-established configuration, then a longer bounded run if results warrant it. Confirm worker affinity and process exit status, sample continuity, and verify temporary-directory cleanup. Check the exported public JSON against the private result. Record exact ADB, Python, and host versions.

Host simulations already exercise success, temperature stop, unexpected boot identity, and worker failure. Do not create a real overheat or corrupt a working boot image merely to test those branches. A deliberately low policy cutoff on an otherwise normal-temperature phone can test refusal behavior; a malformed input file can test offline hash gates. Test higher-risk device events only on an explicitly designated test unit with recovery available.

## Extend confidence in the retained phone

The completed load duration is short. A practical follow-up record should distinguish:

- Normal reboots from fully powered-off starts.
- Display-off states from actual suspend entry and exit.
- USB-powered tests from battery-powered use.
- CPU arithmetic from GPU, camera, media, storage, and radio activity.
- Thermal stops from checksum failures, resets, application exceptions, and transport disconnects.

Begin with ordinary use and staged, attended load sessions. Increase duration only after the previous stage passes and temperatures settle. For example, a 30-minute requested CPU run fits the current wrapper's two 900-second maximum phases; repeated sessions with cooling and log review give better context than an unattended retry loop. A duration target is a proposed experiment, not a guarantee or a manufacturer specification.

Record charging state, approximate room temperature, screen state, and observed battery temperature. Battery capacity and cycle fields in this case are not trustworthy state-of-health estimates. A controlled discharge experiment is a separate battery investigation and should not be mixed into CPU clock tuning.

Deep suspend needs explicit study because `lpm_levels.sleep_disabled=1` was already present in the original image. Do not remove it silently while claiming to reproduce the retained configuration. If a future experiment changes sleep behavior, give that image a new hash and experiment ID, keep the current image as fallback, and measure actual suspend/resume behavior and idle energy.

## Reproduce on another device

Use the [device report template](../templates/DEVICE-REPORT.md). Establish the phone's product, installed software, lock state, active slot, original image hash, symptoms, and accessible transports before deciding whether the clock-path hypothesis fits.

For the exact supported source hash, the builder can reproduce the same two images; each device still needs its own recovery baseline and validation. For another source hash, stop the existing binary transformation path. The diagnostic collector can still be useful, but changed offsets and image provenance must be established through a new profile or source implementation.

A useful comparison includes a known-healthy `marlin` on matching software. Healthy hardware can help determine whether the alternate-PLL divider behavior is a general property of this driver configuration or peculiar to the case installation. Do not assume that a healthy control's working settings are safe for the failing phone.

Avoid transferring entire private logs between strangers. Exchange a reviewed numerical summary, exact image hashes, selected relevant lines, and a completed report. Owners should retain the original full evidence locally.

## Port to a different compiled boot image

Prefer a controlled source build when feasible. If binary work is justified, a new profile requires all of the following:

1. Establish which boot image belongs to the installed system/vendor build and slot. Preserve it unchanged and identify it by full hash.
2. Parse the actual boot header, compression framing, payload boundaries, appended device trees, and trailing data. Do not force a modern or signed layout through the legacy-v0 parser.
3. Establish the source structures and their compiled layout for that image. Offsets from this case are not transferable evidence.
4. Locate each intended field through trustworthy symbols or independently reviewed binary analysis, and verify the surrounding values. Record how address-to-file-offset translation was established.
5. Confirm the PLL divider interpretation and parent/ACD semantics in that image's driver version. Similar names are insufficient.
6. Enumerate every relevant device-tree frequency table and retain existing voltage-corner pairs. Check all DTBs that the image can select, not just the first one.
7. Preserve the ramdisk and every unrelated image component. Independently validate the new structure and DTBs. Do not silently drop a signature or footer.
8. Give the new profile a distinct ID, input hash, output hashes, source/tool provenance, and tests. Obtain a reviewed recovery plan before physical validation.

Changing `source_boot_sha256` in the existing JSON to make the builder accept a different image does not satisfy these requirements. The final output gate also encodes a known result; replacing all expected hashes without validating the transformation defeats the purpose of a profile.

## Build a controlled source implementation

Recover the exact ROM build manifest, kernel commit, configuration, compiler/linker versions, and packaging steps if possible. First build a control kernel without the workaround. Determine whether it reproduces the relevant behavior and remains compatible with the installed ramdisk and userspace. Record differences if byte-identical reproduction is unavailable.

A source implementation could expose an explicitly named option for the alternate clock path and corrected divider values, document its interaction with ACD, and apply selected frequency caps in device-specific DT data. Preserve default behavior for unaffected devices unless broader evidence supports a change. Do not turn this single case into a silent global driver default.

Validation should include source review, boot layout and DT inspection, measured clock behavior, arithmetic checks, reboots, and power-state transitions. The old binary profile remains useful as a reproducible historical reference, even if a better source implementation replaces it for new work.

## Separate the competing clock-path explanations

The existing experiment changed multiple related factors. The following matrix is a research design, not an instruction to flash these states into the recovered phone:

| Clock path | ACD | Divider/caps | Existing evidence or open question |
| --- | --- | --- | --- |
| Normal primary path | Original mode | Performance cap near 902 MHz | E02 restarted with repeated lock warnings; low frequency alone was insufficient |
| Normal primary path | Disabled | Same conservative caps | Not tested; may help distinguish ACD dependence if the driver permits a valid configuration |
| Alternate path | Disabled | Original divide-by-two | Booted and computed correctly; actual clocks were half reported |
| Alternate path | Disabled | Corrected divide-by-one, retained caps | E08 retained configuration and recorded validation |
| Alternate path | Enabled | Any | Rejected by the inspected driver; not a valid independent comparison without deeper engineering |

An A/B/A return sequence can improve causal confidence if it is justified on a designated test device: reproduce a baseline, change one supported factor, then confirm the baseline again. It also reintroduces known failure exposure, so it is not required merely to keep the recovered phone useful.

Repeated lock warnings can arise from the clock circuit, its supply, timing/initialization, or related control logic. Software experiments alone cannot conclusively identify a defective solder joint or rail. A hardware-lab investigation would need its own measurement plan and appropriately qualified equipment access. Heating or reflow is not a diagnostic result and is not part of this toolkit.

## Frequency exploration comes after stability

The retained performance cap is conservative and was not proven optimal. A future campaign could evaluate additional existing operating points one step at a time, with measured clock verification, identical workloads, thermal records, a new image hash per step, and rollback after any correctness or continuity failure.

Do not infer permission to raise voltage, disable mitigation, or remove the DT limits from this plan. Keep voltage entries and thermal behavior unchanged when testing a frequency hypothesis. An apparent speed increase without clock measurement and correctness checks can repeat the divide-by-two misunderstanding.

Performance reporting should distinguish per-core throughput, aggregate throughput, UI behavior, and energy. Use multiple repeated runs under comparable starting temperature and background activity. The earlier approximately 21% SHA improvement on the two-core system does not estimate whole-phone improvement from E08.

## Reporting and release milestones

The first public package can accurately be described as a **single-device case study with an exact-image reconstruction toolkit**. It should not be advertised as a universal repair, a newly discovered physical defect, or an exhaustive comparison with earlier community work.

A later release should state what changed, whether new tools were actually run on hardware, which original hashes are supported, and which failures remain. Keep a changelog. Preserve old result files when a parser bug is corrected and add a review note, as was done for the ramoops false alarm.

For each later public release, review the archive for private identifiers, raw dumps, unrelated files, and binary redistribution obligations. The owner-selected publication destination is [westman2000/pixel-xl-recovery](https://github.com/westman2000/pixel-xl-recovery). Publication there does not imply endorsement by an upstream project.
