# Pixel XL clock-path investigation report

Replace the placeholders with observations. Leave unknown fields as “unknown.” Keep the original private collection locally; do not attach it unreviewed.

## Scope and identification

- Report date and time basis:
- Owner consent and data-preservation constraints:
- Product/codename (no serial):
- ROM property and Android release:
- Kernel release:
- ROM/source provenance, if established:
- Bootloader version and already-unlocked state:
- Active slot at backup and at each installation:
- Original boot SHA-256 and byte size:
- Available transports and modes:
- Public toolkit version / host OS / Python / ADB / fastboot / LZ4 versions:

## Original symptom and evidence

Describe the visible failure and how long it took. State whether recovery booted, which CPUs were available there, and whether the preserved log belongs to the failing boot.

- Relevant log excerpt, with timestamps and private identifiers removed:
- Matching warning count within the captured buffer:
- Conclusive panic or reset reason, if actually captured:
- Other plausible software/hardware explanations:
- Battery temperature sensor, units, and power/charging conditions:

## Experiment record

| ID | Input hash | Changes | Output/installed hash | Boot result | CPUs/parents/measured clocks | Workload result | Rollback result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | | None | | | | | |
| Rescue | | | | | | | |
| Candidate | | | | | | | |

Distinguish the first rescue candidate from a rescue image already tested on this device. Record any UI, cpuset, application, charging, or background-work changes that could affect performance comparisons.

## Validation

- Public tools used on real hardware, private harness, or simulation:
- Correctness algorithm(s), input size, and host reference method:
- Per-core iterations and total checks:
- Requested load time and observed harness duration:
- Boot continuity and online CPUs:
- Reported rates versus independently measured clocks under load:
- Maximum sampled battery temperature and thermal-service status:
- New PLL messages or critical kernel candidates:
- Reboots, cold starts, display transitions, and actual suspend tests (separate counts):
- Cleanup verified:
- Any detector false positive, preserved original result, and review explanation:

Attach the reviewed public summary JSON if applicable. A temperature stop, disconnected cable, wrong image, and arithmetic mismatch are different outcomes; describe which one occurred.

## Conclusion and limits

- Retained configuration and hash:
- Tested fallback and hash:
- Observation supported by this report:
- Hypothesis that remains unproven:
- Unperformed tests / unresolved issues:
- Next proposed experiment and what question it would answer:

## Publication review

Confirm manually that shared material contains no serial/IMEI, account data, network identifiers, boot UUIDs, private host paths, full unreviewed logs, or firmware binaries. Include only information necessary to reproduce or interpret the result.
