# Contributing observations and improvements

The most useful contribution is a precise, reproducible report, including a failed reproduction. Use [the device report template](templates/DEVICE-REPORT.md). Begin with the original image hash and observed device identity, then describe changes, measurements, and limitations.

## Reports

Keep raw diagnostics and original boot images private. Review a public numerical export and selected log excerpts before sharing. Remove device serials, IMEI/MEID values, account names, network identifiers, boot UUIDs, local usernames and paths, and unrelated application traces. Do not post a whole pstore directory or bugreport merely because one PLL line is relevant.

Record whether the supplied public tools actually ran on hardware or only on simulated transport. Identify temperatures by sensor and units. Distinguish normal reboots from cold starts, display changes from deep suspend, and arithmetic success from overall hardware health. Give exact durations and checks rather than “stable for a while.”

For failures, preserve the initial result and classify the evidence: checksum mismatch, reset, missing transport, temperature policy stop, image mismatch, or harness problem. If a detector was wrong, retain the original result and explain the review. Do not silently change a failed report into a pass.

## Code and profiles

Run the host tests described in [Tools](docs/TOOLS.md). Changes to boot parsing, transformations, or refusal behavior need focused tests. Profiles for additional images need the source hash, layout evidence, field-location method, independent structural checks, output hashes, recovery plan, and actual device results when available.

Do not weaken an input hash gate to make an unsupported image pass. Do not introduce automatic unlocking, wiping, relocking, slot changes, or hidden thermal/frequency mutations. Keep device effects explicit in both the CLI and documentation. Flash planning must remain separate from execution unless a later reviewed design deliberately changes that contract.

Avoid hard-coded private serials or host paths. Use explicit device selection and unique local output directories. New evidence should be selected or allowlisted for publication, not copied wholesale from a private run.

## Attribution and release state

Document upstream sources without implying endorsement or exact compiled-image provenance that has not been established. Preserve license notices. This package distributes newly written tools/docs and selected case evidence; it does not distribute firmware binaries.

The project repository is [westman2000/pixel-xl-recovery](https://github.com/westman2000/pixel-xl-recovery). Submit a reviewed report through [the device-report issue template](https://github.com/westman2000/pixel-xl-recovery/issues/new/choose), or open an issue describing a tool problem. Code improvements can be proposed in a pull request. Do not attach private source images or complete raw collections.
