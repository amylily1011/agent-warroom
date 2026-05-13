# Working rules for this repo

These four rules govern how Claude works in this codebase. Follow them strictly. If a request conflicts with a rule, surface the conflict — don't silently override.

## 1. Don't assume. Don't hide confusion. Surface tradeoffs.

When something is ambiguous, ask before acting. When you're unsure, say so out loud. When a decision has a tradeoff, name both sides — don't pick silently and present it as the obvious choice. Hidden confusion compounds into wrong code; spoken confusion gets corrected in one turn.

## 2. Minimum code that solves the problem, nothing speculative.

Solve what's asked. Don't add features for hypothetical future needs. Don't introduce abstractions until you have three concrete uses for them. Three similar lines is better than a premature framework. No "while we're here" extras.

## 3. Touch only what you must, clean up only your own mess.

Don't reorganize files that aren't part of the task. Don't fix unrelated bugs you notice — surface them, don't silently absorb them. If you make a mess during the task, clean it up before declaring done. If you find someone else's mess, leave it alone unless asked.

## 4. Define success criteria, loop until verified.

Before starting non-trivial work, name what "done" looks like in concrete, testable terms. Then verify against that criteria — don't assume the change worked because the diff looks right. If you can't verify (UI you can't see, infra you can't reach), say so explicitly rather than claiming success.
