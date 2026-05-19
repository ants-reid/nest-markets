import { test, expect } from '@playwright/test';

test('inspect overflow', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000/');
  
  const metrics = await page.evaluate(() => {
    const innerWidth = window.innerWidth;
    const scrollWidth = document.documentElement.scrollWidth;
    
    const elements = Array.from(document.querySelectorAll('*'));
    const overflows = elements
      .map(el => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName,
          id: el.id,
          className: el.className,
          text: el.textContent?.slice(0, 30).trim() || '',
          width: rect.width,
          right: rect.right,
          left: rect.left
        };
      })
      .filter(el => el.right > innerWidth || el.width > innerWidth)
      .sort((a, b) => b.right - a.right)
      .slice(0, 10);

    const nav = document.querySelector('nav');
    const navRect = nav ? nav.getBoundingClientRect() : null;
    const navOverflows = navRect ? (navRect.right > innerWidth || navRect.width > innerWidth) : false;

    return {
      innerWidth,
      scrollWidth,
      overflows,
      navOverflows
    };
  });

  console.log(JSON.stringify(metrics, null, 2));
});
