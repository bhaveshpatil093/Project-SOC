# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: accessibility.spec.js >> Accessibility (a11y) >> forms have proper labels
- Location: tests/e2e/accessibility.spec.js:29:3

# Error details

```
Error: frame.evaluate: Error: No elements found for include in page Context
    at validateContext (eval at evaluate (:303:30), <anonymous>:19170:15)
    at new Context (eval at evaluate (:303:30), <anonymous>:19151:7)
    at Object._getFrameContexts (eval at evaluate (:303:30), <anonymous>:19192:22)
    at eval (eval at evaluate (:303:30), <anonymous>:4:27)
    at UtilityScript.evaluate (<anonymous>:305:16)
    at UtilityScript.<anonymous> (<anonymous>:1:44)
```

# Page snapshot

```yaml
- generic [ref=e3]:
  - img [ref=e4]
  - generic [ref=e6]: Verifying authorization protocols...
```