## t24u (2026-11-23 ET) — approved 8 alleys + protected rear lanes

| view | baseline IoU | actual IoU | delta |
|---|---:|---:|---:|
| south | 0.8076 | 0.8002 | -0.0074 |
| north | 0.8116 | 0.7967 | -0.0149 |
| west | 0.7404 | 0.7356 | -0.0048 |
| east | 0.7477 | 0.7434 | -0.0043 |
| top | 0.9420 | 0.9136 | -0.0284 |

Measured fresh baseline/new saved Blend, same0.1m/px calibration. Top footprint .8521→.8240; outline1.186→1.723m. Main plinth widened±31.35→±33.15, 8 net>=1.4m alleys, full11m house depth retained. Actual optimized GLB minimum including finish/quantization1.403997m. Detailed geometry, full-window and negative evidence: docs/superpowers/t24u-validation.md. No calibration, original textures or runtime JS/HTML changes; no deployment.
