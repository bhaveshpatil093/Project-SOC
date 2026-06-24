# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: accessibility.spec.js >> Accessibility (a11y) >> alerts page has no accessibility violations
- Location: tests/e2e/accessibility.spec.js:11:3

# Error details

```
Error: expect(received).toEqual(expected) // deep equality

- Expected  -   1
+ Received  + 105

- Array []
+ Array [
+   Object {
+     "description": "Ensure the document has a main landmark",
+     "help": "Document should have one main landmark",
+     "helpUrl": "https://dequeuniversity.com/rules/axe/4.12/landmark-one-main?application=playwright",
+     "id": "landmark-one-main",
+     "impact": "moderate",
+     "nodes": Array [
+       Object {
+         "all": Array [
+           Object {
+             "data": null,
+             "id": "page-has-main",
+             "impact": "moderate",
+             "message": "Document does not have a main landmark",
+             "relatedNodes": Array [],
+           },
+         ],
+         "any": Array [],
+         "failureSummary": "Fix all of the following:
+   Document does not have a main landmark",
+         "html": "<html lang=\"en\" style=\"--bg_primary: #0f172a; --bg_secondary: #1e293b; --bg_tertiary: #334155; --text_primary: #f1f5f9; --text_secondary: #94a3b8; --border: #334155; --accent: #3b82f6; --critical: #ef4444; --high: #f97316; --medium: #eab308; --low: #22c55e;\">",
+         "impact": "moderate",
+         "none": Array [],
+         "target": Array [
+           "html",
+         ],
+       },
+     ],
+     "tags": Array [
+       "cat.semantics",
+       "best-practice",
+     ],
+   },
+   Object {
+     "description": "Ensure that the page, or at least one of its frames contains a level-one heading",
+     "help": "Page should contain a level-one heading",
+     "helpUrl": "https://dequeuniversity.com/rules/axe/4.12/page-has-heading-one?application=playwright",
+     "id": "page-has-heading-one",
+     "impact": "moderate",
+     "nodes": Array [
+       Object {
+         "all": Array [
+           Object {
+             "data": null,
+             "id": "page-has-heading-one",
+             "impact": "moderate",
+             "message": "Page must have a level-one heading",
+             "relatedNodes": Array [],
+           },
+         ],
+         "any": Array [],
+         "failureSummary": "Fix all of the following:
+   Page must have a level-one heading",
+         "html": "<html lang=\"en\" style=\"--bg_primary: #0f172a; --bg_secondary: #1e293b; --bg_tertiary: #334155; --text_primary: #f1f5f9; --text_secondary: #94a3b8; --border: #334155; --accent: #3b82f6; --critical: #ef4444; --high: #f97316; --medium: #eab308; --low: #22c55e;\">",
+         "impact": "moderate",
+         "none": Array [],
+         "target": Array [
+           "html",
+         ],
+       },
+     ],
+     "tags": Array [
+       "cat.semantics",
+       "best-practice",
+     ],
+   },
+   Object {
+     "description": "Ensure all page content is contained by landmarks",
+     "help": "All page content should be contained by landmarks",
+     "helpUrl": "https://dequeuniversity.com/rules/axe/4.12/region?application=playwright",
+     "id": "region",
+     "impact": "moderate",
+     "nodes": Array [
+       Object {
+         "all": Array [],
+         "any": Array [
+           Object {
+             "data": Object {
+               "isIframe": false,
+             },
+             "id": "region",
+             "impact": "moderate",
+             "message": "Some page content is not contained by landmarks",
+             "relatedNodes": Array [],
+           },
+         ],
+         "failureSummary": "Fix any of the following:
+   Some page content is not contained by landmarks",
+         "html": "<span class=\"text-xl font-medium tracking-tight\">Verifying authorization protocols...</span>",
+         "impact": "moderate",
+         "none": Array [],
+         "target": Array [
+           "span",
+         ],
+       },
+     ],
+     "tags": Array [
+       "cat.keyboard",
+       "best-practice",
+       "RGAAv4",
+       "RGAA-9.2.1",
+     ],
+   },
+ ]
```

