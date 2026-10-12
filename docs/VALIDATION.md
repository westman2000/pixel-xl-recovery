# Validation methodology and evidence map

## Three different questions

This project keeps three kinds of validation separate:

1. **Image correctness:** did a transformation produce the intended bytes without changing unrelated payloads?
2. **Device behavior:** did the installed configuration boot, select the intended clocks, and execute the recorded workloads correctly?
3. **Tool correctness:** do the newly packaged scripts parse, refuse, record, and clean up as intended in their tested paths?

Exact image hashes answer the first question. Original phone logs and results answer a bounded part of the second. Host tests, including simulated transport, answer part of the third. None is a substitute for the others.

## Evidence inventory

| Artifact | What it preserves | What it does not establish |
| --- | --- | --- |
| [validation-summary.json](../evidence/validation-summary.json) | Selected image, aggregate counts, durations, maximum sampled temperatures, lifecycle totals | Long-term reliability or a second device |
| [E07-soak.json](../evidence/E07-soak.json) | Predecessor image's two load phases and selected telemetry | Evidence that E07 had the final efficient-cluster DT cap |
| [E08-soak.json](../evidence/E08-soak.json) | Final image's main test, measured clocks, telemetry, and false-alarm review note | An untouched automatically passing first result |
| [E08-post-reboot.json](../evidence/E08-post-reboot.json) | Shorter final-image load after lifecycle checks | Additional ten-minute load |
| [lifecycle.json](../evidence/lifecycle.json) | Ten display transitions, three normal reboots, selected post-boot observations | Deep suspend, power-off cold starts, or standby drain |
| [floating-point.json](../evidence/floating-point.json) | Per-core numerical errors and iteration counts | Exhaustive instruction/FPU/SIMD validation |
| [pll-log-excerpts.txt](../evidence/pll-log-excerpts.txt) | Relevant initial, failed-experiment, and retained-boot warning excerpts/counts | A captured conclusive panic or full private log |
| [image-ledger.json](../evidence/image-ledger.json) | Image basenames, sizes, and hashes | Permission to use them with a different system build |
| [source-references.json](../evidence/source-references.json) | Pinned reference-file hashes and match observations | Exact compiled-ROM source provenance |
| [tool-tests.txt](../evidence/tool-tests.txt) | Public host-suite transcript and scope | Public wrapper hardware validation |

The public evidence was selected from private originals. Serial numbers, host home directories, boot UUIDs, and unrelated raw log contents were omitted. Boot continuity is represented as a reviewed boolean and lifecycle identity changes as a count. Original private records remain the primary local audit trail; the sanitized selection is not a cryptographically authenticated independent laboratory report.

## Load generation and counting

The original main runs used a 32 MiB input. One half was deterministic pseudorandom data and one half repeating byte values, so compression did useful work without making the entire input either trivially compressible or incompressible. Expected SHA-256 and SHA-512 values came from the host. Uploaded input was verified before load.

Four workers were pinned concurrently, one per CPU. Each hash iteration checked both expected digests. Each mixed iteration added a gzip compress/decompress roundtrip and a SHA-256 comparison of the recovered bytes. Thus:

```text
hash checks  = 2 × sum(per-core hash iterations)
mixed checks = 3 × sum(per-core mixed iterations)
```

| Run | Hash iterations CPU0/1/2/3 | Mixed iterations CPU0/1/2/3 | Total checks | Harness elapsed | Max sampled battery |
| --- | --- | --- | ---: | ---: | ---: |
| E07 | 725 / 723 / 433 / 405 | 115 / 116 / 81 / 75 | 5,733 | 610.83 s | 38.2 °C |
| E08 main | 742 / 754 / 464 / 470 | 115 / 116 / 82 / 84 | 6,051 | 616.83 s | 39.0 °C |
| E08 post-reboot | 146 / 146 / 93 / 94 | 23 / 24 / 17 / 17 | 1,201 | 132.44 s | 37.0 °C |

The selected image's two runs total **7,252 checks and 749.27 seconds of harness time**. Their requested phase durations total approximately twelve minutes of load; process startup, monitoring, and completion account for additional elapsed time. E07's 5,733 checks belong to a predecessor image and are not added to the final image's total.

