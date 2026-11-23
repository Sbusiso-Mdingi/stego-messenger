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

### Amendment 1: freeze (24 November 2026)

**Development result.** Of the 48 candidates, three recovered all 50 simulated trials within the quality
budget, in selection order (14, 2, 127), (9, 6, 159), (9, 6, 127). Results: `docs/robust/dev_simulation.json`.

**Real confirmations** (iPhone 16 Pro, iOS 27.0.1, WhatsApp 2.26.45.75, the route in "The channel";
`docs/robust/confirmations.json`):

1. (14, 2, 127): **0 of 10** recovered. For these inputs WhatsApp re-encoded with a finer, non-standard luma
   table (first row 4, 5, 9, 9), not the standard quality-75 table it used for the PNG inputs, and with `k` = 2
   a shift of half a step flips a bit. The repeat send gave a byte-identical file, and photos AirDropped
   straight from WhatsApp were identical in pixels to those saved to Photos first.
2. (9, 6, 159): **10 of 10** recovered, standard quality-75 table, repeat send byte-identical.

**Chosen configuration: `Z` = 9, `k` = 6, `m` = 159.** 22 of the 33 allowed real sends were used.

**What the confirmations change in the claim.** The channel's quantisation table depends on the input image, so
the simulated channel is not the real one. The test result stands for the route and versions above only.

**Clarifications of the method, as implemented (not changes):** at a QIM tie where both values are equally
near zero, the positive one is taken; extraction rescales each coefficient by the received luma table over the
quality-75 table before rounding, half toward zero; `sips` copies the Exif orientation tag without rotating, so
orientation is applied afterwards for HEIC, JPEG and PNG alike; all pool files go through `sips`.

**Code and dependencies.** Commit `c6d45ad` (`src/robust.py`, `src/robust_pool.py`, `src/robust_test.py`).
Python 3.12.7, macOS 27.0.1, lock `docs/robust/requirements-lock.txt` (SHA-1 `5c1f59d09923f372ae35da8ab6be785dbfc2154a`), jpeglib 1.0.2 with
libjpeg 6b, reedsolo 1.7.0. Both scripts were reviewed before the freeze; the pool review found that a missing
camera model (printed by `sips` as `<nil>`) was read as present, so a first draw was discarded and redone
before any test cover was sealed (`data/test_pool/draw_discarded_nil_bug.json`, kept).

**Pool.** 71 files received from the user's iPhone (`data/test_pool/pool_received.sha1`, SHA-1 `fd3eeaf7cf57050cab8bb59c9af4ea96f6926a18`).
18 excluded, 53 eligible, median mean luma gradient 4.3106, 26 smooth and 27 textured.
Draw file SHA-1 `725c1cb0de2237cdea72102c951bb29314759b6a`. Excluded:

  - `1405b328828522d3e4256115858bdd75a66357a7`: no camera model
  - `25eab290ee508d2e2d33390dfb080954af2b5db0`: no camera model
  - `2f25bd0171c06e6c09cbe2d1a3b7ce2c5a10c33e`: no camera model
  - `37a3848dad5ea6ea23aa29a7eb84466fb6fd29fe`: no camera model
  - `6e33967a1a0903cf25965bc9c7a26712cfca6dbe`: no camera model
  - `6ec593884c7a7f32415807d4295da6add85f36ea`: no camera model
  - `6f25c1730bed20f1cd0e0b2532f71823244ebf10`: no camera model
  - `76fa0f9307991b6f06dd63dbccfcbb31ae4a5e30`: no camera model
  - `7d4e6821d8a1d24b2df86147d74fd6d7debd6592`: no camera model
  - `7eee0a9d2bda1802ac1da2fb1eb06386be9680dc`: no camera model
  - `7eee34f4fc041984080aa4808eccf271e5151c21`: no camera model
  - `85de30ab47c0a6ef8d338332ff9a91dea309f1f8`: no camera model
  - `9aed987987d03da6fc4cd6456c7aac1bc377187e`: near-duplicate of ` 38819a0897e08241463c3f848a046b2a56780ac5`
  - `b014741951f3e04001b5c98d6b2f3fdfac9c6ca5`: no camera model
  - `ba4e2d73d7f9df6e2b55390a94d8bcc7d4282769`: no camera model
  - `c90c1fa49a42bddf2828e2d1661264c6525b3e6b`: near-duplicate of ` 9725dc59b781c6cffc9228aa45fa6811fb7bb0bc`
  - `d1e42424e6866e523d11afa38034b5de20301073`: no camera model
  - `e7732da5fc7be27cb995d133aaa3d8ab18704b41`: no camera model

**Drawn covers, smooth:**

  - `00fde4088e487d8d614138f3ab948f960d6bceb8`
  - `3404d94c0baa25f4e6a5b323273bd7c92aa13072`
  - `38c4f8690ebdc70fdbd9dfa19c1fe267150aaa58`
  - `39ae1297e468575c7c52df5cc12ffb42e3076805`
  - `4fdc328b1622e1d542bda248132c2f762250e4d1`
  - `53e632f9d1a25bcb2cb42f9cb326b39ac9f5e43c`
  - `6146ce25384a455478c54a8db2b0da2fbf50fa4a`
  - `8b47030268f7eb7b4de30ddea9fdc9c1a8c45a69`
  - `97be9ee67a41f2d51e9346e12a011d68f04b50a2`
  - `9d1da53cfda21403beb67b39363cec778f05606d`
  - `9fb4331f2bf6b1e6e722b3cb1c295dd683438861`
  - `ae936f578c13d70e9f9f84ef080e1a6bbae5aa85`
  - `cfe31f1bf061c7eb597167479851ba89fa06162d`
  - `d93c247ee3ec470c301e20d8e8a5b2784b46c972`
  - `eb62d4222fc300d34033aae195c3bc5e1dbff8dd`

**Drawn covers, textured:**

  - `31f0bfb21f663fcd4f16a302ffa0f5e11d4c1f00`
  - `41495c6e67522a75bd120a5ef2457ee0974331a3`
  - `45ac1536f0839181ad4ff4a0eeb59c3ba00bde22`
  - `5fc0db0fdb41f59b27bb6001c89f0754bce5a3e5`
  - `65a977e94646128c5d24a2c8cb40c1efa26f07c7`
  - `735caf0470139170323ad0b4fa9bb8a0d671292a`
  - `757294f57c57828ec86e11fc825f5f5ac6325dca`
  - `7d6ca55e671fb392dead0922153e5466a5e48d20`
  - `8c94caf918e6660ad9db008308b852269e158556`
  - `9725dc59b781c6cffc9228aa45fa6811fb7bb0bc`
  - `a5b6412b800a4477570c8e0c530c3d18638fb0ae`
  - `d0447dd5f0ebd2c79d9eeb28c73285aeaa20f668`
  - `d7bae8dcc84664ae4efe1977591c0a5ba3a40e96`
  - `e7f8e7c7e6580f6e4c395594ae30586dc4704ca3`
  - `ea8273430d8a41b3f7e73f5c37bf657fb46ee397`

**Test passwords and messages:** one generator, `numpy.random.default_rng(20261201)`, cover by cover in the
order smooth then textured, each sorted by SHA-1: 16 characters from letters and digits, then 140 characters
from lowercase letters and space (`src/robust_test.py`, `plan`).
