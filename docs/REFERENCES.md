# References and source provenance

## Reference code used to interpret the clock path

The reference repository is [LineageOS/android_kernel_google_marlin](https://github.com/LineageOS/android_kernel_google_marlin), pinned for this package to commit:

```text
4075955d5b36f402a0f43ae01b708ae4705ce484
```

The following files at that commit matched the local reference copies used in the investigation. Full file SHA-256 values and raw URLs are recorded in [source-references.json](../evidence/source-references.json).

| File | Relevance |
| --- | --- |
| [clock-cpu-8996.c](https://github.com/LineageOS/android_kernel_google_marlin/blob/4075955d5b36f402a0f43ae01b708ae4705ce484/drivers/clk/msm/clock-cpu-8996.c) | CPU clock parents, alternate PLL structures, ACD interaction, and frequency-table selection |
| [clock-alpha-pll.h](https://github.com/LineageOS/android_kernel_google_marlin/blob/4075955d5b36f402a0f43ae01b708ae4705ce484/include/soc/qcom/clock-alpha-pll.h) | Alternate PLL structure fields and layout interpretation |
| [clock-alpha-pll.c](https://github.com/LineageOS/android_kernel_google_marlin/blob/4075955d5b36f402a0f43ae01b708ae4705ce484/drivers/clk/msm/clock-alpha-pll.c) | Programming of alpha PLL configuration fields |
| [clock-pll.c](https://github.com/LineageOS/android_kernel_google_marlin/blob/4075955d5b36f402a0f43ae01b708ae4705ce484/drivers/clk/msm/clock-pll.c) | Normal PLL enable/lock handling and associated messages |
| [qcom-cpufreq.c](https://github.com/LineageOS/android_kernel_google_marlin/blob/4075955d5b36f402a0f43ae01b708ae4705ce484/drivers/cpufreq/qcom-cpufreq.c) | cpufreq integration and reported frequency behavior |
| [msm8996pro.dtsi](https://github.com/LineageOS/android_kernel_google_marlin/blob/4075955d5b36f402a0f43ae01b708ae4705ce484/arch/arm/boot/dts/qcom/msm8996pro.dtsi) | MSM8996pro device-tree clock/frequency data |
| [msm8996.dtsi](https://github.com/LineageOS/android_kernel_google_marlin/blob/4075955d5b36f402a0f43ae01b708ae4705ce484/arch/arm/boot/dts/qcom/msm8996.dtsi) | Related platform device-tree definitions |

The DTS files are under `arch/arm/boot/dts/qcom` in this tree even though the decompressed kernel is an ARM64 Image. Do not substitute a guessed `arch/arm64` URL.

**This is reference-code provenance, not compiled-image provenance.** A match for these files does not establish the original kernel's full commit, build configuration, compiler, or ROM distribution authenticity. The original boot's full hash is the binary builder's compatibility identity.

## Boot format and Android tools

- [AOSP boot-image header documentation](https://source.android.com/docs/core/architecture/bootloader/boot-image-header) describes header versions and fields. The kit deliberately implements only the case's legacy-v0 subset.
- [AOSP bootloader locking/unlocking documentation](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking) describes lock-state transitions and data-reset behavior. The case device was already unlocked.
- [AOSP A/B implementation documentation](https://source.android.com/docs/core/ota/ab/ab_implement) describes the slot model relevant to selecting a matching boot partition.
- [Google Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) is the official source for ADB and fastboot.
- [AOSP unpack_bootimg.py](https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/main/unpack_bootimg.py) is the upstream boot-image unpacker used as an independent format reference. The linked main branch is mutable; a future reproducible build should record the exact revision it uses. The private campaign retained its local copy, but no exact upstream revision is claimed here.

## Device trees and compression

- [Devicetree flattened-format specification](https://devicetree-specification.readthedocs.io/en/stable/flattened-format.html) documents the FDT header and structure tokens, including NOP. The transformation shortens selected property payloads and fills the freed structure space with NOP tokens.
- [Device Tree Compiler / libfdt upstream](https://git.kernel.org/pub/scm/utils/dtc/dtc.git) provided the independent DT checks. The private campaign built version 1.7.2 at commit `2d10aa2afe35527728db30b35ec491ecb6959e5c`.
- [LZ4 upstream](https://github.com/lz4/lz4) provides the compression utility. Exact public reconstruction used LZ4 1.10.0 with `-12 -B7 -f`, plus a decompression roundtrip and a final full-image hash gate.

## Community context and attribution

CPU-count restrictions are a diagnostic technique, and community bootloop workarounds predate this case. This package does not claim invention of disabling CPUs, alternative clock paths, or a universal new repair. It documents the specific evidence chain and resulting configuration observed here.

No systematic survey of every earlier Pixel/Nexus bootloop report was completed for this package. Similar forum symptoms should not be treated as proof of a shared hardware defect. A useful future literature review would record device codename, original software, actual diagnostic logs, precise changes, validation duration, and whether data/lock state constrained the experiment.

Upstream projects are cited for code and format interpretation. They have not endorsed this workaround. Full source files and compiled firmware are not redistributed in this kit; see [NOTICE](../NOTICE) for licensing scope.
