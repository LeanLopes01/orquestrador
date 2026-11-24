import { test, expect } from '@playwright/test';

test('service screens and explicit report planning fit desktop and mobile',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'À sua disposição.'})).toBeVisible();
 const nav=page.getByRole('navigation',{name:'Navegação principal'});
 await expect(nav.getByRole('button')).toHaveText(['Central Jarvis','Projects · Jarvis','Janela de contexto','RAG local','Ingestão de fontes','Relatórios','Contas e integrações','Rotinas','Atualizações','Sistema']);
 for(const old of ['overview','tasks','runs','review','settings']){
  await page.goto(`/#${old}`);await expect(page.getByRole('heading',{name:'À sua disposição.'})).toBeVisible();
 }
 await expect(page.getByText('Demonstração ativa')).toHaveCount(0);
 for(const width of [1440,1024,390]){
  await page.setViewportSize({width,height:900});
  for(const route of ['home','projects','context','rag','ingestion','reports','connections','routines','updates','system']){
   await page.goto(`/#${route}`);await expect(page.locator('h1').first()).toBeVisible();
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);expect(overflow,`${route} at ${width}px overflows`).toBe(false);
  }
 }
 expect(errors).toEqual([]);
});

test('real local context loads, filters, selects and exports sources',async({page})=>{
 await page.goto('/#context');
 await expect(page.getByRole('button',{name:'Atualizar fontes',exact:true})).toBeEnabled({timeout:20000});
 const sources=page.locator('.source-row');expect(await sources.count()).toBeGreaterThan(0);
 await sources.first().click();await page.getByRole('button',{name:'Usar no contexto'}).click();
 await expect(page.getByRole('button',{name:'Selecionada',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Atualizar fontes',exact:true}).click();
 await expect(page.getByRole('button',{name:'Atualizar fontes',exact:true})).toBeEnabled();
 await expect(page.getByRole('button',{name:'Selecionada',exact:true})).toBeVisible();
 await page.getByLabel('Buscar nas fontes').fill('nonexistent-fixture-12345');await expect(page.getByText('Nenhuma fonte encontrada.')).toBeVisible();
 const pending=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar contexto'}).click();const download=await pending;
 const stream=await download.createReadStream();let text='';for await(const chunk of stream!)text+=chunk.toString();expect(text.length).toBeLessThanOrEqual(6000);expect(text).toContain('SHA256:');
});

test('context fails explicitly and rejects cross-origin requests',async({page,request})=>{
 await page.route('**/api/context',route=>route.fulfill({status:503,body:'{}',contentType:'application/json'}));
 await page.goto('/#context');await expect(page.getByRole('alert')).toContainText('indisponível');
 const response=await request.get('/api/context',{headers:{Origin:'https://untrusted.example'}});expect(response.status()).toBe(403);
});
