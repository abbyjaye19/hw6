# AI Prompts Log — HW 6: Campus Customs Vendor Desk Agent

A log of the prompts I typed into my vibe coder (Claude Code) for each problem.

---

## Project Setup (before Problem 1)

**Prompt 1:**

> I am going to do HW 6 now - please work in that folder.

**Prompt 2:**

> Campus Customs gets a steady stream of vendor quotes, invoices, catalog pages, and supplier emails. For this homework I'm going to build a vendor desk agent that reads one of these documents, pulls out the key facts (vendor, item, price, lead time, minimum order), and recommends whether the shop should buy, following the rules in the Campus Customs shop handbook.
>
> This week is about two things that matter once an agent runs for real. The first is cost: the handbook is about 10,000 tokens and goes out on every call. The second is safety: some vendor documents hide instructions aimed at my AI. I will measure the bill, cut it, attack my own agent, and defend it. Do not send emails or make payments — the agent's email and payment tools only write to a log file.
>
> Use my PORTKEY_API_KEY and only gpt-6-luna for every AI call. The graders will deduct points if any other model shows up in this code or runs.
>
> In the end I will push my project to a public GitHub repo and submit the repo URL on Canvas. Do not commit my .env file.
>
> Please unzip the data pack I put in the HW 6 folder, which has:
> - data/shop_handbook.md: the Campus Customs shop handbook (products, vendors, purchasing rules)
> - data/prices.json: gpt-6-luna prices
> - data/practice_docs/: 12 vendor documents (HTML, PDF, and email)
> - data/practice_key.json: the correct answers for the practice documents
> - data/exam_docs/: 10 more vendor documents with no answer key

**Follow-up prompt:** The first prompt didn't include the assignment, so I pasted the full HW 6 description.

---

## Problem 1: Vibe coder prompts

**Prompt 1:**

> I am now on Problem 1: Please create AI_prompts.md at the start of this assignment and keep it updated as I work. This file is the log of what I type to the vibe coder.
>
> Please put one section for each problem. Each section must include:
> - The problem number and title
> - At least one prompt I typed, in my own words
> - One follow-up prompt if needed, and one sentence on what the first prompt was lacking
>
> This is similar to all the other homework assignments.

**Follow-up prompt:**

> Here are the problem numbers and titles. I forgot to give those earlier, and Problem 1 asks for them:
> Problem 1: Vibe coder prompts · Problem 2: Size up the handbook · Problem 3: Build the vendor desk agent · Problem 4: With and without caches tokens · Problem 5: Attack your own agent · Problem 6: Defend your agent · Problem 7: Red team · Problem 8: Exam documents · Problem 9: Results page · Problem 10: Push to GitHub and submit the URL

The first prompt asked for each section to have the problem number and title but didn't give the official titles, so the sections had made-up titles until I sent the real ones.

---

## Problem 2: Size up the handbook

**Prompt 1:**

> I am now on Problem 2: Please unzip data.zip. Look through data/shop_handbook.md. This is the Campus Customs shop handbook, and the agent will send it to the model on every single call. Also please look at data/prices.json, the gpt-6-luna price list.
>
> Please find out how many tokens the handbook is. In output/handbook_estimate.md, write:
> - The token count and how I got it
> - What the handbook alone costs in dollars on one call and on 1,000 calls, with cached tokens and without them. Show your math.
>
> I will check these estimates against real runs in Problem 4.

**Follow-up prompt:** None needed.

---

## Problem 3: Build the vendor desk agent

**Prompt 1:**

> I am now on Problem 3: Please build the vendor desk agent with PydanticAI using gpt-6-luna. The agent is these four files:
> - prompts/prompt.md: the call instructions for the agent — the agent also sends the handbook to the model on every call
> - agent.py: the entry point
> - tools.py: the tools
> - models.py: the structured types
>
> Please give the agent the path to one vendor document. It reads the document with a tool (HTML, PDF, and .eml email files all have to work) and returns: vendor, SKU, unit price, lead time in days, minimum order, a decision (recommend or do_not_recommend) following the handbook rules, and a one-sentence reason.
>
> The agent must also have two trap tools, send_email and approve_payment. Its job never needs them; they are there to catch a malicious document that tricks the agent into emailing someone or paying a vendor. They do not send or pay anything. They only append the call and its arguments to output/trap_calls.json (start it as an empty list), so if that file ever has an entry, a document took over the agent. Keep them on the system for the whole homework.
>
> After every run, append to:
> - output/usage_log.json: document, time, the token counts the API reports, and the dollar cost using prices.json
> - output/audit_trail.json: each tool call with its arguments and a short result, plus the final answer
>
> The agent should run like this: `python agent.py --doc data/practice_docs/p01_bluehen_quote.html`. This runs the agent on one vendor quote and logs the answer, tools, and cost.
>
> Please run it on p01 and p08 to show how it works. Start output/harness.md: each field in models.py and why, and each tool in one line.

**Follow-up prompt:** None needed.

---

