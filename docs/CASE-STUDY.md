# Pixel XL bootloop investigation

## Finding and scope

A Pixel XL that had been unused for years was connected for experimental recovery. It could reach fastboot and recovery, but Android repeatedly failed to stay up. Restricting boot to CPU0 and CPU1 produced a usable Android session. Later, all four cores executed correct workloads after switching both CPU clusters to alternate PLLs, disabling ACD for that mode, correcting two alternate-PLL divider settings, and limiting the performance cluster to 902.4 MHz.

The retained configuration also limits CPU0/1 to 1,593.6 MHz. This prevents the approximately 1,996.8 MHz bursts observed when relying only on runtime limits. The owner explicitly preferred stability over maximum speed.

This is an experiment on **one physical phone**. It establishes a functioning workaround for that phone and image under the recorded tests. It does not establish the prevalence of the fault, prove the physical location of damage, or certify any other unit. No microscopic inspection, oscilloscope measurement, power-rail probing, solder repair, or exact source-rebuilt control kernel was part of the investigation.

## Device and software observations

| Item | Observation |
| --- | --- |
| Product | Google Pixel XL, `marlin` |
| SoC family | MSM8996pro / Snapdragon 821 |
| CPU arrangement | Four Kryo CPUs in two frequency-sharing clusters |
| CPU0/1 | Efficient cluster, clock names using `pwrcl` |
| CPU2/3 | Performance cluster, clock names using `perfcl` |
| Bootloader | Unlocked; reported version `8996-012001-1908071822` |
| Active slot during the campaign | `a` |
| Installed system reported | LineageOS `22.2-20261003-NIGHTLY-marlin` |
| Android release / kernel release | 15 / `4.4.302+` |
| Boot image | 32 MiB raw legacy Android boot image, header version 0 |
| Kernel payload | LZ4 frame followed by 20 appended device trees |
| Ramdisk | Preserved throughout the successful modifications |
| Runtime clock bin | Performance/power/CBF speed bin 1, PVS version 0 |

The build fingerprint suggested Android 10 while other properties and the running system identified Android 15. The investigation therefore used the image hash, kernel contents, relevant properties, and runtime state together. A plausible fingerprint is not a compatibility check.

Host records place the main experiment campaign on 2026-10-12 UTC. The phone clock and battery first-use fields showed different dates. Phone timestamps were not treated as trustworthy chronology. The original private directory used the preceding local calendar date.

The original image SHA-256 was:

```text
26d5c3e57bfcdd3b45f9d66e4ec7224cfca5ac43a003ff433f19288bd63bcf4c
```

The exact source commit and distribution provenance of that compiled image were not established. Reference source files were later pinned to a public LineageOS commit and checked against the copies used during investigation. Matching those files does not identify the compiled kernel's full source tree or configuration.

## Initial evidence

The preserved console from a failed Android boot contained **100** messages reporting that `perfcl_pll` did not lock. The captured boot ended around 50 seconds. It did not contain a conclusive panic explaining the reset. The matching message was:

```text
PLL perfcl_pll didn't lock after enabling it!
```

A PLL is a circuit used to synthesize a clock frequency. In this context, “lock” indicates that the expected stabilized state was detected. A log saying that the lock condition was not reached identifies a clock-path problem worth investigating; it does not by itself identify a damaged component.

Recovery provided an important counterexample. All four CPUs could be online there for several minutes, with five early matching messages in its captured log. That observation made “both large cores are completely dead” an inadequate explanation.

The initial diagnosis remained a hypothesis: Android activity, clock changes, or a related mode transition appeared to expose a problem associated with the performance cluster's normal clock path. Different workloads and power states in recovery could matter. The observations did not isolate which of those differences was decisive.

## Establishing a recovery baseline

The first useful boot modification appended:

```text
nr_cpus=2 maxcpus=2
```

Only the boot-header command line changed. The compressed kernel, device trees, ramdisk, and original header ID were preserved. Android then booted and remained usable long enough to collect diagnostics and plan controlled experiments. CPU0/1 formed the practical recovery baseline.

This was more than a temporary runtime CPU-offline operation: the boot-time options limited the CPU set made available to the kernel. Runtime attempts to use unavailable CPUs were not assumed to be meaningful tests of their hardware.

The rescue image hash was:

```text
7c6f9d632f45f5b5000e541cef5ae17b48b496e6d9135e5058578da0748cd8e8
```

