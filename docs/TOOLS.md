# Tool reference

## Environment and verification scope

The host tools use Python 3.9+ and its standard library. Invoke them with `python3` from the project root. The device tools additionally need Google's `adb` or `fastboot` on PATH; each accepts an explicit executable path. The stable image builder needs the LZ4 command-line utility. Exact image reconstruction was verified with LZ4 1.10.0 on macOS.

The public host suite passed on Ubuntu with Python 3.9 and 3.12 in [GitHub Actions](https://github.com/westman2000/pixel-xl-recovery/actions/workflows/host-checks.yml). Those Linux jobs use simulated device transport and skip the private-image test; they do not validate a real Linux-to-phone session. Windows-specific transport, quoting, and terminal behavior have not been validated. The planner prints POSIX shell commands; do not assume that its quoting is appropriate for PowerShell or cmd.exe.

All device commands require an explicit `--serial`. The collector and soak tool require Android/recovery to report `ro.product.device=marlin`. ADB root must already be available for boot backup and soak. The tools do not enable root, grant authorization, unlock a bootloader, change slots, or choose a device implicitly.

The original hardware campaign used private scripts. The public refactor has host tests and exact image-reconstruction checks, but its new ADB collection and load wrappers were not rerun on a phone during packaging. A packaging smoke attempt stopped at “device not found.” Do not confuse the supplied historical device results with a hardware certification of the public wrappers.

## `inspect_boot.py`: inspect a raw legacy boot image

```sh
python3 tools/inspect_boot.py ../private/boot-original.img
```

Outputs JSON with the complete hash, payload sizes and offsets, command line, stored legacy ID, and whether the ID matches a fresh calculation. It reads only the named host file.

The underlying parser accepts a narrow legacy header-v0 layout with supported page alignment, an empty second-stage payload, zero padding, and a zero trailer. It rejects modern headers and unexplained nonzero trailing data. This strictness is intentional: an unrecognized footer may be meaningful. Inspection does not establish that an image belongs to the connected phone or will boot.

## `build_boot.py`: reproduce a profiled image offline

Required arguments are `--boot`, `--profile`, `--variant rescue|stable`, and `--out`. Optional `--lz4` selects a particular executable. The output directory must not already exist.

```sh
python3 tools/build_boot.py \
  --boot ../private/boot-original.img \
  --profile profiles/marlin-lineage22-case1.json \
  --variant stable \
  --lz4 /path/to/lz4 \
  --out ../private/stable-build
```

Omit `--lz4` when the intended executable is on PATH. The rescue variant does not need LZ4. Both variants start from the same unmodified original, rather than layering changes onto a previously patched image.

The builder writes `boot-rescue.img` or `boot-stable.img` and a `manifest.json`. The manifest records hashes, variant, parser observations, and transformation details; the stable manifest also records LZ4 version and DT changes. Temporary decompression files are created in the host's temporary directory and removed when the build context exits normally or with an exception.

The full source hash is checked before raw kernel offsets are used. The complete output hash must match the selected case variant before the output directory and image are written. An unexpected compression output, changed profile, altered source byte, or incompatible layout causes refusal. An externally killed process can still leave temporary host files or a partial output directory; use a new directory after reviewing what happened.

There is no ADB or fastboot invocation in the builder. A successful build proves the byte transformation, not a successful boot on another phone. See [Implementation](IMPLEMENTATION.md) for the exact checks and the source image's unusual legacy ID.

## `collect.py`: private read-only device collection

```sh
python3 tools/collect.py \
  --serial SERIAL \
  --out ../private/collection-01 \
  --include-pstore \
  --backup-boot
```

| Argument | Meaning |
| --- | --- |
| `--serial` | Required exact device selection |
| `--out` | Required new local directory |
| `--adb` | Optional ADB executable, default `adb` |
| `--include-pstore` | Read `console-ramoops-0` if available |
| `--backup-boot` | Root-required read of the active slot's boot partition |

Collection includes selected build properties, kernel release, boot options, CPU lists, cpufreq tables, relevant clock options/parents, battery/BMS interfaces, thermal-service state, cpusets, and dmesg. It does not request a full Android bugreport, application databases, screenshots, or all properties. Nevertheless, raw kernel and battery output can contain private identifiers.

The pstore option reads the console record, not the Android persistent-message buffer. Unavailable files or non-root dmesg access can yield a partial collection. Capture return codes are in the journal. A final “saved” message means the collected outputs were saved, not that every requested field was readable.

With `--backup-boot`, the tool reads `ro.boot.slot_suffix`, permits only `a` or `b`, downloads `/dev/block/by-name/boot_<slot>`, checks a reasonable byte-size bound, and compares the host SHA-256 with the device SHA-256. It writes `boot-original.img` and `backup.json` only after that comparison. The filename means “original to this collection”; it may already be a modified image. Identify it by hash and record its actual history.

Selected shell queries use bounded subprocess timeouts: typically 15 seconds, 30 seconds for log captures, and 60 seconds for boot backup. A host timeout does not prove a hardware failure. Read-only access can still wake the phone and affect power observations.

## `flash_plan.py`: validate inputs and print a plan

```sh
python3 tools/flash_plan.py \
  --serial SERIAL \
  --profile profiles/marlin-lineage22-case1.json \
  --source-backup ../private/boot-original.img \
  --image ../private/stable-build/boot-stable.img \
  --rollback ../private/rescue-build/boot-rescue.img
```

Optional `--fastboot` selects an executable. The phone must already be in fastboot. The script checks the profiled original, candidate and rescue hashes and sizes, then queries product, current slot, unlocked state, and the selected boot partition's size. It accepts the bootloader's usual stderr output for `getvar`.

The JSON output contains quoted installation, reboot, and rollback commands. **No flash or reboot command is executed.** The planner does not create a backup, test the rollback, establish system/vendor compatibility, or confirm the ownership history of a supplied image. Its JSON explicitly identifies the installation-match condition that fastboot variables cannot prove.

On the first rescue installation, `--image` and `--rollback` may name the same rescue candidate. That does not make it a tested fallback on a new phone. Keep the untouched original and establish that rescue actually works before advancing to the four-core candidate. The runbook describes this sequence.

## `soak.py`: bounded correctness workloads

```sh
python3 tools/soak.py \
  --serial SERIAL \
  --out ../private/load-01 \
  --expected-boot-sha256 YOUR_VERIFIED_INSTALLED_BOOT_SHA256 \
  --cores 0,1,2,3 \
  --seconds-per-phase 30 \
  --data-mib 32 \
  --battery-stop-c 40 \
  --max-freq0-khz 1593600 \
  --max-freq2-khz 902400
```

The expected hash is a required, full lowercase SHA-256. The example placeholder is deliberately not a valid hash. Use the hash of the configuration you have independently chosen and installed. Unlike the builder, the soak tool can measure another `marlin` image when its hash is explicitly supplied; that is not an endorsement of that image.

| Option | Default / range | Interpretation |
| --- | --- | --- |
| `--cores` | `0,1`; indexes 0–3 | CPUs to pin; all must be online |
| `--seconds-per-phase` | 30; 5–900 | Requested duration of each of two phases |
| `--data-mib` | 32; 8, 16, 32, 64 | Shared input size, not an all-RAM test |
| `--battery-stop-c` | 40; 30–40 | Conservative policy cutoff in degrees Celsius |
| `--max-freq0-khz` | Unset | Optional observed CPU0 cpufreq upper bound |
| `--max-freq2-khz` | Unset | Optional observed CPU2 cpufreq upper bound |
| `--adb` | `adb` | Host executable |

Before load, it checks product, root identity, active boot hash, selected online CPUs, battery temperature, thermal-service state, and availability of `taskset`, `sha256sum`, `sha512sum`, `gzip`, and `timeout`. The expected thermal service is `vendor.thermal-engine`. Another ROM may need a reviewed adaptation.

The battery sysfs value is interpreted as tenths of a degree Celsius. The initial plausibility check catches grossly invalid readings; it cannot prove units for an arbitrary driver. A cutoff of 40 °C is an experiment policy, not a manufacturer temperature specification and not a substitute for CPU/SoC thermal management.

The host creates a deterministic data buffer: half pseudorandom bytes, half repeated byte values. It calculates SHA-256 and SHA-512 locally and verifies the uploaded data's SHA-256. The target directory is a unique `/dev/pixel-lab-<nonce>` path; on the case platform `/dev` is RAM-backed. Inspect this assumption when porting. Input data plus per-core compressed/decompressed working files consume additional RAM; a 32 MiB buffer does not mean a 32 MiB total footprint.

Each selected CPU receives one pinned worker. Phase `hash` verifies both digests of the shared data. Phase `mixed` additionally compresses the buffer, decompresses it to a per-core file, and compares the recovered file's SHA-256. Each successful hash iteration counts as two checks; each mixed iteration counts as three. The known expected values come from the host, so “a command completed” is insufficient to pass.

Workers use device uptime for a deadline, a per-iteration temperature check, a shared STOP file, and an outer `timeout` of requested phase duration plus 30 seconds. Host monitoring samples approximately every three seconds, with additional command latency. It checks boot continuity, online CPUs, thermal service, temperature, optional reported frequency limits, worker status, and log-stream availability. It imposes a phase watchdog. These checks do not guarantee that every instantaneous clock or temperature excursion is sampled.

Kernel logs are captured before, during, and after load. The current implementation evaluates critical-message candidates and new PLL failures at the end of the completed workload; it does not promise immediate interruption on the first log line. Worker, temperature, continuity, and transport failures are checked during execution. Existing critical messages stop the load before workers start. Existing early PLL warnings are recorded separately; newly observed PLL lock failures cause the run to fail. `dmesg -w` behavior and readable timestamps are assumptions of the case platform.

### Output and stopping behavior

A local run directory contains `PRIVATE.txt`, `journal.jsonl`, `result.json`, generated `worker.sh`, per-core worker output, and initial/live/final dmesg when available. The temporary host data buffer is removed in cleanup. Raw output includes the device serial and boot UUIDs; keep this directory private.

Journal events are flushed and fsynced. Result JSON is written through a temporary file and rename. On a normal Python exception or Ctrl-C, cleanup requests STOP, allows workers time to finish their current operation, terminates remaining host ADB processes, stops the log stream, and attempts to remove only that run's device directory. `device_temporary_files_removed` records whether the final device cleanup command succeeded. A successful workload can still need cleanup review.

Host process termination or cable loss does not guarantee instant termination of every device-side helper. Workers retain finite deadlines and outer timeouts; a kernel hang is outside their control. After reconnecting, inspect remaining `pixel-lab` processes and the exact `cleanup_path` recorded for the run. Do not use broad deletion patterns. If the host was forcibly killed before finalization, `result.json` may be missing; the journal is evidence of an incomplete run, not a pass.

A successful run proves the recorded bounded checks completed. It does not test all RAM, storage durability, every instruction, GPU load, radio use, deep suspend, or weeks of uptime. It does not verify hardware clock measurements: the optional frequency guards read cpufreq values, which initially hid the divide-by-two issue in this case.

## `floating_point.awk`: the numerical workload used in the case

This source preserves the actual 200,000-iteration numerical program used in E08. It evaluates `sqrt(x)^2`, `sin(x)^2 + cos(x)^2`, and `exp(log(1+x))`, reports maximum errors and a trigonometric sum, and returns nonzero when its declared tolerances are exceeded.

The private harness ran four copies concurrently, pinned with hexadecimal masks `1`, `2`, `4`, and `8`, with 90-second timeouts, image/temperature preconditions, and before/after boot checks. Those results are in [floating-point evidence](../evidence/floating-point.json). The source is included for reproduction; it is not a new automatic device orchestration tool.

To evaluate the program on a host with AWK:

```sh
awk -f tools/floating_point.awk
```

A host result validates the numerical script only. Different AWK and libm implementations may produce different rounding. For a device run, use the already-established product, image, root, CPU, temperature, and rollback checks. Upload the source to an explicitly chosen temporary path, then use the form `timeout 90 taskset MASK awk -f PATH` for each chosen CPU, capture every exit status, verify continuity afterwards, and remove the uploaded file. Keep thermal protections active. See [Validation methodology](VALIDATION.md) for the comparison limits.

## `export_summary.py`: allowlist export

```sh
python3 tools/export_summary.py \
  --run ../private/load-01 \
  --out ../public-load-01.json
```

The exporter accepts the public soak tool's schema-1 `result.json`, not the older private harness format. It exports pass status, selected cores, buffer size, duration, maximum sampled battery temperature, continuity, per-phase iteration counts, and correctness counts. It omits raw text, exception strings, serials, UUIDs, paths, and arbitrary extra fields. The output must not already exist.

Review even the small export before publication. On a stopped run, `boot_continuity=false` means continuity was not established by successful completion; it does not alone prove the device rebooted. Consult the private evidence and write a manually reviewed failure classification.

## Host tests

```sh
python3 -m unittest discover -s tests -v
```

The real-input reconstruction test is skipped unless a matching private original is explicitly supplied:

```sh
PIXEL_ORIGINAL_BOOT=../private/boot-original.img \
  python3 -m unittest discover -s tests -v
```

The test also needs the intended LZ4 executable on PATH. It reconstructs both variants in memory and refuses a one-byte-modified input. Other tests exercise parser bounds, repacking, DT property preservation, input refusals, error-log matching, privacy export, fastboot response parsing, and simulated soak success/failure cleanup. The supplied transcript distinguishes these checks from physical-device tests.

Do not suppress a failing test to obtain a green report. Preserve the initial result, classify the problem, fix the responsible layer, and rerun the relevant checks. The recorded ramoops false positive is an example of why that distinction matters.

## Rebuild the offline reader

```sh
python3 tools/render_docs.py
python3 tools/render_docs.py --site
```

The first command renders the package's twelve Markdown chapters into `READ-ME.html` with local navigation, readable code blocks, and scrollable tables. The second generates `index.html` for the [GitHub Pages website](https://westman2000.github.io/pixel-xl-recovery/), with evidence/source links pointing to GitHub. The renderer uses no network or third-party packages. It intentionally supports only the Markdown subset used by these documents; it is not a general Markdown engine. Edit the Markdown sources first, then regenerate both HTML files.

The reader references local evidence and source files, so keep it with the extracted project when following those links. The text and navigation work without a server. Use `SHA256SUMS` to check the files in a distributed package; hashes detect changed bytes, not publisher authenticity.

GitHub Pages is configured to publish the root of the `main` branch. The `.nojekyll` marker serves the prepared HTML directly. After changing distributed files, regenerate `SHA256SUMS`; public CI checks it. The site and offline reader share the same Markdown sources, so their technical content stays aligned.