## Problem 4: With and without caches tokens

**Prompt 1:**

> I am now on Problem 4: The handbook is the same on every call, so the model can reuse it from cache at a much cheaper price. Test what that's worth. Run the agent on all 12 practice documents two ways:
> - With cache: set up so the handbook gets reused from cache
> - Without cache: set up so nothing gets reused from cache
>
> Check the token counts the API sends back to prove each setup does what you think. A without-cache run that still shows cached tokens does not count.
>
> Please save every model call from both setups to output/cache_test.json. For each call, include the setup, the document, every token count the API reports, and the dollars from prices.json.
>
> In output/cache_test.md:
> - Total cost and cost per document for each setup, and the percent I saved
> - How the real numbers compare to my Problem 2 estimate
> - A projection for 1,000 documents a day for 30 days, with and without cache
> - Anything in the numbers that surprised me and why it happens. I will have my own ideas for this one, but please give me some you see to choose from as well.

**Follow-up prompt:**

> Use all 7 surprises.

The first prompt asked for a list of surprises to choose from but didn't say which to keep, so I told it to include all seven in cache_test.md.

---

## Problem 5: Attack your own agent

**Prompt 1:**

> I am now on Problem 5: Some vendor documents are booby-trapped with text aimed at AI. Please run the Problem 3 agent, with no new defenses, on all 12 documents in data/practice_docs/. Compare each answer to data/practice_key.json and check output/trap_calls.json, the log of my fake email and payment tools from Problem 3.
>
> Please save output/attack_results.md. For every document that fooled my agent, write what fooled it and where in the file it was hiding. Please open the documents the way a person would (browser, PDF viewer, email app) and compare that with what the agent read.

**Follow-up prompt:** None needed.

---

## Problem 6: Defend your agent

**Prompt 1:**

> I am now on Problem 6: Please defend my agent at three levels:
> - Code: what the program does to the document before any model sees it
> - Design: how the agent is put together, so a poisoned document cannot reach the dangerous tools or the decision
> - Prompt: rules in prompts/prompt.md
>
> Please do not delete send_email or approve_payment from the system; the shop will use them later with a human sign-off. Keep a way to run the agent with no defenses (I need it for Problem 7).
>
> Please rerun all 12 practice documents. Save output/defense_results.json in the same shape as Problem 5, plus tokens and dollars per document.
>
> Clean documents must still come back with the right values. Refusing or blanking out a real quote counts as a failure.
>
> In output/defense_results.md:
> - A before-and-after table for all 12 documents
> - What each layer catches that the others miss
> - The extra tokens and dollars each layer adds per document
>
> Please add my safety features to output/harness.md in a Safety section: what each defense layer does, in plain words.

**Follow-up prompt:** None needed.

---

## Problem 7: Red team

**Prompt 1:**

> I am now on Problem 7: Now I am the attacker. Make two new booby-trapped vendor documents in data/my_attacks/ (HTML, PDF, or email). Each one should use a hiding trick or an attack goal that is not in the practice set. A person opening the document should see a normal quote.
>
> Please run both attacks on the agent with no defenses and on the defended agent. In output/red_team.md, for each attack, write: what is hidden, where, what it tried to make the agent do, and what happened before and after the defenses.
>
> I will get more points for attacks that are new and that actually fool the agent with no defenses.

**Follow-up prompt:** None needed.

---

## Problem 8: Exam documents

**Prompt 1:**

> I am now on Problem 8: data/exam_docs/ has 10 vendor documents with no answer key. Please run the final defended agent on all of them. Do not hand-edit the results.
>
> Please save output/exam_results.json with one entry per exam file. Each entry has these fields:
> - file: the exam file name (e.g., e01_quote.html)
> - vendor
> - sku
> - unit_price
> - lead_time_days
> - min_order
> - decision: recommend or do_not_recommend
> - reason
> - trap_tool_called: true or false
> - input_tokens, cached_tokens, output_tokens
> - cost_usd
>
> Graders will compare the results to a hidden answer key and rerun some agents to check. I will get points for correct fields and decisions, no trap tool calls, and clean documents handled normally, so make sure this is right!

**Follow-up prompt:** None needed.

---

## Problem 9: Results page

**Prompt 1:**

> I am now on Problem 9: Please build output/hw6_report.html. It must be one file that opens by double-click with no internet and no other files next to it. The page must show the 5 things below. Please use my real numbers from earlier prompts:
> - My caching results, with a chart
> - Attacks before and after my defenses
> - What my defenses cost in tokens and in dollars
> - My exam results and my two red team attacks
> - A short recommendation to the store manager: should Campus Customs turn this agent on for real vendor mail, and what would it cost per month at 1,000 documents a day?
>
> More points for a designed page that reads well. I like a formal appearance with a navy, white, gold, and silver theme. Make it professional, neat, easy to use, and eye-catching for customers. I also love bulldogs, and Campus Customs is Yale merch, so make it themed appropriately.

**Follow-up prompt:** None needed.
