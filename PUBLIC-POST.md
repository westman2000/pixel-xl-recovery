# Pixel XL bootloop case: recovering four cores through an alternate clock path

We investigated a first-generation Pixel XL (`marlin`) that had been unused for years and repeatedly failed to stay in Android. The original failed-boot console contained 100 `perfcl_pll` lock warnings. Recovery could still run all four CPUs, so the evidence did not support simply declaring the two performance cores dead.

A boot image restricted to CPU0/1 first restored a usable Android session. Capping the performance cluster near 902 MHz and enabling CPU2 on the original clock path still produced repeated warnings and another restart. Switching both clusters to the driver's alternate PLL mode, with ACD disabled as required by that mode, allowed all four cores to execute correct workloads.

There was another finding: the alternate path initially ran at half its reported frequency. Clock measurements under load exposed a divide-by-two setting. Correcting two data bytes in the decompressed kernel restored measured rates to the intended values. The retained image also caps CPU0/1 at 1,593.6 MHz and CPU2/3 at 902.4 MHz, preserving retained voltage entries and thermal settings.

The selected configuration completed 7,252 checksum/compression checks over approximately twelve minutes of requested load, 800,000 floating-point iterations across four cores, three normal reboots, and ten display Dozing/Awake transitions. Maximum sampled battery temperature during its load runs was 39.0 °C. One early PLL warning remained; the repeated failure sequence did not recur in those runs.

This is **one device**, not a universal fix or a proven diagnosis of a particular physical defect. The PLL path and ACD mode changed together, and the exact compiled kernel provenance remains unknown. Deep suspend, days of reliability, and a second-device reproduction remain open work.

The accompanying package contains the full experiment sequence, failed approaches, sanitized numerical evidence, a recovery/rollback runbook, an exact-input boot builder, diagnostic collection, a bounded per-core load tool, host tests, and a research plan. The builder accepts only one full original-image SHA-256 and reproduces the two validated case images byte-for-byte. No firmware binaries or personal device identifiers are distributed.

The device campaign used a private harness. The refactored public scripts have host tests and exact reconstruction checks; their new ADB wrappers still need a fresh hardware validation. The documentation also preserves a useful harness mistake: `Oops:` incorrectly matched normal `ramoops` initialization until the detector was fixed and the original results were reviewed.

We would welcome carefully documented independent reports, especially comparisons that help separate clock-parent and ACD effects. Start with the included README and device-report template. Do not bypass the image hash checks or transfer raw offsets to a different build.

Read the documentation and get the tools at [westman2000/pixel-xl-recovery](https://github.com/westman2000/pixel-xl-recovery), or [download the latest release](https://github.com/westman2000/pixel-xl-recovery/releases/latest). Share reviewed results through the repository's [report template](https://github.com/westman2000/pixel-xl-recovery/issues/new/choose).
