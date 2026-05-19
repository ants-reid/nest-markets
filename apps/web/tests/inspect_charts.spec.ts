import { test, expect } from '@playwright/test';

test('inspect charts and svgs', async ({ page }) => {
  const paths = ['/analytics', '/alerts'];
  for (const path of paths) {
    console.log(`\n--- Path: ${path} ---`);
    try {
      await page.goto(path);
      // Wait for network idle to ensure chart loads
      await page.waitForLoadState('networkidle');
      
      const chartSelector = '[aria-label="Time series chart"]';
      const chart = await page.locator(chartSelector).first();
      const exists = (await chart.count()) > 0;
      console.log(`Exists: ${exists}`);

      if (exists) {
        const outerHTML = await chart.evaluate(el => el.outerHTML);
        console.log(`OuterHTML (first 800): ${outerHTML.substring(0, 800)}`);
        
        const pathCount = await chart.locator('path').count();
        const circleCount = await chart.locator('circle').count();
        console.log(`Path count: ${pathCount}`);
        console.log(`Circle count: ${circleCount}`);
      } else {
          // Check for empty state text near where chart should be or in main container
          const bodyText = await page.innerText('body');
          console.log(`Body text snippet (first 200): ${bodyText.substring(0, 200).replace(/\n/g, ' ')}`);
      }
    } catch (e) {
      console.log(`Error navigating to ${path}: ${e.message}`);
    }
  }
});
