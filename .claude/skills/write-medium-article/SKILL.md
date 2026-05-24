---
name: write-medium-article
description: Write a medium article on a given topic referring to the repo.  Use this skill when the user asks to write or draft a Medium post, article, or blog post, especially when a codebase or repository is involved.
---
# Write Medium Article
 
Write a high-quality, tutorial-style Medium article based on a code repo or project the user provides.
 
## Workflow
 
### 1. Understand the Repo
 
Before writing, explore the repo to understand:
- **What it does** — read the README, entry points, and any docs
- **Key technical decisions** — architecture, libraries, interesting patterns
- **The "why"** — what problem does it solve, why would a reader care?
If the user shares a GitHub URL, read the README and key source files. If they paste code directly, work with what's given. If something is unclear, ask one focused question before proceeding.
 
### 2. Choose an Angle
 
Pick the angle that best suits the repo. For tutorial/how-to articles, good angles include:
- "How I built X" — first-person walkthrough of building the project
- "How to do X with Y" — teaching a technique using the repo as the example
- "X from scratch" — step-by-step guide using the code as the reference implementation
State the chosen angle briefly to the user before writing, unless it's obvious.
 
### 3. Write the Article
 
Produce a complete, publish-ready Medium article with the following structure:
 
#### Title Block
Provide **3 SEO-friendly title options** before the article body. Format:
```
Title options:
1. [Option 1]
2. [Option 2]
3. [Option 3]
```
Good titles are specific, outcome-oriented, and include the main technology (e.g. "Build a REST API with FastAPI and PostgreSQL in 15 Minutes").
 
#### Article Structure
 
```
## Introduction
Hook the reader in 2–3 sentences. State what they'll learn and why it matters.
 
## Prerequisites
Brief bullet list: what the reader needs to know / have installed.
 
## [Section 1: First major concept or step]
...
 
## [Section 2: Next step]
...
 
## [Continue as needed]
 
## Conclusion
Summarize what was built/learned. Suggest next steps or extensions.
```
 
#### Code Snippets
- Pull real code from the repo — don't invent placeholder examples
- Always wrap in fenced code blocks with the language specified (```python, ```bash, etc.)
- Keep snippets focused: show only the relevant part, not entire files
- Add a one-line comment above each snippet explaining what it does
- Add the relative file path in the comment as it helps orient the reader (e.g. `# app.py`)
- Please also add requirements installation snippets if relevant (e.g. `pip install fastapi uvicorn`)
- Also include virtual environment setup for Mac and WINDOWS if relevant (e.g. `python -m venv venv` + activation commands)

#### Flow Diagrams

Use both styles in the same article — choose based on complexity:
1. Simple text flows — for linear, step-by-step pipelines. Use whenever a process is sequential with or without branching:
input
↓
text extraction
↓
entity mapping
↓
output

Keep labels short (2–4 words). Use ↓ as the arrow. No code block needed — render inline as a plain text block.

2. Mermaid diagrams — for branching logic, architecture, or multi-component systems. Use flowchart TD (top-down) by default; switch to LR (left-right) only when the flow is clearly horizontal in nature.
Conventions:

Node labels: Title Case with an emoji prefix for major components (e.g. B[🔍 Vector DB])
Subgraph labels: always include a descriptive title with an emoji (e.g. subgraph RAG["🔁 Retrieval-Augmented Generation"])
Edge labels: use -->|action| syntax when the relationship needs clarification, omit when the flow is self-evident
Theme: use default Mermaid theme; avoid custom style overrides unless critical

Must include at least one diagram (either style) per article when the project has a meaningful architecture or multi-step pipeline.

For complex architecture or flows, include diagrams to clarify. Use Mermaid syntax for flowcharts, sequence diagrams, or architecture diagrams as needed. For example:
```mermaid
flowchart TD
    A[User] --> B[Streamlit App]    
    B --> C[PDF Parser]
    B --> D[Vector DB]
    B --> E[LLM]
    E --> F[Answer Generation]
    D --> E
    C --> E
    E --> G[Answer Display]
    subgraph Retrieval["🔍 Retrieval-Augmented Generation"]
```


#### Writing Style
- **Conversational but precise** — write like a knowledgeable colleague explaining to another developer
- **Second person** — address the reader as "you"
- **Active voice** — "you'll build", not "a server will be built"
- **Short paragraphs** — 2–4 sentences max; Medium readers skim
- **No fluff** — skip filler phrases like "In today's fast-paced world..." or "As we all know..."


### 4. Output Format
 
Deliver in this order:
1. Title options (3 choices)
2. The full article in Markdown, ready to paste into Medium
3. A short note on any repo sections you didn't cover and why (if relevant)
Medium supports Markdown via its import feature, so use standard Markdown throughout.
 
## Example Trigger Phrases
 
- "Write a Medium article about this repo"
- "Turn my project into a blog post"
- "Help me write a tutorial for this code"
- "Draft an article explaining how this works"
- "Write something I can post on Medium about [project]"