# Page snapshot

```yaml
- generic [ref=e7]:
  - generic [ref=e8]:
    - img [ref=e10]
    - heading "ISRO ISTRAC" [level=1] [ref=e14]
    - paragraph [ref=e15]: Advanced SOC Analytics Platform
  - generic [ref=e17]:
    - generic [ref=e18]:
      - text: Personnel ID
      - textbox "Enter your tracking designation" [ref=e19]
    - generic [ref=e20]:
      - text: Passcode
      - textbox "••••••••" [ref=e21]
    - button "Sign In" [ref=e22] [cursor=pointer]:
      - img [ref=e23]
      - text: Sign In
  - paragraph [ref=e27]: RESTRICTED ACCESS • AUTHORIZED PERSONNEL ONLY
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import AxeBuilder from '@axe-core/playwright';
  3  | 
  4  | test.describe('Accessibility (a11y)', () => {
  5  |   test('dashboard has no accessibility violations', async ({ page }) => {
  6  |     await page.goto('/dashboard');
  7  |     const results = await new AxeBuilder({ page }).analyze();
  8  |     expect(results.violations).toEqual([]);
  9  |   });
  10 | 
  11 |   test('alerts page has no accessibility violations', async ({ page }) => {
  12 |     await page.goto('/alerts');
  13 |     const results = await new AxeBuilder({ page }).analyze();
> 14 |     expect(results.violations).toEqual([]);
     |                                ^ Error: expect(received).toEqual(expected) // deep equality
  15 |   });
  16 | 
  17 |   test('alert detail page has no accessibility violations', async ({ page }) => {
  18 |     await page.goto('/alerts/1');
  19 |     const results = await new AxeBuilder({ page }).analyze();
  20 |     expect(results.violations).toEqual([]);
  21 |   });
  22 | 
  23 |   test('investigation page has no accessibility violations', async ({ page }) => {
  24 |     await page.goto('/workbench');
  25 |     const results = await new AxeBuilder({ page }).analyze();
  26 |     expect(results.violations).toEqual([]);
  27 |   });
  28 | 
  29 |   test('forms have proper labels', async ({ page }) => {
  30 |     // Verify Login Form
  31 |     await page.goto('/');
  32 |     const loginResults = await new AxeBuilder({ page })
  33 |       .include('form')
  34 |       .withRules(['label', 'aria-valid-attr'])
  35 |       .analyze();
  36 |     expect(loginResults.violations).toEqual([]);
  37 |     
  38 |     // Verify Feedback Form (if exists on a specific page, say workbench)
  39 |     await page.goto('/workbench');
  40 |     const feedbackResults = await new AxeBuilder({ page })
  41 |       .include('form')
  42 |       .withRules(['label'])
  43 |       .analyze();
  44 |     expect(feedbackResults.violations).toEqual([]);
  45 |   });
  46 | 
  47 |   test('color contrast meets WCAG AA', async ({ page }) => {
  48 |     await page.goto('/dashboard');
  49 |     const results = await new AxeBuilder({ page })
  50 |       .withTags(['wcag2aa', 'wcag21aa'])
  51 |       .analyze();
  52 |     // We only care about contrast for this test
  53 |     const contrastViolations = results.violations.filter(v => v.id === 'color-contrast');
  54 |     expect(contrastViolations).toEqual([]);
  55 |   });
  56 | 
  57 |   test('keyboard navigation works through sidebar', async ({ page }) => {
  58 |     await page.goto('/dashboard');
  59 |     // Tab through sidebar links, verify focus is visible
  60 |     await page.keyboard.press('Tab');
  61 |     await page.keyboard.press('Tab');
  62 |     // Check if something is focused
  63 |     const focusedElement = await page.evaluate(() => document.activeElement !== document.body);
  64 |     expect(focusedElement).toBeTruthy();
  65 |   });
  66 | });
  67 | 
```