---
kind: milestone
title: Ship guarded API
target: v2 launch gate
---
The public API refuses abusive traffic without hurting honest clients. Done
means the limiter is on every authenticated route, documented, and load-tested
at twice expected peak.