Iterations are deterministic repeated workloads, not independent statistical trials over all possible faults. Repeated correct results provide useful evidence for these paths but do not yield a defensible universal failure probability.

## Clock and continuity checks

The original harness compared the installed active-boot SHA-256 to the intended candidate before exercising it. It recorded boot identities to detect unnoticed restarts and sampled online CPUs, frequencies, temperature, thermal-service state, and CPU accounting. E08 main work intervals showed approximately 99.8–100% CPU busy time in the sampled accounting.

Reported frequency was checked separately from hardware clock measurement. Before the divider correction, a reported 1,593.6 MHz corresponded to about 796.8 MHz, and a reported 902.4 MHz to about 451.2 MHz. After correction, measurements under load agreed closely with requested rates. The main E08 record contains 1,593,608,048 Hz and 902,407,456 Hz hardware measurements for 1,593,600,000 Hz and 902,400,000 Hz reported rates.

Small measurement differences do not imply an overclock to the last recorded digit. These values are debug clock-counter observations. Idle clock gating can also produce much smaller readings. A future report should include the workload and measurement context rather than a lone frequency number.

The private measurement procedure briefly requested existing permitted minimum frequencies and restored both clusters to 307,200 kHz afterwards. It also temporarily relaxed `kptr_restrict` to read symbols, then restored it to 2. The public soak script does neither operation. Its cpufreq guards alone cannot detect a repeated divide-by-two reporting issue.

## Floating-point workload

The preserved [AWK source](../tools/floating_point.awk) computes, for `i=1..200000` and `x=i/1024`:

| Quantity | Recorded maximum on every core | Allowed threshold |
| --- | ---: | ---: |
| Absolute `sqrt(x)^2 - x` | 2.842170943040401e-14 | 1e-9 |
| Absolute `sin(x)^2 + cos(x)^2 - 1` | 2.220446049250313e-16 | 1e-12 |
| Absolute `exp(log(1+x)) - (1+x)` | 8.526512829121202e-14 | 1e-9 |
| Sum of `sin(x)^2 + cos(x)^2` | 200000 | Within 1e-5 of 200000 |

The original controller checked each exit status and output, and boot identity/online CPUs before and after. Four cores completed 200,000 iterations each, for 800,000 total. These are identity-based numerical checks using the installed AWK/libm implementation. They do not compare every operation against an independently computed high-precision reference, and common-mode numerical errors are possible.

## Lifecycle checks

Ten screen cycles recorded `mWakefulness=Dozing` followed by `mWakefulness=Awake`. Three requested normal reboots produced three distinct boot identities; the original harness also checked the installed image hash, all four CPUs, clock parents, and limits on return. The sanitized lifecycle file contains selected observations rather than the complete original snapshots.

Normal reboot validation does not test a cold power-on from a fully powered-off state. Dozing/Awake validation does not establish low-power CPU suspend. The inherited sleep-disabling command-line option makes that distinction especially relevant here.

## Kernel logs and the reviewed false alarm

The campaign preserved live and final dmesg, worker outputs, and result JSON. The main E08 workload completed correctly, but an overly broad `Oops:` expression matched normal `ramoops: attached` initialization. The original failed result was preserved, the matched context was reviewed, the detector was corrected, and the logs were checked again. The amended result explicitly states why the initial verdict changed.

One early `perfcl_pll` warning persisted on final boots. A report saying “zero PLL warnings” would be inaccurate. The meaningful change was the absence of the repeated lock-failure sequence during successful operation. The captured original and E02 warnings support clock-path investigation without proving the exact physical reset mechanism.

Log matching remains heuristic. Correct word boundaries eliminate this particular false positive; they do not turn all kernel text into a perfect health signal. A ring buffer may overwrite old lines, pstore may refer to a different boot, and a disconnected stream may lose evidence. Preserve collection status and timestamps alongside the lines.

## What remains untested

No claim is made about all-memory coverage, uncorrected memory errors, storage endurance, GPU stability, camera/radio stress, deep suspend, days of operation, battery state of health, or maximum stable frequency. No controlled source-rebuilt baseline and no second physical device were part of this case.

The original workloads actually ran on the phone. The public refactor's image outputs were actually rebuilt byte-for-byte. Its ADB control paths were host-tested with simulated devices; they await their own hardware validation. Keeping these statements separate is necessary for an honest reproduction report.
