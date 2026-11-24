# Governed Virtual Artist & System Identity

This design adds persistent, versioned technical identity to the SYNAPSE / NGOS-X
concept without treating software as a person. Identity revisions record parent
version, referenced experiences, reflection, changes, provenance and human
review. They are auditable records, not self-authorizing upgrades.

## Identity lifecycle

```text
Version N -> referenced experiences -> reflection -> proposed revision
         -> human review -> approved Version N+1
```

A revision is not approved merely because an agent proposes it. Keep prior
records immutable in the integrating application and link each revision to its
parent. Avoid storing private session contents; use consented, minimal references.

## NEON-ZERO profile

The sample profile is a fictional AI artist, clearly disclosed as AI, with an
original synthetic voice. Any voice resembling an identifiable person requires
separately verified permission and rights; the default profile does not authorize
imitation. Do not collect sensitive or personal audience data for targeting.

## Campaign planning boundary

`review_campaign()` validates a local plan and returns `review_ready` or `hold`.
It does not publish, contact users, scrape social posts, generate fake trends,
create fabricated conflict, or spend budget. `review_ready` means only that the
local policy checks passed; it is not permission to publish. A separately
reviewed human workflow must approve assets, rights, disclosure, schedule and
platform compliance.

Only first-party, aggregated, opt-in analytics may inform planning. Posting is
rate-limited by the plan schema and is never executed by this module. Prohibited
tactics include covert sentiment scraping, impersonation, fake beef, spam,
algorithm backdoors and emotional exploitation.

## CLI

```bash
synapse-ava-plan --out reports/ava_campaign_plan.json
```

The command writes a local governance manifest only. It makes no network calls.
