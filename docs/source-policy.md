# Viewing-source policy

RamanPlay distinguishes official provider sources from personally saved My Links.

## Official sources

Official or curated sources must use a trusted public HTTPS domain and include game- or event-specific evidence. They may be labeled `FREE_LEGAL`, `FREE TRIAL`, `SUBSCRIPTION`, `OFFICIAL`, `AUDIO ONLY`, or `UNAVAILABLE` only when the supplied evidence supports that label. A successful link check proves HTTP reachability, not broadcast rights, playback, regional availability, or eligibility.

## My Links

A user may save any public HTTPS link that passes URL and SSRF validation. RamanPlay records one of these trust states:

- **VERIFIED** — trusted provider domain.
- **UNVERIFIED** — public HTTPS destination supplied by the user; it requires confirmation before external navigation.
- **WARNING** — suspicious redirect behavior or another warning condition.
- **BLOCKED** — unsafe scheme, credentials, private or local address, blocked domain, malformed URL, or unsafe redirect destination.

My Links are attached only to the selected NFL/NBA game or UFC event. They are never discovered automatically or shared with another event by default.

## Safety and playback boundaries

The link checker validates every redirect, rejects private/internal destinations, limits redirects, honors blocked domains, uses TLS-verified public connections, and does not store response bodies. Only user-authorized direct-media URLs that pass the existing checks can use RamanPlay’s native video element. External webpages are opened separately and are never embedded in an iframe, object, or embed.

RamanPlay does not hunt for streams, scrape hidden media URLs, remove provider ads, proxy or rehost media, bypass paywalls, subscriptions, authentication, DRM, CAPTCHAs, geo restrictions, or other access controls.
