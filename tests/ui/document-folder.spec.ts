import {test, expect} from '@playwright/test';

test('document folder has clear path, explicit indexing and actionable errors', async ({page}) => {
  const posts: string[] = [];
  await page.route('**/api/rag/**', async route => {
    const path = new URL(route.request().url()).pathname.split('/api/rag/')[1];
    if (route.request().method() === 'POST') posts.push(path);
    const data = path === 'health' ? {online:true,index:{documents:0,document_chunks:0},model:{state:'not_configured'}}
      : path === 'document-folder' ? {path:'D:\\Documentos RAG',formats:['.pdf','.txt']}
      : path === 'index-jobs' ? {job_id:'test1'}
      : path === 'index-jobs/test1' ? {state:'completed',report:{documents:{added:1,updated:0,removed:0,errors:['scan.pdf: Página 1 precisa de OCR']}}}
      : {opened:true};
    await route.fulfill({json:data});
  });
  await page.goto('/#rag');
  await expect(page.getByLabel('Caminho da pasta de documentos')).toHaveValue('D:\\Documentos RAG');
  expect(posts).toEqual([]);
  await page.getByRole('button',{name:'Abrir pasta no Windows'}).click();
  await page.getByRole('button',{name:'Indexar pasta agora'}).click();
  await expect(page.getByRole('status').filter({hasText:'scan.pdf'})).toBeVisible();
  expect(posts).toEqual(['document-folder/open','index-jobs']);
  await page.screenshot({path:'.local/screenshots/document-folder-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'.local/screenshots/document-folder-mobile.png',fullPage:true});
});
