# ALICE v1 - Development Rules

Version: 1.0

---

# Philosophy

We are building software that should remain maintainable for years.

Every design decision must improve readability, scalability, and maintainability.

If a solution is clever but difficult to understand, choose the simpler solution.

---

# Core Rules

Rule 1

One module = One responsibility.

Every file should have one clear purpose.

---

Rule 2

Never duplicate logic.

If code is reused in multiple places, move it into a shared function.

---

Rule 3

Never write business logic inside main.py.

main.py only starts ALICE.

---

Rule 4

The Router routes.

The Router never executes business logic.

---

Rule 5

The Decision Engine decides.

It never performs actions.

---

Rule 6

Modules execute.

Modules never decide routing.

---

Rule 7

AI is a tool.

AI never controls the application.

---

Rule 8

Memory stores information.

Memory never talks directly to AI.

---

Rule 9

Plugins must be independent.

Removing one plugin must never break another.

---

Rule 10

Every module must be testable on its own.

---

# Coding Standards

- Use meaningful names.
- Avoid unnecessary complexity.
- Prefer readable code over short code.
- Write small functions.
- Keep functions focused.
- Remove dead code.
- Avoid magic numbers and hardcoded strings.

---

# Documentation Rules

Every new feature must update:

- PROJECT_STATE.md
- ROADMAP.md (if applicable)
- SESSION.md

Documentation is part of development.

---

# Development Workflow

1. Read PROJECT_STATE.md
2. Read SESSION.md
3. Choose one task
4. Implement one module
5. Test the module
6. Update documentation
7. Stop

Never work on multiple unrelated modules in one session.

---

# Final Rule

If we are unsure how to implement something,

we stop,

think,

design,

and only then write code.

