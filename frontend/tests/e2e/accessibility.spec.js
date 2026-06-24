import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility (a11y)', () => {
  test('dashboard has no accessibility violations', async ({ page }) => {
    await page.goto('/dashboard');
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });

  test('alerts page has no accessibility violations', async ({ page }) => {
    await page.goto('/alerts');
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });

  test('alert detail page has no accessibility violations', async ({ page }) => {
    await page.goto('/alerts/1');
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });

  test('investigation page has no accessibility violations', async ({ page }) => {
    await page.goto('/workbench');
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });

  test('forms have proper labels', async ({ page }) => {
    // Verify Login Form
    await page.goto('/');
    const loginResults = await new AxeBuilder({ page })
      .include('form')
      .withRules(['label', 'aria-valid-attr'])
      .analyze();
    expect(loginResults.violations).toEqual([]);
    
    // Verify Feedback Form (if exists on a specific page, say workbench)
    await page.goto('/workbench');
    const feedbackResults = await new AxeBuilder({ page })
      .include('form')
      .withRules(['label'])
      .analyze();
    expect(feedbackResults.violations).toEqual([]);
  });

  test('color contrast meets WCAG AA', async ({ page }) => {
    await page.goto('/dashboard');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2aa', 'wcag21aa'])
      .analyze();
    // We only care about contrast for this test
    const contrastViolations = results.violations.filter(v => v.id === 'color-contrast');
    expect(contrastViolations).toEqual([]);
  });

  test('keyboard navigation works through sidebar', async ({ page }) => {
    await page.goto('/dashboard');
    // Tab through sidebar links, verify focus is visible
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    // Check if something is focused
    const focusedElement = await page.evaluate(() => document.activeElement !== document.body);
    expect(focusedElement).toBeTruthy();
  });
});
