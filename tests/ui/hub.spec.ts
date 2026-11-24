import {test,expect} from '@playwright/test';

test('home opens Projects with the draft and HUD adapts to mobile',async({page})=>{
 await page.goto('/#home');
 await expect(page.getByRole('heading',{name:'À sua disposição.'})).toBeVisible();
 await page.screenshot({path:'.local/screenshots/jarvis-home-desktop.png',fullPage:true});
 await page.getByLabel('Objetivo do projeto').fill('Verificar regras do grid');
 await page.getByRole('button',{name:'Abrir em Projetos'}).click();
 await expect(page.getByLabel('Pedido para o Jarvis')).toHaveValue('Verificar regras do grid');
 await page.setViewportSize({width:390,height:844});await page.goto('/#home');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
 await page.screenshot({path:'.local/screenshots/jarvis-home-mobile.png',fullPage:true});
});

test('catalog requires a concrete review before any execution',async({page})=>{
 let executed=0;
 await page.route('**/api/orchestrator/v1/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  let json:unknown={accounts:[],runtime_enabled:false,message:''};
  if(path.endsWith('/extensions'))json={configured:true,entries:[{id:'notion',enabled:true}]};
  if(path.endsWith('/prepare'))json={id:'a'.repeat(32),digest:'b'.repeat(64),connection:'notion',tool:'search_pages',arguments:{query:'example'},message:'Revise os argumentos.'};
  if(path.endsWith('/execute')){executed++;json={status:'completed',result:[]};}
  await route.fulfill({json});
 });
 await page.goto('/#connections');
 await page.getByLabel('Buscar integração').fill('Notion');
 await page.locator('.catalog-item').filter({hasText:'Notion'}).first().click();
 await expect(page.getByRole('dialog')).toBeVisible();
 await page.getByRole('button',{name:'Preparar chamada'}).click();
 expect(executed).toBe(0);
 await expect(page.getByText('Revise os argumentos.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Confirmar esta execução'}).click();
 await expect(page.getByRole('status')).toContainText('completed');
 expect(executed).toBe(1);
 await page.getByLabel('Fechar detalhes').press('Escape');
 await expect(page.getByRole('dialog')).toHaveCount(0);
});
