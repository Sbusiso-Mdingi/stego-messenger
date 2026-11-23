# Protocol: a `robust` method that survives WhatsApp photos

Draft 2, 23 November 2026, revised after a design review (`docs/robust_protocol_astra_review.md`). Written
before any `robust` code exists. Nothing below is frozen until the hash line for this file is recorded in
`docs/robust_protocol.sha1`; after that, changes go under Amendments at the end, each hashed the same way.

## Question

Can a sealed message (the existing format-3 blob: prefix, salt, AES-256-GCM token) be recovered exactly from an
image after it is sent as a standard-quality photo through the WhatsApp iPhone app, the harshest channel measured
so far, without damaging the image beyond a stated budget?

## The channel, as measured

From `data/channel/whatsapp/` (23 November 2026, ten PNGs per channel):

| | WhatsApp Web in Safari | WhatsApp iPhone app |
|---|---|---|
| Size | long side capped at 1,600 px | long side capped at 1,280 px |
| Re-encode | baseline JPEG, non-standard tables near quality 96 | progressive JPEG, standard libjpeg quality-75 tables |
| Chroma | 4:2:0 | 4:2:0 |
| Same input, same output | yes (one image sent twice) | not yet tested |

Those sends used PNG inputs; the method sends JPEGs, so development re-measures the channel with real stego
JPEGs. **The channel** means the whole route: Mac → AirDrop → iPhone Photos → WhatsApp iPhone app, standard
quality, to the user's own chat → save to Photos → AirDrop → Mac. Every send records the iPhone model, iOS
version and WhatsApp version. Android, HD mode and other apps are not measured and nothing here claims
anything about them.

## Method (all choices fixed here except `Z`, `k` and `m`)

1. **Pre-shape the cover.** If the long side is over 1,280 px, resize to a 1,280 px long side (Pillow Lanczos),
   then crop centrally to whole multiples of 16 px. Encode as a baseline JPEG with the standard quality-75
   tables and 4:2:0 subsampling through `jpeglib`, with the libjpeg version pinned.
2. **Positions.** Luma quantised AC coefficients at zigzag indices 1 to `Z` in every 8×8 block, ordered by a
   permutation seeded with the existing `position_key(password)`.
3. **Header.** The coded payload length as 4 bytes, each bit written 7 times at the first positions of the
   permutation and read by majority vote.
4. **Error correction.** The blob is split into Reed-Solomon RS(255, `m`) codewords (`reedsolo`), the last one
   shortened, and the codeword bytes interleaved round-robin over the permutation after the header.
5. **QIM.** With an even step `k` on the quantised (whole-number) coefficient, bit 0 moves the coefficient to the
   nearest multiple of `k` and bit 1 to the nearest multiple of `k` plus `k/2`. Ties go to the value nearer zero.
   Extraction reads the nearest point.
6. **One decode path.** The decoder sees only the received image, the password and the frozen configuration. It
   never sees the expected message or its length. There are no fallbacks or retries; the result is either a
   message that AES-GCM verifies or a failure. Expected bytes are compared only afterwards.
7. **Capacity** is the largest blob that fits after the header and all Reed-Solomon parity, per cover.

## Image-quality budget

Measured on luma (BT.601 Y), the decoded stego JPEG against the decoded pre-shaped cover, at the same size:
**PSNR at least 36 dB and SSIM at least 0.97** (scikit-image defaults, data range 255), per cover. The cost of
pre-shaping (the pre-shaped cover against the lossless resized and cropped original) is reported but not
budgeted.

## Development (allowed before the freeze)

- **Development images:** the ten channel images in `data/channel/whatsapp/sent/`, and nothing else.
  Neither development nor simulation may touch the test pool.
- **Candidate grid:** `Z` in {5, 9, 14, 20}, `k` in {2, 4, 6}, `m` in {223, 191, 159, 127}: 48 candidates.
- **Simulated channel:** decode the stego JPEG to pixels and re-encode it with libjpeg at the standard
  quality-75 tables and 4:2:0. It is a stand-in only, since the iPhone uses Apple's encoder.
- **Simulation suite, the same for every candidate:** each development image × 5 seeds (20261123 to 20261127)
  for password and message, with a 140-byte message (192-byte blob): 50 trials per candidate.
