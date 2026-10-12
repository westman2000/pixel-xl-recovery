# Changelog

## 0.1.0 — initial public release, 2026-10-12

- Documented the single-device recovery sequence, including E02's failure, the alternate-clock half-frequency finding, the divider correction, and retained E08 validation.
- Added a strict profile for one original boot hash and exact offline reproduction of rescue and retained four-core images.
- Added private collection, plan-only flash validation, bounded correctness load, allowlist export, and the original floating-point workload source.
- Preserved sanitized numerical evidence, source-reference hashes, and the reviewed ramoops detector false alarm.
- Added host tests, recovery/rollback instructions, validation methodology, a research/porting plan, and a community report template.
- Added a GitHub device-report template and host CI for Python 3.9 and 3.12. The real-image test remains private and is skipped in public CI.
- Added a responsive [GitHub Pages reading site](https://westman2000.github.io/pixel-xl-recovery/) with chapter navigation, code blocks, evidence links, and toolkit downloads, generated from the same Markdown as the offline reader.
- Published the prepared source and downloadable package at [westman2000/pixel-xl-recovery](https://github.com/westman2000/pixel-xl-recovery). Public ADB wrapper hardware validation remains pending.