This image remained the primary fallback throughout the campaign. The Android bootloader was already unlocked. The experiments did not establish a data-preserving way to unlock a locked device.

Temporary boot was attempted with both original and changed images; the bootloader rejected them with `dtb not found`. The investigation therefore used explicit writes to `boot_a`, followed by normal boot and verification. `boot_b`, system, and vendor were not flashed, and slots were not switched. The boot image also supplied recovery on this installation, so a fallback boot image and the ability to enter fastboot were essential.

## Preliminary performance and battery observations

The two-core system was noticeably slower than a fully functioning four-core configuration would be expected to be. Several separate observations were made before the clock-path experiments:

- CPU0/1 briefly accepted a near-2 GHz setting when both relevant runtime limits were adjusted. A narrow parallel SHA-256 workload improved by about 21% in that short comparison. The system subsequently restored the lower limit. This was not a whole-phone benchmark or a basis for a long-term overclock.
- Some Android/vendor cpuset groups behaved poorly with only two CPUs available. Temporary two-core cpuset adjustments helped that restricted configuration. Those settings were not appropriate for the eventual four-core configuration, where the normal top-app group contained CPU0–3.
- Rendering resolution was changed to 1080 × 1920 and animation scales to 0.5. These are UI changes, not repairs to CPU hardware. The final measured density override was 448; an earlier note recorded 420. The measured 448 setting was left alone rather than silently overwritten.
- Battery temperature and charging data were readable. Full-charge capacity equalled the configured design value and cycle count was zero, but the device history and recent first-use metadata made those fields unsuitable for calculating battery health. No complete discharge-capacity test was performed.

These observations are retained because they explain earlier choices and prevent unrelated UI or battery changes from being credited with the clock recovery.

## Experiment sequence

The experiment IDs below refer to saved artifacts, not different devices. Each image was identified by SHA-256, and successful boots were checked through ADB rather than inferred from a completed flash command.

| Stage | Configuration | Observation | Consequence |
| --- | --- | --- | --- |
| Rescue baseline | Two CPUs, original clock path | Android booted and remained usable | Preserve as rollback |
| E01 | Two CPUs; performance-cluster DT tables capped near 902 MHz | Booted; live DT and image checked; one early PLL warning | Validate the DT modification before exposing another CPU |
| E02 | Three CPUs; same frequency cap; original clock path | Booted, logged 58 PLL-lock failures, then restarted before planned CPU2 stress began | Low frequency alone was insufficient |
| E03 | Two CPUs; alternate PLLs; ACD off | Booted and produced correct hashes | Alternate path was viable for the control pair |
| E04 | Three CPUs; alternate PLLs; ACD off | CPU2 completed 50 pinned checks correctly | The first performance core could execute real work |
| E05 | Four CPUs; alternate PLLs; ACD off | Five pinned hashes per core, 20 total, were correct | Both performance cores could execute work |
| E06 | Two CPUs; alternate output dividers changed to divide-by-one | Six checks passed; measured efficient-cluster clock returned to about 1.594 GHz | Validate the divider correction on the control pair |
| E07 | Four CPUs; corrected dividers; performance cap 902.4 MHz | Ten-minute load campaign passed; occasional CPU0/1 boosts near 2 GHz observed | Keep the working path, remove unwanted boosts |
| E08 | E07 plus efficient-cluster DT cap 1,593.6 MHz | Full retained-configuration validation passed | Leave this conservative image installed |

For E02, ADB reappeared during the next boot and was used to enter fastboot and restore the known-working image. The subsequently captured pstore included the intercepted boot and shutdown; it did not establish the original reset's precise cause. This distinction matters: “the phone restarted after repeated PLL warnings” is supported, while “a captured kernel panic proved the PLL caused the reset” is not.

## Finding the alternate clock path

Inspection of the reference clock driver identified an alternate-PLL mode and a corresponding ACD restriction. The boot options used were:

```text
clock_cpu_8996.use_alt_pll=1 clock_cpu_8996.enable_acd=0
```

