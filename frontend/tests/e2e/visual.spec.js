import { test, expect } from '@playwright/test';

test.describe('Visual Regression', () => {
  test('dashboard visual snapshot', async ({ page }) => {
    await page.goto('/dashboard');
    // Wait for the page to settle (charts might animate)
    await page.waitForTimeout(1000);
    await expect(page).toHaveScreenshot('dashboard.png', { maxDiffPixels: 500 });
  });

  test('alert detail visual snapshot', async ({ page }) => {
    await page.goto('/alerts/1');
    await page.waitForTimeout(1000);
    await expect(page).toHaveScreenshot('alert-detail.png', { maxDiffPixels: 500 });
  });

  test('dark mode visual snapshot', async ({ page }) => {
    // Assuming dark mode is default or we can toggle it
    await page.goto('/dashboard');
    // We can evaluate localStorage to force dark mode
    await page.evaluate(() => localStorage.setItem('theme', 'dark'));
    await page.reload();
    await page.waitForTimeout(1000);
    await expect(page).toHaveScreenshot('dashboard-dark.png', { maxDiffPixels: 500 });
  });

  test('light mode visual snapshot', async ({ page }) => {
    await page.goto('/dashboard');
    await page.evaluate(() => localStorage.setItem('theme', 'light'));
    await page.reload();
    await page.waitForTimeout(1000);
    await expect(page).toHaveScreenshot('dashboard-light.png', { maxDiffPixels: 500 });
  });
});
