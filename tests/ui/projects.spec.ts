import {test,expect} from '@playwright/test';

test('Projects sends the same durable request contract and retains input on offline rejection',async({page})=>{
  const bodies:Record<string,unknown>[]=[];
  let offline=false;
  const conv={id:'conversation-1',title:'Verificar grid',state:'planning',updated_at:1792500000,messages:[{seq:1,author:'user',text:'Verificar grid'}],plans:[],runs:[],jobs:[]};
  await page.route('**/api/orchestrator/v1/**',async route=>{
    const request=route.request();
    const path=new URL(request.url()).pathname;
    if(request.method()==='POST'){
      bodies.push(request.postDataJSON());
      expect(request.headers()['x-orchestrator-request']).toBe('1');
      await route.fulfill({status:offline?503:202,json:offline?{message:'Abra o Orquestrador no BATCOMPUTADOR'}:conv});return;
    }
    await route.fulfill({json:path.endsWith('/runtime')?{online:true,planning_routing:{version:1,pipeline_version:1,execution_agents:['claude','codex','antigravity'],agents:['codex','antigravity'],execution_agent:'claude'}}:path.endsWith('/conversations')?{conversations:bodies.length?[conv]:[]}:conv});
  });
  await page.goto('/#projects');
  await expect(page.getByText('Orquestrador disponível neste PC')).toBeVisible();
  await page.getByLabel('Pedido para o Jarvis').fill('Verificar grid');
  offline=true;
  await page.getByRole('button',{name:'Enviar ao Jarvis'}).click();
  await expect(page.getByRole('alert')).toContainText('Abra o Orquestrador');
  await expect(page.getByLabel('Pedido para o Jarvis')).toHaveValue('Verificar grid');
  offline=false;
  await page.getByRole('button',{name:'Enviar ao Jarvis'}).click();
  await expect(page.getByRole('heading',{name:'Verificar grid'})).toBeVisible();
  expect(bodies[0].request_id).toBe(bodies[1].request_id);
  expect(bodies[0].project).toBe('dicevtt');
  await page.screenshot({path:'.local/screenshots/projects-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth)).toBe(false);
});

