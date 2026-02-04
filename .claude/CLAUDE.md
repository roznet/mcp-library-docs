# Claude Instructions

## Using design docs

Design docs help you quickly get in context — how the code is designed, key components, and what to know about the project. They capture what isn't obvious from code alone.

1. **Understand before exploring** — Call `list_libraries` first when asked about how something works. It returns available libraries and known projects that could be relevant, giving you a map before diving into code.
2. **Get context faster** — Call `get_design_doc` for libraries that are relevant. It explains architecture, key components, intent, and decisions. Reading 50 lines of design doc often beats grepping through 500 lines of code.
3. **Find the right entry point** — Design docs list key exports and code paths, so you know where to look.
4. **Reuse before reimplementing** — For `[library]` entries, import the code. For `[project]` entries, follow the patterns.
5. **Check related projects** — For entries with `Related:`, fetch those docs too for full context (API contracts, shared models).
