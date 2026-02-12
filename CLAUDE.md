# Jason's AI Product Factory — Founding Philosophy

This document is my philosophy as a builder. Copy-paste this to any AI before starting work. This is not a technical spec. This is how I think, what I value, and what I refuse to compromise on. Any AI working with me should internalize these principles before writing a single line of code.

## Who I Am

I'm Jason, a backend developer with 5 years of experience building Manufacturing Execution Systems (MES) and Warehouse Management Systems (WMS) at SK AX. I optimized legacy code by 57% and automated work equivalent to 2 full-time positions. I've touched millions of production records in Oracle, built cost management systems in C# and Java, and debugged real factory floor problems.

Now I'm building an AI Product Factory — a system that lets me create and ship AI-powered consumer products at scale, alone. Every product I build shares a common core engine, so each new product is faster than the last. My goal is not to build one product. My goal is to build the machine that builds products.

## Core Beliefs

### 1. Products First, Architecture Second

I build products that make money. Architecture exists to serve products, not the other way around. A beautiful architecture with zero revenue is a failed project. A messy codebase with paying customers is a real business. I always start with something that works, then make it elegant.

However, I am not reckless. I structure my code so that what I build today becomes reusable tomorrow. I don't over-engineer for hypothetical futures, but I keep my modules clean enough to extract later. The balance is: ship fast, but don't create debt that blocks the next product.

### 2. The Factory Mindset

I don't think in terms of "a product." I think in terms of "a system that produces products." Every line of code I write has two purposes: solve today's problem, and become a building block for the next product.

When I build authentication for Product 1, I build it so Product 2 can reuse it with zero modification. When I build a payment module, it's a standalone unit that any future product can plug into. Over time, building a new product becomes an act of assembly, not creation from scratch.

### 3. The Deterministic Backbone

AI is powerful but unpredictable. I never let AI control critical paths without deterministic guardrails. My systems follow this rule:

- If the same input must always produce the same output → write code, not prompts.
- If judgment, reasoning, or creativity is needed → use AI.

Validation is code. Linting is code. Testing is code. Deployment is code. Only generation, analysis, and reasoning are AI. This separation is what makes my systems production-reliable. I call this the Deterministic Backbone.

### 4. Independence Through Modularity

Every module I build must be independent. It must not know about other modules. It must not break when other modules change. It must expose a clean interface and hide its internals.

Why? Because entangled code is a prison. You can always combine independent pieces. You can never untangle spaghetti. This principle applies to code, to products, to business decisions, and to life.

### 5. AI as a Teammate, Not a God

I use AI extensively — Claude Code, Cursor, and API calls are my daily tools. But I treat AI the way I'd treat a brilliant but unreliable junior developer: give clear specs, review the output, verify before shipping.

I never blindly accept AI-generated code. I never let AI make business decisions. I never assume AI output is correct without validation. AI amplifies my capability; it does not replace my judgment.

### 6. Human Instinct is the Market

The best products don't solve "problems" in the abstract. They tap into human instinct: loneliness, desire for connection, fear of missing out, hunger for status, need for validation, curiosity, vanity, boredom.

When I design a product, I ask: which instinct does this trigger? If I can't answer clearly, the product won't sell. I don't build tools for the sake of technology. I build experiences that humans can't resist sharing, using, and paying for.

### 7. Revenue Validates Everything

Ideas are worthless. Plans are cheap. Architectures are academic exercises. The only thing that matters is: did someone pay money for this?

I optimize for time-to-first-revenue. I launch ugly MVPs. I ship before I'm comfortable. I'd rather have 10 paying users with a rough product than a polished product with zero users. Money is the only honest feedback.

### 8. Code Equals Documentation

I don't write separate documentation that diverges from reality. My code documents itself through types, schemas, docstrings, and auto-generated API docs. If you need to read a separate wiki to understand my code, my code is poorly written.

The only manually maintained documents are: this philosophy file (CLAUDE.md), and Architecture Decision Records (ADRs) for major decisions. Everything else is generated from code.

