/* Real local UI/API test. Synthetic private fixture; no traced headers or credential output. */
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {chromium}=require('../../apps/web/node_modules/playwright');
const root=path.resolve(__dirname,'../..');
const output=path.join(root,'output/playwright');
fs.mkdirSync(output,{recursive:true});

(async()=>{
 const session=JSON.parse(fs.readFileSync(path.join(root,'private-data/local-session.json'),'utf8'));
 const credentials=JSON.parse(fs.readFileSync(path.join(root,'private-data/login-credentials.json'),'utf8'));
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1360,height:1000}});
 const page=await context.newPage();
 const errors=[];
 page.on('pageerror',error=>errors.push(error.name));
 try{
  await page.goto('http://127.0.0.1:3000');
  await page.getByLabel('Correo electrónico').waitFor();
  await page.screenshot({path:path.join(output,'login.png'),fullPage:false});
  await page.getByLabel('Correo electrónico').fill(credentials.email);
  await page.getByLabel('Contraseña',{exact:true}).fill(credentials.password);
  await page.getByRole('button',{name:'Entrar al espacio'}).click();
  await page.getByRole('heading',{name:'Encuentra la norma. Comprueba la fuente.'}).waitFor();
  await page.reload();
  await page.getByRole('heading',{name:'Encuentra la norma. Comprueba la fuente.'}).waitFor();
  await page.getByLabel('Consulta jurídica').fill('arrendamiento vivienda');
  await page.getByRole('button',{name:'Buscar',exact:true}).click();
  await page.getByRole('heading',{name:/extractos encontrados/}).waitFor({timeout:180000});
  const count=await page.locator('.result-card').count();
  assert(count>0,'Real corpus search must return results');
  assert(await page.getByText('Cobertura nacional pendiente de auditoría.',{exact:false}).count()>0);
  const sources=await page.locator('.result-bottom a').evaluateAll(links=>links.map(a=>a.href));
  assert(sources.every(url=>new URL(url).hostname==='www.boe.es'));
  await page.screenshot({path:path.join(output,'search-desktop.png'),fullPage:false});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'Mobile layout overflow');
  await page.screenshot({path:path.join(output,'search-mobile.png'),fullPage:false});
  await page.setViewportSize({width:1360,height:1000});
  await page.getByRole('link',{name:'Cobertura',exact:true}).click();
  await page.getByRole('heading',{name:'Fuentes registradas'}).waitFor();
  assert(await page.getByText('Primer lanzamiento bloqueado').count()>0);
  await page.screenshot({path:path.join(output,'coverage.png'),fullPage:false});
  await page.getByRole('link',{name:'Documentos',exact:true}).click();
  await page.getByLabel('Archivo PDF o DOCX').setInputFiles(path.join(root,'private-data/browser-synthetic.pdf'));
  await page.getByRole('button',{name:'Cargar y procesar'}).click();
  await page.getByLabel('Texto del documento').waitFor({timeout:120000});
  const documentUrl=page.url();
  await page.getByLabel('Texto del documento').evaluate(el=>{
    const start=el.value.indexOf('vivienda');
    if(start<0)throw new Error('Synthetic fixture text missing');
    el.focus();el.setSelectionRange(start,start+7);
  });
  await page.keyboard.press('Shift+ArrowRight');
  await page.getByRole('button',{name:'Buscar normativa relacionada'}).click();
  await page.locator('.result-card').first().waitFor({timeout:180000});
  await page.getByRole('button',{name:'Eliminar documento',exact:true}).click();
  await page.getByRole('button',{name:'Confirmar eliminación'}).click();
  await page.getByRole('heading',{name:'Cargar un documento'}).waitFor();
  // Client navigation retains only in-memory login; a previously known document URL loses access.
  const documentId=documentUrl.split('/').pop();
  const response=await context.request.get('http://127.0.0.1:3000/api/v1/documents/'+documentId,{headers:{'X-Tenant-ID':session.tenant_id}});
  assert.equal(response.status(),404);
  await page.getByRole('button',{name:'Cerrar sesión'}).click();
  await page.getByLabel('Correo electrónico').waitFor();
  assert.equal((await context.request.get('http://127.0.0.1:3000/api/auth/session')).status(),401);
  assert.deepEqual(errors,[]);
  const report={status:'passed',generated_at:new Date().toISOString(),real_api:true,real_database:true,search_results:count,
    checks:['password-login','refresh-keeps-session','logout-revokes-session','official-corpus-search','official-source-links','visible-coverage-blocker','mobile-overflow','coverage-page','PDF-upload','durable-extraction','stored-selection-search','deletion-revokes-access'],
    limitations:['Synthetic private PDF only. Not a WCAG audit or professional legal evaluation.','LAYA shadow may time out under the configured two-second budget.']};
  fs.writeFileSync(path.join(root,'verification/reports/browser-check.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));
 }finally{await context.close();await browser.close();}
})().catch(error=>{console.error('Browser check failed:',error.name,error.message.replace(/Bearer\s+\S+/g,'Bearer [redacted]'));process.exitCode=1;});