- **Selection rule:** among candidates that recover all 50 simulated trials and meet the quality budget on all
  ten images, take the smallest `k`, then the smallest `Z`, then the largest `m`. If none qualify, the method
  fails at development and this is reported.
- **Real confirmation:** the selected candidate, the ten development images with seed 20261123, sent through
  the channel, plus one image sent twice to test repeatability (11 sends). Confirmation passes if all ten
  recover. If it fails, the next candidate in the same order is confirmed the same way, for at most **three**
  confirmations in total (33 real sends). Every confirmation result is kept and reported.
- **Unit tests,** not part of the pass rule: the header and Reed-Solomon framing round-trip for blob lengths
  from the minimum up to capacity, in the simulated channel.

## Freeze

Before any test cover is sealed, an amendment records: the chosen `Z`, `k` and `m`; the commit of the
`robust` code; a lock of every dependency version; the test pool and the draw below. Its hash line goes into
`docs/robust_protocol.sha1`. Nothing is tuned after that.

## Test (one attempt)

- **Pool:** the user's own iPhone photos. The user picks a date range and AirDrops every photo taken in it, at
  least 60, as originals (HEIC or JPEG). They do not pick individual photos. SHA-1s of the received files are
  recorded on arrival, before any file is decoded. The photos stay in `data/test_pool/`, which is never
  committed; location data is never read or kept. No photo in the pool is used in development.
- **Preparation:** HEIC files are decoded with macOS `sips` to 8-bit sRGB PNG, then Exif orientation is
  applied. A script excludes photos with a long side under 1,280 px, files without a camera model in Exif
  (screenshots and saved images), and near-duplicates (difference hash, 64 bits, Hamming distance 6 or less;
  the earliest is kept). Exclusions are listed by SHA-1 in the freeze amendment.
- **Draw:** 30 covers, drawn with seed 20261201 as 15 smooth and 15 textured. Smooth and textured are split at
  the pool median of mean luma gradient magnitude on the pre-shaped cover.
- **Messages:** one per cover, 140 bytes of UTF-8 text from seed 20261201 (192-byte blob). The claim is in
  bytes, not characters. A cover whose capacity is under 192 bytes counts as a failure.
- **Sends:** each stego image is sent once through the channel. No resends; every result is recorded, including
  transfer mistakes.

### Pass rule

`robust` **passes** if **at least 28 of 30** messages are recovered exactly through the iPhone app **and**
every recovered cover meets the image-quality budget.

28 of 30 is the smallest count whose one-sided 95% Clopper-Pearson lower bound is at least 80%, so a pass
supports the statement "at least 80% of such sends recover, with 95% confidence", for this channel. Fewer than
28 is a fail and is reported as it is. A later attempt needs a new protocol version, new parameters if any,
and a new draw from a pool not used before. Every attempt, passed or failed, stays in the main report.

### Description only (not part of the pass rule)

- The same 30 stego images sent through WhatsApp Web in Safari: recovered count.
- **Bit error rate before error correction:** coded bits read at the frozen positions against the bits
  embedded, over all coded bits of every cover, including covers whose decode failed. Header errors are
  reported separately.
- Capacity per cover in blob bytes and in plaintext bytes (blob minus the 52-byte format-3 overhead), and the
  share of embedded bits that is Reed-Solomon parity or header.
- PSNR and SSIM as defined above, and the pre-shaping cost, for every cover.
- The existing chi-square, RS and HCF detectors on the stego images and on the pre-shaped covers. These are
  pixel-domain detectors built for LSB methods, so a quiet result says little about JPEG-domain embedding. A
  JPEG-domain detector is a separate, later task.

## What a pass would and would not mean

A pass means 140-byte messages survive standard-quality photos through the WhatsApp iPhone app, on the recorded
device and versions in December 2026, within the quality budget. It says nothing about Android, HD mode, other
apps, later WhatsApp versions or undetectability. The README and web preview would say exactly that.

## Dependencies

`jpeglib` (MPL-2.0) and `reedsolo` (Unlicense or MIT-0), used as libraries without changes to their files. The
project stays Apache-2.0.

## Amendments

None yet.
