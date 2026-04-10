# HB5_PLAN.md

## Where am I?
HB5/20, Build. HB4 scaffold solid (upload/thumbs). G2 HB7: 2 HB left (resize HB5, zip HB6, deploy HB7).

## What phase?
Build (core logic)

## Gate?
G2 HB7 on track.

## Actions
1. Edit index.html: Add resize/compress in processAll() (canvas scale to maxw, toBlob quality/format).
2. JS: Async loop files → img load → canvas draw/resize → blob (log orig/new sizes), progress update.
3. Test: Local server (existing), simulate process (console sizes reduce).
4. Prep HB6: Note JSZip CDN for zip.
5. Update RESOURCES progress.

## Success
Process works: Blobs generated, sizes down, progress animates. Core resize ready for zip.

## Fallback
Native only (no extra lib), sequential process.

## Outreach
None.
