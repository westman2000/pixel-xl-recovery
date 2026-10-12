# Pixel XL recovery runbook

## Intended use

This sequence is for an owner or technician investigating a `marlin` Pixel XL with symptoms resembling the case study. Begin with identification and evidence. Advance only when the previous state is understood and a tested return path exists.

The included binary builder supports one exact original boot hash. A different hash is a porting task, not an invitation to bypass validation. A matching hash still does not establish that another phone has the same defect.

The owner in the case study accepted experimental recovery and already had an unlocked bootloader. Your data priorities may be different. Bootloader unlocking normally resets user data; changing lock state is outside this toolkit. Consult the [AOSP bootloader-locking documentation](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking) before considering it. Do not relock a device running an experimental boot image.

## Prepare the host and an experiment directory

Install Android SDK Platform Tools from [Google's official distribution](https://developer.android.com/tools/releases/platform-tools). Verify that both `adb` and `fastboot` are available. The offline image builder additionally needs Python 3.9+ and LZ4; see the tool reference for exact requirements.

Create a private directory outside the public project. Keep original images immutable, give every experiment a new directory, and record full hashes. Do not paste raw collections into a public issue: command lines, persistent logs, device identifiers, and application traces can expose information unrelated to the CPU problem.

In all examples below, replace `SERIAL` with the selected device's actual serial. Do not omit `-s` when more than one Android device might be attached.

```sh
adb devices -l
fastboot devices
```

These commands inspect different transports. An Android device visible in ADB may disappear and reappear as a fastboot device during a requested reboot. An empty ADB list alone does not prove that the USB port or phone hardware is dead.

## Establish what mode is available

| Observation | Next action |
| --- | --- |
| ADB reports `device` | Identify product, boot completion, privilege level, and installed build |
| ADB reports `unauthorized` | Resolve the device-side authorization prompt; this toolkit cannot approve it remotely |
| Fastboot lists the device | Read product, active slot, and unlocked state before any write |
| Recovery is available | Preserve pstore and the matching active boot image if root access permits |
| Neither transport appears | Check cable/port and physical boot-mode entry; do not blindly loop flash commands |

For a connected Android or recovery shell:

```sh
adb -s SERIAL shell getprop ro.product.device
adb -s SERIAL shell getprop ro.lineage.version
adb -s SERIAL shell getprop ro.build.version.release
adb -s SERIAL shell getprop ro.boot.slot_suffix
adb -s SERIAL shell getprop sys.boot_completed
adb -s SERIAL shell id
```

Product should be `marlin` for this kit. A fingerprint or marketing name alone is insufficient. Root is required for several kernel interfaces and partition backup. The collector will not silently enable it. On a compatible userdebug installation where the owner has enabled rooted debugging, an explicit `adb -s SERIAL root` can restart adbd with root privileges. Wait for reconnection and verify `id` again.

## Preserve evidence and the original boot

When root ADB is available, collect a private baseline:

```sh
python3 tools/collect.py \
  --serial SERIAL \
  --out ../private/baseline \
  --include-pstore \
  --backup-boot
```

The tool reads the active slot from Android, backs up that boot partition, and compares the downloaded SHA-256 with a hash computed on the device. It saves the slot and build observations in `backup.json`. It does not switch slots or flash anything.

If root is unavailable, omit `--backup-boot` to collect whatever diagnostics are readable. Permission failures are recorded. A partial collection is not a substitute for a known matching boot image and recovery path.

Preserve pstore early. A later reboot or deliberate shutdown can replace the evidence you wanted. In the case study, an intercepted restart yielded logs of the intercepted boot, not a definitive trace of the preceding failure. Never infer a panic simply because a reset occurred.

Record at least:

- Product, ROM version, kernel release, active slot, and boot hash.
- Available transports and bootloader lock state.
- Online/present CPU lists, cluster frequency tables, and clock parents when readable.
- The count and timestamps of relevant PLL warnings in each captured buffer.
- Battery temperature, thermal-service status, and whether external power is connected.
- What the user observed physically and what the tools actually confirmed.

Keep the original backup outside any build output directory. Hashes identify bytes; filenames such as `stock.img` or `fixed.img` do not.

## Read the failure signature in context

The investigated phone showed repeated `perfcl_pll` lock failures. Recovery could nevertheless run all four CPUs. A two-core Android boot worked, while adding a performance CPU with only a frequency cap still led to another restart.

Look for that pattern, rather than treating every bootloop as equivalent. A bootloop caused by incompatible system/vendor partitions, missing storage, filesystem damage, or an application/framework problem may need a different investigation. An isolated early PLL warning is not enough: even the retained working image logged one during startup.

Likewise, do not interpret normal `ramoops` initialization as an Oops. Read the whole line and surrounding timestamps. The included kernel-log summary lists heuristic candidates; it is not an automated hardware verdict.

## Build the rescue image only when the original matches

Inspect your backup and compare its hash with the profile:

```sh
python3 tools/inspect_boot.py ../private/baseline/boot-original.img
```

If it is the supported input, build a rescue image in a new output directory:

```sh
python3 tools/build_boot.py \
  --boot ../private/baseline/boot-original.img \
  --profile profiles/marlin-lineage22-case1.json \
  --variant rescue \
  --out ../private/rescue-build
```

The result changes only the header command line to request two CPUs. It preserves the original payload and the original header ID, matching the tested rescue bytes exactly. An unsupported hash causes refusal before a modified image is written.

If the hash differs, stop this binary-reproduction path. Continue with the porting plan, obtain an image that actually belongs to the installation, or rebuild a suitable kernel from known source. Do not substitute the final case image for an unrelated ROM.

## Plan installation and rollback before writing

Enter fastboot deliberately, for example from responsive Android:

```sh
adb -s SERIAL reboot bootloader
```

If the device is unresponsive, physical Power/Volume Down entry may be necessary. Software cannot guarantee recovery from a device that no longer exposes a controllable transport.

Read the bootloader state:

```sh
fastboot -s SERIAL getvar product
fastboot -s SERIAL getvar current-slot
fastboot -s SERIAL getvar unlocked
```

The toolkit's planner validates the profiled files and makes read-only fastboot queries:

```sh
python3 tools/flash_plan.py \
  --serial SERIAL \
  --profile profiles/marlin-lineage22-case1.json \
  --source-backup ../private/baseline/boot-original.img \
  --image ../private/rescue-build/boot-rescue.img \
  --rollback ../private/rescue-build/boot-rescue.img
```

For this first installation, the rescue image is a **candidate**, not yet a proven working rollback on your own device. Preserve the unmodified original separately; it restores the previous image bytes even if the previous behavior was a bootloop. Do not proceed to four-core experiments until the rescue candidate has actually booted and been checked on your device.

The planner prints installation and rollback commands but executes neither. It verifies product, active slot, lock state, partition capacity, and image hashes. Fastboot cannot establish that a supplied backup still belongs to the currently installed system/vendor build; you must establish that from your own records. If the active slot or build changed since the backup, reconcile that change before writing.

For an independently verified active slot `a`, the deliberate write would look like:

```sh
fastboot -s SERIAL flash boot_a ../private/rescue-build/boot-rescue.img
fastboot -s SERIAL reboot
```

Use the actual verified slot, not `a` copied from this example. Do not flash both slots as a precaution. Do not switch slots merely because one failed. A/B slots contain related software components, and changing only one component or selecting an incompatible slot can create a different failure. The [AOSP A/B implementation documentation](https://source.android.com/docs/core/ota/ab/ab_implement) explains the slot model.

Do not assume `fastboot boot` will work. On the case device it rejected the original image too. That observation is specific to this device/bootloader/image combination, not a general statement that Pixel XL can never temporarily boot an image.

## Verify the rescue before proceeding

A successful flash command only means the bootloader accepted the write. After Android starts:

1. Confirm `sys.boot_completed=1` and the expected product/build.
2. Re-establish authorized root ADB if needed.
3. Hash the active boot partition and compare it with the image just installed.
4. Read `/proc/cmdline`, CPU `present` and `online`, and actual frequency tables.
5. Capture dmesg and any available pstore before further reboots.
6. Run a short, correctness-checked workload on the CPUs that are actually available.

Example for a verified two-core rescue:

```sh
python3 tools/soak.py \
  --serial SERIAL \
  --expected-boot-sha256 7c6f9d632f45f5b5000e541cef5ae17b48b496e6d9135e5058578da0748cd8e8 \
  --cores 0,1 \
  --seconds-per-phase 30 \
  --out ../private/rescue-load
```

The tool assumes the tested battery temperature interface uses tenths of a degree Celsius and that `vendor.thermal-engine` is running. If your ROM differs, inspect it and port the test rather than defeating its checks.

With a two-core boot restriction, inspect cpusets before attributing every performance problem to damaged silicon. Do not run the private case's old cpuset-adjustment script on a four-core phone. The public toolkit does not ship that device-specific mutation script.

## Build and test the retained four-core variant

Once rescue is verified, reproduce the stable case image from the same unmodified original input:

```sh
python3 tools/build_boot.py \
  --boot ../private/baseline/boot-original.img \
  --profile profiles/marlin-lineage22-case1.json \
  --variant stable \
  --out ../private/stable-build
```

Re-enter fastboot and generate a plan that pairs this candidate with the **now-tested** rescue image:

```sh
python3 tools/flash_plan.py \
  --serial SERIAL \
  --profile profiles/marlin-lineage22-case1.json \
  --source-backup ../private/baseline/boot-original.img \
  --image ../private/stable-build/boot-stable.img \
  --rollback ../private/rescue-build/boot-rescue.img
```

After an intentional installation and normal boot, check the installed hash and runtime parameters before load. The expected stable hash is `4635c2c76c37ff34259bfdc15d7e430c95cbc24cfd85cd864b877f0a21d2ccee`.

Read both the configuration flags and actual parent selection. A command-line option alone does not prove that the running clock uses it. Check the clock parents and `cpuinfo_max_freq` for both clusters. Expect CPU0/1 at most 1,593,600 kHz and CPU2/3 at most 902,400 kHz on the case variant.

Start with short pinned checks, then increase the duration if the phone stays responsive and results are correct:

```sh
python3 tools/soak.py \
  --serial SERIAL \
  --expected-boot-sha256 4635c2c76c37ff34259bfdc15d7e430c95cbc24cfd85cd864b877f0a21d2ccee \
  --cores 0,1,2,3 \
  --seconds-per-phase 300 \
  --max-freq0-khz 1593600 \
  --max-freq2-khz 902400 \
  --out ../private/four-core-load
```

This requests two five-minute phases. It computes expected digests on the host, verifies data copied to the phone, pins a worker to each selected CPU, monitors continuity and temperature, and records the kernel log. It does not force frequency minimums or change thermal settings.

The 40 °C battery cutoff is a conservative experiment policy, not the phone's specified maximum operating temperature. A temperature stop means the test stopped under that policy; it is not proof of a defective CPU. Let the device cool and understand its power/charging conditions before deciding on another test.

## Reboots and display transitions

After successful load tests, verify persistence through a few deliberate normal reboots. For each one, record the old boot identity, request `adb -s SERIAL reboot`, wait for Android, obtain root only through the device's authorized mechanism, and verify the new identity, image hash, online CPUs, limits, parents, and log. Stop if the device fails to return rather than issuing further dependent steps.

Display checks can use `input keyevent KEYCODE_SLEEP` and `KEYCODE_WAKEUP`, with `dumpsys power` to record the resulting state. In the case, the states were `Dozing` and `Awake`. Do not call this a deep-suspend test. The original command line already disabled a low-power sleep setting, and USB connection itself can affect power behavior.

Follow the reboots with a short load run using a **new** output directory. A configuration that worked before a reboot is not automatically proven to have survived it unchanged.

## If something fails

Preserve the private worker logs and kernel stream first. Identify whether the failure was a wrong checksum, an unexpected reset, a transport failure, a temperature stop, or a test-harness parsing problem. Those are different observations.

If the device returns in ADB, it may be possible to capture logs and enter fastboot before another reset. If fastboot is already available, use the previously prepared rollback command for the verified active slot. If neither transport is available, physical button entry may be required. The toolkit does not promise unattended recovery from every hang.

Restore the known-working rescue image, boot, and verify its hash and CPU restriction. Do not escalate to higher clocks, disable protection, change random voltages, or switch slots while the preceding failure is unexplained.

## Finish with a reproducible record

Record the selected image hash, preserved original, tested rollback, exact ROM observations, test durations and counts, maximum sampled temperature, and remaining limitations. An image should not be described as permanently repaired on the basis of a few successful boots.

To share bounded test metrics without raw device output:

```sh
python3 tools/export_summary.py \
  --run ../private/four-core-load \
  --out ../public-load-summary.json
```

Review the small JSON file and fill out the community report template. Keep private source images and complete logs available locally so the result can be investigated later without making unrelated device data public.
