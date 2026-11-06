import {test,expect} from '@playwright/test';
test('offline dataset, assessment review and validation',async({page})=>{
 const token='e2e-token-'.repeat(6);
 await page.goto('/');
 await page.getByLabel('Local backend port').fill('8765');
 await page.getByLabel('Session token').fill(token);
 await page.getByRole('button',{name:'Connect to workspace'}).click();
 await page.getByRole('button',{name:'Load offline demo'}).click();
 await expect(page.getByText('Synthetic demonstration',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Inspect →'}).click();
 await expect(page.getByText('Prediction model with shared code',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Start article assessment →'}).click();
 await expect(page.getByText('6 / 6 records processed')).toBeVisible();
 await page.getByRole('button',{name:'Compare with human annotations →'}).click();
 await expect(page.getByRole('heading',{name:'Comparison with human annotations'})).toBeVisible();
 await expect(page.getByRole('cell',{name:'Is match',exact:true})).toBeVisible();
 await page.screenshot({path:'test-results/workspace-validation.png',fullPage:true});
});
