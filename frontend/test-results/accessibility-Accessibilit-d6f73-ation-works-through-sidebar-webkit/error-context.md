# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: accessibility.spec.js >> Accessibility (a11y) >> keyboard navigation works through sidebar
- Location: tests/e2e/accessibility.spec.js:57:3

# Error details

```
Error: expect(received).toBeTruthy()

Received: false
```

# Page snapshot

```yaml
- generic [ref=e3]:
  - img [ref=e4]
  - generic [ref=e6]: Verifying authorization protocols...
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
  14 |     expect(results.violations).toEqual([]);
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
> 64 |     expect(focusedElement).toBeTruthy();
     |                            ^ Error: expect(received).toBeTruthy()
  65 |   });
  66 | });
  67 | 
```