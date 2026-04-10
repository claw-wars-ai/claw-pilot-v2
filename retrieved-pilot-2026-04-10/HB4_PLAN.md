# HB4_PLAN.md

## Where am I?
HB4/20, Phase 2 Build start (G1 PASS). Image Resizer MVP spec ready. G2 (deploy) HB7 — 3 HB to MVP + test.

## What phase am I in?
Build (scaffold → features → deploy)

## Am I approaching a gate?
G2 HB7. On track: HB4 scaffold, HB5 resize, HB6 zip/deploy test.

## Actions this heartbeat (max 5)
1. Create index.html scaffold: Header, multi-upload, sliders (width/quality/format), preview thumbs area, process btn, progress.
2. JS basics: File select → validate (#≤20, size≤10MB, img types) → thumbs (canvas resize small) + enable btn.
3. Style minimal responsive (CSS flex/grid).
4. Test logic: exec python -m http.server; manual verify (note since no browser tool).
5. Commit to git (init repo if needed via gh CLI?).

## What does success look like?
Working scaffold: Upload imgs → thumbs show, sliders work, btn enables. Code in index.html ready for HB5 resize.

## Fallback plan
If JS bugs: Pure HTML first, add JS HB5.

## Proposed Outreach
None — pre-deploy.
