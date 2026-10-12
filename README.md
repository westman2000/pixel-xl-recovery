# Pixel XL clock recovery investigation and toolkit

An instrumented case study of a first-generation Google Pixel XL, codename **marlin**, that repeatedly failed to boot. A two-core boot option first restored Android. Further experiments restored all four cores using alternate CPU PLLs, corrected output dividers, and conservative frequency limits.

Start with the [case study](docs/CASE-STUDY.md) to read the investigation, or the [recovery runbook](docs/RECOVERY-RUNBOOK.md) to follow the diagnostic sequence. All documentation is in English.

**[Read the website](https://westman2000.github.io/pixel-xl-recovery/)** · **[Download the latest release](https://github.com/westman2000/pixel-xl-recovery/releases/latest)** · [Report a result or problem](https://github.com/westman2000/pixel-xl-recovery/issues/new/choose) · [Host checks](https://github.com/westman2000/pixel-xl-recovery/actions/workflows/host-checks.yml)

For the single offline reading copy, download and extract the release archive, then open `READ-ME.html` in a browser. GitHub displays HTML as source; the Markdown chapters above can be read directly on GitHub. Keep the extracted files together so the reader's evidence links work.

**One physical device was tested. This is a documented workaround with a narrowly supported image builder, not a universal bootloop repair.** The exact physical defect remains unknown. The results justify further investigation of the normal clock path; they do not prove that a particular transistor, solder joint, power rail, or PLL is damaged.

The retained configuration passed approximately 12 minutes of concurrent correctness workloads, 7,252 checksum and compression checks, 800,000 floating-point test iterations across four cores, three normal reboots, and ten display Dozing/Awake transitions. Maximum sampled battery temperature during its load runs was 39.0 °C. These are bounded tests, not evidence of months of reliable operation.

## Start with the appropriate path

| Your situation | Start here |
| --- | --- |
| You want the complete story and evidence | [Case study](docs/CASE-STUDY.md) |
| Your Pixel XL is bootlooping and you need a cautious sequence | [Recovery runbook](docs/RECOVERY-RUNBOOK.md) |
| You want to inspect or reproduce the boot modifications | [Implementation](docs/IMPLEMENTATION.md) |
| You want exact test methodology and evidence limits | [Validation](docs/VALIDATION.md) |
| You want the CLI commands and their limits | [Tool reference](docs/TOOLS.md) |
| Your boot image differs from this case | [Porting and research plan](docs/RESEARCH-PLAN.md) |
| You want to help reproduce or publish results | [Contributing](CONTRIBUTING.md) and [report template](templates/DEVICE-REPORT.md) |

The case involved **LineageOS 22.2-20261003-NIGHTLY-marlin**, Android 15, and a kernel reporting `4.4.302+`. These are observed properties. They do not authenticate where the ROM came from, identify its exact build source commit, or establish support for another release with a similar name. The runtime fingerprint was inconsistent with the actual Android release and was not used as the image identity.

## What changed

| Component | Retained setting |
| --- | --- |
| CPU availability | All four CPUs, numbered 0–3 |
| Efficient cluster CPU0/1 | Maximum 1,593,600 kHz |
| Performance cluster CPU2/3 | Maximum 902,400 kHz |
| CPU clock parents | Alternate PLLs for both clusters |
| ACD option | Disabled for the alternate-PLL mode |
| Alternate PLL output dividers | Changed from divide-by-two to divide-by-one |
| Retained voltage entries and thermal configuration | Preserved |
| Android system and vendor partitions | Not flashed in these experiments |
| Recovery fallback | A previously tested boot image limited to two CPUs |

Only **two data bytes in the decompressed kernel** were changed for the divider correction. That is not the total size of the boot-image modification: command-line fields, device-tree frequency tables, compressed kernel bytes, layout offsets, and the legacy header checksum also changed.

The original boot already included `lpm_levels.sleep_disabled=1`. It was preserved. Display transitions are therefore not presented as proof of deep suspend or good standby battery life.

## Compatibility before convenience

The offline builder accepts only an original boot image with this full SHA-256:

```text
26d5c3e57bfcdd3b45f9d66e4ec7224cfca5ac43a003ff433f19288bd63bcf4c
```

That restriction protects against applying raw kernel offsets to a different binary. It is **not** a claim that every phone using this image can safely use the workaround. A matching image can still run on a phone with a different fault.

No boot images, kernel binaries, personal device identifiers, screenshots, or complete private logs are included. Obtain a backup of your own matching installation. If its hash differs, use the diagnostic tools and porting plan; do not change the expected hash merely to bypass the check.

This kit does not cover Pixel 2 or newer devices, the smaller `sailfish` Pixel, Nexus devices, locked bootloaders, modern `vendor_boot`/`init_boot` layouts, AVB signing, or arbitrary Snapdragon boards. Related hardware is a research lead, not a compatibility guarantee.

## Quick offline reproduction

Requirements: Python 3.9 or newer and, for the four-core build, the LZ4 command-line program. The exact reconstruction was verified with **LZ4 1.10.0**. Standard-library Python is sufficient; no Python packages need to be installed.

Get the tools by extracting a release archive or cloning the repository:

```sh
git clone https://github.com/westman2000/pixel-xl-recovery.git
cd pixel-xl-recovery
```

Run these commands from the kit directory. Keep original images and generated outputs outside the public project:

```sh
python3 tools/inspect_boot.py ../private/boot-original.img

python3 tools/build_boot.py \
  --boot ../private/boot-original.img \
  --profile profiles/marlin-lineage22-case1.json \
  --variant rescue \
  --out ../private/rescue-build

python3 tools/build_boot.py \
  --boot ../private/boot-original.img \
  --profile profiles/marlin-lineage22-case1.json \
  --variant stable \
  --out ../private/stable-build
```

The builder never contacts a phone. It rejects existing output directories and writes an image only after the result matches the recorded case hash. “Stable” is the retained case variant name; it does not certify a new device.

Expected outputs:

```text
rescue  7c6f9d632f45f5b5000e541cef5ae17b48b496e6d9135e5058578da0748cd8e8
stable  4635c2c76c37ff34259bfdc15d7e430c95cbc24cfd85cd864b877f0a21d2ccee
```

Read the runbook before installing either image. On the case device, `fastboot boot` rejected both the original and modified images with `dtb not found`; temporary boot was not an available escape hatch. Recovery was contained in the boot image, so modifying boot affected the recovery path too.

## Included tools

| Tool | Purpose | Device effects |
| --- | --- | --- |
| `inspect_boot.py` | Inspect a supported raw legacy image | None |
| `build_boot.py` | Reproduce the two hash-gated case images | None |
| `collect.py` | Capture selected diagnostics and optionally back up active boot | Reads from the device; no root enablement or reboot |
| `flash_plan.py` | Check files and a device already in fastboot, then print commands | Read-only fastboot queries; never flashes |
| `soak.py` | Run bounded per-core hash and compression checks | Temporary RAM-backed files and CPU load |
| `export_summary.py` | Export an allowlist of numerical test results | None |
| `floating_point.awk` | Preserve the numerical workload used in E08 | None until explicitly run on a target |

The recovery runbook supplies the deliberate installation, rollback, and reboot steps. There is no automatic bootloader unlock, slot switch, wipe, frequency override, thermal disable, or unattended flashing loop in these tools.

## Evidence and validation

- [Experiment history](docs/CASE-STUDY.md) includes failed approaches as well as successful ones.
- [Numerical results](evidence/validation-summary.json) preserve exact counts, durations, and temperatures.
- [PLL excerpts](evidence/pll-log-excerpts.txt) show the observed failure signature.
- [Image ledger](evidence/image-ledger.json) identifies the original and intermediate images.
- [Reference source hashes](evidence/source-references.json) distinguish reference code from the unknown exact ROM build provenance.
- [Host test output](evidence/tool-tests.txt) records the public toolkit tests.

The original device campaign used a private, device-specific harness. The public version was refactored afterwards. Its parser, transformation, refusal, redaction, and stress orchestration paths have host tests; both boot outputs were reconstructed byte-for-byte from the private original image. The phone was no longer available over ADB during packaging, so the new public collector and stress wrapper have **not** been newly validated against the phone. Simulated transport tests are labelled as such.

## Sharing and attribution

New toolkit code and documentation are provided under the [MIT license](LICENSE). Upstream Android, LineageOS, Linux, and LZ4 components retain their own licenses; see [NOTICE](NOTICE). This is an independent community investigation, not an official Google or LineageOS repair procedure.

[PUBLIC-POST.md](PUBLIC-POST.md) provides a shareable English summary, and [References](docs/REFERENCES.md) records upstream sources. The project is maintained at [westman2000/pixel-xl-recovery](https://github.com/westman2000/pixel-xl-recovery). Use [GitHub issues](https://github.com/westman2000/pixel-xl-recovery/issues) for reviewed reproduction reports and tool problems.

GitHub Actions runs the host suite on Python 3.9 and 3.12 and checks documentation and package hashes. The private-image reconstruction test is skipped in public CI because firmware is not distributed; it passed locally with the real case input. See [the local test transcript](evidence/tool-tests.txt).

Keep raw collections private. Review exported summaries before posting them. To contribute, start with the template and explain exactly what was observed, what was changed, and what failed. A second independently reproduced device is more valuable than an unsupported claim of a universal fix.
