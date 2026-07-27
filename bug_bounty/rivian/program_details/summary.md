---
company: Rivian
program: Rivian Bug Bounty
platform: Intigriti
program_url: https://intigriti.com/programs/rivian-bug-bounty (inferred)
---

OVERVIEW
========
Rivian designs, develops, and manufactures electric vehicles and accessories,
selling directly to consumers and commercial markets. This bug bounty program
is hosted on Intigriti with Safe Harbor protections.

BOUNTY TIERS
============
Tier 1 (Low $150 / Medium $700 / High $2,000 / Critical $5,000 / Exceptional $5,000)
Tier 2 (Low $100 / Medium $350 / High $1,500 / Critical $3,500 / Exceptional $3,500)
Bonus: $50 for verified fix, bonus for fast validation.

IN-SCOPE ASSETS
===============
Tier 1:
  - *.rivian.com (wildcard)
  - https://business.rivian.com/api
  - https://rivian.com/api/gql/content/graphql
  - https://rivian.com/api/gql/gateway/graphql
  - https://rivian.com/api/gql/orders/graphql

Tier 2:
  - 1570215232 (iOS app)
  - basecamp.rivian.com
  - com.rivian.android.consumer (Android app)
  - rivian.com
  - assets.rivian.com

OUT OF SCOPE
============
- careers.rivian.com
- demovehicles.rivian.com
- feedback.rivian.com
- internalshop.rivian.com
- media.rivian.com
- stories.rivian.com
- view.e.rivian.com
- cloud.e.rivian.com
- Third-party infrastructure and redirects
- Vehicle systems themselves (not in scope)

KEY RESTRICTIONS
================
- No DoS/DDoS
- No attacks requiring physical access
- No reporting without PoC
- No disclosure without prior written consent
- No vehicle remote control testing
- No spam, social engineering, or physical intrusion
- Must use @intigriti.me email for registration
- No account holders who are/currently Rivian employees (within 6 months)

REGISTERING
===========
1. Go to https://rivian.com/connect/tell-us-more
2. Provide name, phone, zip, valid email (use @intigriti.me)
3. https://rivian.com/auth/forgot → enter email → confirm
4. Create password → verify via OTP → account created

VALIDATION TIMES
================
Exceptional/Critical: 2 working days
High: 5 working days
Medium/Low: 15 working days

STATS (last 90 days)
====================
Submissions: 508
Accepted: 90
Average payout: $637
Total payouts: $61,775
Avg time first response: < 2 weeks
Avg time to triage: < 3 weeks
Avg time to decide: +3 weeks