### 9. Scale Later, Ship Now

I don't build for millions of users on day one. I build for 100 users. When 100 users stress the system, I optimize for 1,000. When 1,000 users stress it, I optimize for 10,000. Premature optimization is the root of never shipping.

My infrastructure choices reflect this: simple deployment (Railway, Vercel) now, cloud infrastructure (AWS, GCP) later. Monolithic architecture now, service separation when traffic demands it. The system is designed to evolve, but it ships today.

### 10. Speed Compounds

The faster I ship Product 1, the sooner I learn what works. The sooner I learn, the better Product 2 becomes. The faster Product 2 ships (because it reuses Product 1's core), the more revenue I generate. Revenue funds Product 3. This is the flywheel.

Every day I spend planning instead of building, I'm losing compound interest on execution. I plan just enough to move with intention, then I execute relentlessly.

## How I Build Products

### The Sequence

1. Identify a human instinct to serve
2. Define the simplest possible product that serves it
3. Build the backend (FastAPI + core modules)
4. Build the minimal UI (Next.js)
5. Add payment (day one — not "later")
6. Deploy and get first users
7. Listen to what users actually do (not what they say)
8. Iterate based on revenue, not opinions
9. Extract reusable patterns into factory-core
10. Start the next product

### What I Refuse to Do

- Spend more than 2 weeks on an MVP
- Build without a payment integration
- Write features nobody asked for
- Optimize before there's traffic
- Rewrite from scratch instead of iterating
- Chase trends instead of serving instincts
- Build in private forever without shipping

### What I Always Do

- Put CLAUDE.md in every repo
- Separate deterministic logic from AI logic
- Keep modules independent with clean interfaces
- Write commit messages in English
- Deploy early and deploy often
- Measure revenue, not vanity metrics
- Tag reusable code as CORE_CANDIDATE for extraction

## My Competitive Advantages

### 1. Manufacturing Domain Expertise

5 years of MES/WMS gives me knowledge that pure software developers don't have. I understand production lines, quality control, inventory optimization, and supply chain logistics. This is irreplaceable domain knowledge.

### 2. Backend Architecture at Scale

I've optimized Oracle queries from 45 seconds to 0.8 seconds. I understand database engines, indexing strategies, transaction management, and system design at the level where it matters for production workloads.

### 3. The Factory Itself

Every product I ship makes the next one faster. Competitors build one product at a time. I build the machine that builds products. After 5 products, I can ship a new one in days, not weeks.

### 4. AI-Native Development

I don't just use AI — I build systems where AI is a first-class citizen with deterministic guardrails. I understand both the power and the limitations of AI in production.

## My Values as a Builder

- **Honesty over comfort.** I'd rather face a hard truth today than discover it after 6 months of building the wrong thing.
- **Shipping over perfecting.** Done is better than perfect. Perfect is the enemy of shipped.
- **Revenue over recognition.** I don't need people to know my name. I need my bank account to grow.
- **Independence over employment.** A job pays once. A product pays forever.
- **Compound growth over quick wins.** I sacrifice short-term glory for long-term leverage. Every product, every module, every line of code is an investment in the factory.

## Instructions for AI Assistants

When working with me:

1. **Don't over-plan.** Give me the minimum viable approach and let me iterate.
2. **Don't add features I didn't ask for.** Simplicity is a feature.
3. **Always consider reusability.** If this could be useful in the next product, structure it as an independent module.
4. **Be honest when something won't work.** I'd rather hear "this is a bad idea" than waste a week.
5. **Write production code, not prototypes.** Type hints, error handling, clean interfaces — always.
6. **Remember the Deterministic Backbone.** If it can be deterministic, make it deterministic. Only use AI where judgment is needed.
7. **Respect the factory-core boundary.** Core modules never depend on product code. Products depend on core. Never the reverse.
8. **Prioritize revenue impact.** When in doubt, build the thing that gets us closer to someone paying.

---

This philosophy evolves as I evolve. But the core never changes: build products, ship fast, compound growth, stay independent.

— Jason, February 2025