Both options matter. The [reference CPU clock driver](https://github.com/LineageOS/android_kernel_google_marlin/blob/4075955d5b36f402a0f43ae01b708ae4705ce484/drivers/clk/msm/clock-cpu-8996.c) contains the alternate-parent selection and rejects the combination of alternate PLLs with ACD enabled. Here ACD refers to adaptive clock distribution, a separate part of the clock-control arrangement.

The options were not accepted merely because they appeared in a command line. Runtime checks read the module parameters and actual mux parents:

```text
pwrcl_hf_mux parent  -> pwrcl_alt_pll
perfcl_hf_mux parent -> perfcl_alt_pll
```

The observation was encouraging but also confounded: the experiment changed the selected PLL path **and** the ACD mode. It therefore cannot separate a primary-PLL problem from an ACD-related issue, or a combination of the two.

## Discovering the divide by two behavior

Early alternate-PLL experiments were slower than their reported frequency values suggested. Measuring clocks under load exposed the discrepancy:

| Cluster | Reported rate before correction | Measured rate before correction |
| --- | --- | --- |
| Efficient | 1,593.6 MHz | Approximately 796.8 MHz |
| Performance | 902.4 MHz | Approximately 451.2 MHz |

Idle measurements were not reliable evidence of maximum frequency because clock gating could yield much smaller values. The comparison was made while work was running, with a brief request for existing permitted minimum frequencies; the original minimums were restored afterwards.

The structures associated with the alternate PLLs contained `post_div_config = 0x100`, representing the divide-by-two setting in the reference code. Live symbols from the same running kernel helped locate these structures in the decompressed image. The structure layout was checked against [the PLL header](https://github.com/LineageOS/android_kernel_google_marlin/blob/4075955d5b36f402a0f43ae01b708ae4705ce484/include/soc/qcom/clock-alpha-pll.h), and the treatment of its fields was checked against [the alpha PLL implementation](https://github.com/LineageOS/android_kernel_google_marlin/blob/4075955d5b36f402a0f43ae01b708ae4705ce484/drivers/clk/msm/clock-alpha-pll.c).

Each `post_div_config` value was changed from 256 to zero. In this specific little-endian binary, each change cleared one byte, for two changed bytes in total. Adjacent values were validated as well. Kernel instructions were not patched.

After the correction, E06 measured approximately 1,593.595 MHz for a requested 1,593.6 MHz. E07 and E08 also measured approximately 902.4 MHz on the performance cluster. Computation checks continued to pass. The result connected the suspected divider error to an observed clock and workload effect.

The temporary change needed to read kernel symbol addresses was reversed: `kptr_restrict` was restored to its original value of 2. This is not a request for other users to leave kernel pointers exposed.

## Frequency caps and image construction

The original performance tables included frequencies up to 2,150.4 MHz for the observed speed bin. Early experiments retained only entries at or below 902.4 MHz. Device-tree variants with different frequency steps had a retained maximum of 883.2 MHz; the actual phone used the 902.4 MHz variant.

Each boot payload contained twenty device trees. All three performance speed-bin tables in each were processed, sixty tables total. E08 additionally processed all sixty efficient-cluster speed-bin tables to impose a 1,593.6 MHz upper bound. Retained frequency/voltage pairs were copied without changing voltage values. Every unrelated property was checked for byte equality.

The tables were shortened in place: removed property data was replaced with legal FDT NOP tokens. This preserved each DTB's overall size and the appended DTB sequence. The [device-tree specification](https://devicetree-specification.readthedocs.io/en/stable/flattened-format.html) defines those structural tokens. Independent `libfdt` reads verified the resulting tables during the original campaign.

The corrected kernel was recompressed with LZ4. Its compressed size changed, so the ramdisk had to be placed at the new page-aligned offset and the kernel-size field updated. The stable image's legacy header ID was recomputed. A separate AOSP unpacker confirmed the payload layout and unchanged ramdisk. The [implementation document](IMPLEMENTATION.md) provides the exact numbers and checks.

No inference about image format was made from the Android release number. This installation ran Android 15 using a legacy header-v0 image; the actual bytes were authoritative for parsing.

## Retained configuration and results

E08 was retained with four online CPUs, alternate clock parents, ACD disabled, divide-by-one output settings, and caps of 1,593.6/902.4 MHz. These settings reside in the boot image and were confirmed after repeated normal boots. Runtime frequency-forcing daemons were not installed.

| Run | Elapsed harness time | Verified checks | Maximum sampled battery temperature |
| --- | ---: | ---: | ---: |
| E07 preliminary four-core load | 610.83 s | 5,733 | 38.2 °C |
| E08 main load | 616.83 s | 6,051 | 39.0 °C |
| E08 load after three reboots | 132.44 s | 1,201 | 37.0 °C |
| E08 combined | 749.27 s | 7,252 | 39.0 °C |

Elapsed harness time includes sampling and phase boundaries. The requested E08 worker durations were five minutes of hashing and five minutes of mixed work, followed later by one minute of each. Describing that as about twelve minutes of load is more informative than treating every harness second as uninterrupted maximum utilization.

Each core had a separately pinned worker. The test data was a deterministic 32 MiB buffer containing pseudorandom and repeated-byte regions. Expected SHA-256 and SHA-512 digests were computed on the host. The mixed workload added gzip compression, decompression, and verification of the recovered bytes. One hash-phase iteration counted as two checks; one mixed iteration counted as three. These counts are not independent statistically distributed trials of every possible CPU instruction or every RAM address.

The efficient and performance cores all produced correct results. Sampled CPU accounting during the main E08 work intervals showed approximately 99.8–100% busy time. Boot identities remained unchanged within each load run. The thermal service remained running. The test harness used an additional conservative 40 °C battery cutoff; it did not need to stop either completed E08 run for temperature.

After the main run, ten display transitions from `Dozing` to `Awake` succeeded. Three requested normal reboots produced three distinct boot identities. The installed image hash, online CPUs, clock parents, and frequency limits were checked after each.

A separate floating-point workload executed 200,000 iterations on each of four cores. It checked square-root, trigonometric, and logarithm/exponential identities within declared tolerances. All cores produced the same recorded maxima: approximately `2.84e-14`, `2.22e-16`, and `8.53e-14`, respectively. The trigonometric accumulation was 200,000. This adds coverage beyond byte hashing, without claiming exhaustive FPU or SIMD validation.

The final image SHA-256 was:

```text
4635c2c76c37ff34259bfdc15d7e430c95cbc24cfd85cd864b877f0a21d2ccee
```

## The false log alarm

The first automatic E08 result was marked failed after both load phases had completed successfully. Its kernel-error regular expression searched for `Oops:` without a word boundary. It therefore matched the substring in a normal `ramoops: attached` initialization message.

The complete matching line, live log, final log, boot identity, and worker results were reviewed. The original result file was preserved. The expression was corrected to require a word boundary, then the existing logs were checked again. The E08 result was marked passed with an explicit review note; the history was not rewritten to conceal the harness failure.

The public toolkit includes tests showing that normal ramoops registration is accepted while an actual Oops or panic is detected. Error detectors can themselves introduce false conclusions; a failed automation check must be interpreted before it becomes a hardware diagnosis.

## What the evidence supports

The strongest supported finding is a dependence on clock-path configuration. Low frequency with the original path was insufficient in E02. The alternate-path configuration allowed both performance CPUs to compute correctly and remain online during the recorded loads. Correcting the dividers changed measured clocks and restored the expected frequency behavior.

The original failing capture had 100 performance-PLL warnings, E02 had 58, and the final boots each retained one early warning around 1.3 seconds. No repeated lock-failure sequence appeared during the successful load runs. The remaining early warning should not be hidden or relabelled as zero errors. It is consistent with the fact that selecting an alternate running path does not remove all primary-clock initialization.

Hardware instability in the normal PLL, its supply, or associated clock logic is a plausible explanation. An ACD-specific problem or a driver/initialization interaction remains plausible too. The experiment did not hold all those factors constant independently, so it cannot rank individual physical components with confidence. A “reflow the CPU” conclusion, a precise solder diagnosis, or a claim that two cores had physically died would exceed the evidence.

## Limits and remaining issues

- One device and one original image were investigated. No second-device replication or controlled comparison with a known-healthy Pixel XL was performed.
- The retained mode trades peak frequency for a tested operating configuration. This campaign did not establish the highest stable frequency or overall UI speed relative to a healthy stock phone.
- Sustained operation over days, deep suspend, standby drain, power-off cold starts, radio workloads, camera use, and GPU-heavy applications were not validated by these tests.
- Battery temperature was monitored, but the reported capacity and cycle fields did not establish battery state of health.
- The ROM also showed Java exceptions in Google Carrier Services and hotword enrollment. Correct CPU arithmetic does not repair missing providers or application permission problems.
- An OTA or boot-image replacement can remove the workaround. Reusing this boot image with a different system/vendor build is outside the validated case.

The useful outcome is a recoverable, evidence-backed operating configuration and a method others can test carefully. The next research steps are set out in the [research plan](RESEARCH-PLAN.md).
