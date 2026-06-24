# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: critical_paths.spec.js >> Critical Paths >> alert table is scrollable and clickable
- Location: tests/e2e/critical_paths.spec.js:31:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('table')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('table')

```

```yaml
- heading "ISRO ISTRAC" [level=1]
- paragraph: Advanced SOC Analytics Platform
- text: Personnel ID
- textbox "Enter your tracking designation"
- text: Passcode
- textbox "••••••••"
- button "Sign In"
- paragraph: RESTRICTED ACCESS • AUTHORIZED PERSONNEL ONLY
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('Critical Paths', () => {
  4  |   test('login flow works across browsers', async ({ page }) => {
  5  |     // Navigate to base URL
  6  |     await page.goto('/');
  7  |     
  8  |     // Fill credentials
  9  |     await page.fill('[name="username"]', 'analyst');
  10 |     await page.fill('[name="password"]', 'analyst123');
  11 |     
  12 |     // Submit login
  13 |     await page.click('button[type="submit"]');
  14 |     
  15 |     // Verify dashboard redirect
  16 |     await expect(page).toHaveURL(/dashboard/);
  17 |   });
  18 | 
  19 |   test('dashboard loads stat cards', async ({ page }) => {
  20 |     await page.goto('/');
  21 |     await page.fill('[name="username"]', 'analyst');
  22 |     await page.fill('[name="password"]', 'analyst123');
  23 |     await page.click('button[type="submit"]');
  24 |     await expect(page).toHaveURL(/dashboard/);
  25 |     
  26 |     // Check for standard dashboard headings or text
  27 |     await expect(page.getByText(/Total Alerts/i)).toBeVisible();
  28 |     await expect(page.getByText(/Active Incidents/i)).toBeVisible();
  29 |   });
  30 | 
  31 |   test('alert table is scrollable and clickable', async ({ page }) => {
  32 |     await page.goto('/alerts');
  33 |     // Ensure table renders
> 34 |     await expect(page.locator('table')).toBeVisible();
     |                                         ^ Error: expect(locator).toBeVisible() failed
  35 |     // Verify there is at least one row
  36 |     const rows = page.locator('tbody tr');
  37 |     await expect(rows.first()).toBeVisible();
  38 |   });
  39 | 
  40 |   test('SLM chat sends and receives message', async ({ page }) => {
  41 |     await page.goto('/workbench');
  42 |     
  43 |     // Type in chat input
  44 |     const input = page.getByPlaceholder('Ask SLM...');
  45 |     await expect(input).toBeVisible();
  46 |     await input.fill('What is the latest critical alert?');
  47 |     
  48 |     // Click send
  49 |     await page.locator('button', { hasText: 'Send' }).click();
  50 |     
  51 |     // Verify user message appears
  52 |     await expect(page.getByText('What is the latest critical alert?')).toBeVisible();
  53 |     
  54 |     // Note: since this is testing against our mock server from msw/dev, it should respond.
  55 |     // Verify SLM response (mocked)
  56 |     // The exact response might depend on the mock handler, we'll just check for a generic response container if we don't know it.
  57 |     await expect(page.locator('.chat-message.system, .chat-bubble.slm').first()).toBeVisible({ timeout: 10000 }).catch(() => true); 
  58 |   });
  59 | 
  60 |   test('mobile viewport shows bottom tab bar', async ({ page, isMobile }) => {
  61 |     // Only test if the project is mobile
  62 |     if (!isMobile) return;
  63 |     
  64 |     await page.goto('/dashboard');
  65 |     // Mobile tab bar or hamburger menu should be visible
  66 |     await expect(page.locator('nav.mobile-nav, button.mobile-menu-toggle, .bottom-tab-bar').first()).toBeVisible().catch(() => true);
  67 |   });
  68 | });
  69 | 
```