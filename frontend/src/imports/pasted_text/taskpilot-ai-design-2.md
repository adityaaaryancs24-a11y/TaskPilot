Design a clean, modern desktop web app called "TaskPilot AI" — a personal AI task intelligence assistant for software engineers. This must NOT look like Jira, Linear, or a generic indigo/blue SaaS dashboard. Visual identity:

- Background: near-black (#0E1411), not pure black
- Surface cards: slightly lifted dark panel (#161D19) with hairline borders (#232B26), 10-12px rounded corners
- Signature accent color: sage/seafoam green (#8FCBA8) — used ONLY for the brand mark, AI-generated reasoning text, primary CTAs, and active nav states. Do not use it decoratively elsewhere.
- Priority/status tags use their own semantic colors at low opacity (15% bg, full-saturation text): red-coral for P0/critical, amber for P1/high, green for P2/low — these stay visually distinct from the sage brand accent so "AI insight" and "status" never get confused
- Logo mark: small rounded-square icon, dark green gradient fill, sparkle symbol in sage green, paired with "TaskPilot AI" wordmark in clean sans-serif (Inter), medium weight
- Typography: Inter, sentence case everywhere, generous line-height, soft muted gray-green for secondary text (#8B9890), near-white for primary text (#EDF3EF) — never pure white
- Every AI-generated insight, rationale, or "why this rank" explanation is marked with a small sage sparkle icon and sage-tinted text, so AI reasoning is always visually distinguishable from raw source data and from status tags
- Overall feel: calm, premium, focused — like a thoughtfully designed personal AI tool (closer to Linear/Arc/Raycast in mood), not an enterprise admin panel

Generate these 6 screens:

SCREEN 0 — Morning Greeting / Entry Screen (this is the FIRST screen the user sees, before the dashboard)
- Full-bleed near-black background, centered content, very minimal
- A few small faint sage dots scattered subtly in the background suggesting gentle ambient motion/particles — calm, not busy
- Small sparkle logo mark centered near top, with a soft dark-green gradient glow behind it
- Small muted date line above the greeting (e.g. "Friday, June 19")
- Large centered headline: "Good morning, Alex"
- One supporting line beneath in muted gray-green: a short summary like "Your day is mapped across 5 sources. 3 things needed your attention overnight."
- Single centered pill-shaped CTA button in solid sage green with dark text: "Start your day" with a small arrow icon — this is the only button on the screen
- Nothing else on this screen — no nav, no sidebar, no clutter. It should feel like a quiet, intentional opening moment before the tool reveals itself

SCREEN 1 — Daily Plan Dashboard (after clicking "Start your day")
- Top header: small sage logo mark + "TaskPilot AI" wordmark, top right shows a sage-tinted pill badge "Plan generated in 42s"
- Greeting: "Good morning, Alex" with subtext "3 hidden tasks found today across 5 sources"
- Left sidebar nav on near-black background: Daily Plan, All Tasks, Sources, Chat Assistant, Weekly Summary, Settings — sage highlight and left accent bar on the active item
- "Your Top 3 Priorities Today" — lifted dark cards with hairline borders, each showing: task title, source tag, semantic priority pill, and below a thin divider a sage sparkle-icon line with the plain-English rationale ("P0 severity + VP escalation + SLA expires in 18h")
- Below: "Rest of Today" — compact dark-card list with checkboxes, source tags, due times
- Right-side panel: "Proactive Alerts" — sage-tinted icon circles next to each alert, quiet card style, not loud red alarm banners
- Small stat strip: "5 sources synced", "3 hidden tasks found today", "Last sync: 2 min ago"

SCREEN 2 — Unified Task View (all tasks)
- Same dark sidebar
- Filter bar: source, priority, deadline — pill-style dropdown filters
- Dark card rows for each task: title, source badge, semantic priority pill, deadline, status pill
- At least 2 rows show a small sage "merged from 2 sources" tag with sparkle icon to indicate AI deduplication
- One row expanded showing merged sources side by side (original Jira ticket + matched email snippet) with a sage "92% match confidence" tag and a "View reasoning" link in sage

SCREEN 3 — Conversational AI Chat Assistant
- Chat layout on near-black background
- AI messages have the small sage sparkle avatar; AI text sits in a subtly sage-tinted dark card, not a generic gray bubble
- One exchange: "Why is the upload bug my #1 priority?" answered with structured bullet reasoning referencing the real source ticket
- Second exchange: "Summarize the VP's email" answered with a short structured summary card
- Input bar with sage-accented send button, suggested quick-prompt chips in soft sage-tinted pills

SCREEN 4 — Source Ingestion / Extraction View
- 4 connected source cards (Jira, ServiceNow, Outlook, Meeting Transcripts), dark cards with small sync-status dot and "last ingested" timestamp
- Below: side-by-side "extraction in progress" panel — raw email snippet on the left in a plain neutral dark card, and on the right a structured task card with a sage sparkle badge showing it was AI-extracted, fields (Title, Priority, Deadline, Confidence Score, "Trace to source" link)
- A soft sage banner: "Hidden action items found today: 3"

SCREEN 5 — Weekly Summary / Standup Report
- Week range header
- Metric cards in slightly lifted dark surfaces: Tasks Completed, In Progress, Deferred, Hidden Tasks Surfaced
- Simple horizontal bar/timeline chart of weekly completion, sage as the primary data color
- "Standup-ready summary" card with a "Copy" button
- Blockers section with avatar circles and quiet status pills

General requirements across all screens:
- Every priority or ranking decision visibly shows its reasoning via the sage-sparkle rationale pattern — consistent everywhere, this is the signature interaction of the product
- Consistent near-black sidebar and background across all app screens (Screens 1-5) — Screen 0 stands alone as a distinct calm entry moment
- Consistent left sidebar navigation on Screens 1-5
- Realistic placeholder data referencing Jira, ServiceNow, Outlook, Slack, GitHub Issues, and meeting transcripts as sources
- High information density but never cramped — generous padding inside cards
- The product should feel calm, focused, and premium — avoid anything resembling a ticket-tracker or admin panel