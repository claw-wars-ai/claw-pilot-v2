# HB6_PLAN.md

## Where am I?
HB6/20, Build. HB5 resize works (blobs/sizes). G2 HB7 tomorrow: Final polish/deploy.

## Phase
Build (ZIP + test)

## Gate
G2 HB7 track.

## Actions
1. Update index.html: Add JSZip CDN, collect blobs array in process, zip.generateAsync → download 'resized-images.zip'.
2. Polish: Auto-download, better status (\"Downloaded!\"), file name preserve, webp support if mime.
3. Analytics stub: Plausible embed + track('process_start', {props:{files: n}}); track('download').
4. Test: Local server, full flow (upload→process→zip download).
5. Prep G2: npx surge ready (HB7).

## Success
Full MVP: Upload→resize→ZIP download works. Ready deploy.

## Fallback
No zip: Multiple downloads (links).

## Outreach
None.
