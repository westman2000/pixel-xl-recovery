# Maintainer handoff

This file records the state of the prepared public package so work can resume without reconstructing the conversation. It contains no private device identifier or host path.

## Completed

- English case study, recovery runbook, implementation details, validation methodology, tool reference, research plan, references, contribution guide, device report template, and prepared announcement.
- Strict offline builder for the single recorded original hash, producing both the rescue and retained E08 images byte-for-byte.
- Private diagnostic collector, plan-only fastboot helper, bounded correctness workload, numerical workload source, and allowlist exporter.
- Sanitized evidence, host tests, offline HTML reader, and a portable local release archive.

## Last established phone configuration

- Product: `marlin`, Pixel XL; observed LineageOS 22.2 / Android 15, kernel 4.4.302+.
- Retained image: E08, SHA-256 `4635c2c76c37ff34259bfdc15d7e430c95cbc24cfd85cd864b877f0a21d2ccee`.
- All four CPUs, alternate PLL parents, ACD disabled, corrected divide-by-one settings.
- CPU0/1 capped at 1,593,600 kHz; CPU2/3 capped at 902,400 kHz.
- Tested rescue SHA-256 `7c6f9d632f45f5b5000e541cef5ae17b48b496e6d9135e5058578da0748cd8e8`.
- Original SHA-256 `26d5c3e57bfcdd3b45f9d66e4ec7224cfca5ac43a003ff433f19288bd63bcf4c`.
- Only boot_a was flashed during the recorded case. Current state must be re-read before any future write; do not infer it from this historical note.

No phone mutation occurred during public-package preparation. A packaging collection attempt found no ADB device. Therefore the public ADB wrappers still need real-device validation, although the original private hardware campaign passed the bounded tests documented here.

## Resume procedure

Read README, the case study, and the research plan. Check the package hashes and host tests before modifying tools. If reconnecting a phone, identify it and collect a new private baseline first. Compare the installed image/slot/build with the historical state rather than assuming the phone has remained unchanged.

Keep the owner's original images and full laboratory logs private and outside this project. Use a new local run directory for every operation. If a result is corrected after review, preserve the earlier result and record why.

The next useful technical step is a short hardware check of the public collector and soak wrapper on an already-established configuration. Further clock-path experiments and higher frequencies are future research, not pending automatic actions.

## Publication state

The owner selected the public repository [westman2000/pixel-xl-recovery](https://github.com/westman2000/pixel-xl-recovery) for publication. The repository is the maintained source; [GitHub Releases](https://github.com/westman2000/pixel-xl-recovery/releases) provides downloadable packages. No forum post, message to another person, or upstream repair claim is part of this release.

The reading website is [westman2000.github.io/pixel-xl-recovery](https://westman2000.github.io/pixel-xl-recovery/). GitHub Pages serves the root of `main`; regenerate `index.html` with `python3 tools/render_docs.py --site` whenever its Markdown sources change. Regenerate `READ-ME.html` without `--site` for the offline copy, then update the file hashes.

Public CI checks the host tests, generated reader, and file hashes. The private-image reconstruction test is intentionally skipped there; the original case input remains private. Public ADB wrapper hardware validation remains the next technical task.
