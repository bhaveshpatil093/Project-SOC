# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: visual.spec.js >> Visual Regression >> dark mode visual snapshot
- Location: tests/e2e/visual.spec.js:17:3

# Error details

```
Error: A snapshot doesn't exist at /Users/bhaveshpatil/Developer/Project-SOC/Project-SOC/frontend/tests/e2e/visual.spec.js-snapshots/dashboard-dark-mobile-chrome-darwin.png, writing actual.
```

# Page snapshot

```yaml
- generic [ref=e7]:
  - generic [ref=e8]:
    - img [ref=e10]
    - heading "ISRO ISTRAC" [level=1] [ref=e12]
    - paragraph [ref=e13]: Advanced SOC Analytics Platform
  - generic [ref=e15]:
    - generic [ref=e16]:
      - text: Personnel ID
      - textbox "Enter your tracking designation" [ref=e17]
    - generic [ref=e18]:
      - text: Passcode
      - textbox "••••••••" [ref=e19]
    - button "Sign In" [ref=e20] [cursor=pointer]:
      - img [ref=e21]
      - text: Sign In
  - paragraph [ref=e25]: RESTRICTED ACCESS • AUTHORIZED PERSONNEL ONLY
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('Visual Regression', () => {
  4  |   test('dashboard visual snapshot', async ({ page }) => {
  5  |     await page.goto('/dashboard');
  6  |     // Wait for the page to settle (charts might animate)
  7  |     await page.waitForTimeout(1000);
  8  |     await expect(page).toHaveScreenshot('dashboard.png', { maxDiffPixels: 500 });
  9  |   });
  10 | 
  11 |   test('alert detail visual snapshot', async ({ page }) => {
  12 |     await page.goto('/alerts/1');
  13 |     await page.waitForTimeout(1000);
  14 |     await expect(page).toHaveScreenshot('alert-detail.png', { maxDiffPixels: 500 });
  15 |   });
  16 | 
  17 |   test('dark mode visual snapshot', async ({ page }) => {
  18 |     // Assuming dark mode is default or we can toggle it
  19 |     await page.goto('/dashboard');
  20 |     // We can evaluate localStorage to force dark mode
  21 |     await page.evaluate(() => localStorage.setItem('theme', 'dark'));
  22 |     await page.reload();
  23 |     await page.waitForTimeout(1000);
> 24 |     await expect(page).toHaveScreenshot('dashboard-dark.png', { maxDiffPixels: 500 });
     |     ^ Error: A snapshot doesn't exist at /Users/bhaveshpatil/Developer/Project-SOC/Project-SOC/frontend/tests/e2e/visual.spec.js-snapshots/dashboard-dark-mobile-chrome-darwin.png, writing actual.
  25 |   });
  26 | 
  27 |   test('light mode visual snapshot', async ({ page }) => {
  28 |     await page.goto('/dashboard');
  29 |     await page.evaluate(() => localStorage.setItem('theme', 'light'));
  30 |     await page.reload();
  31 |     await page.waitForTimeout(1000);
  32 |     await expect(page).toHaveScreenshot('dashboard-light.png', { maxDiffPixels: 500 });
  33 |   });
  34 | });
  35 | 
```