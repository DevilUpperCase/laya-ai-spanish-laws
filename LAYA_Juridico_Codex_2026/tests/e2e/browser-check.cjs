/* Real local UI/API workflow. Private records are synthetic and removed after the run. */
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const {chromium}=require('../../apps/web/node_modules/playwright');
const root=path.resolve(__dirname,'../..');
const output=path.join(root,'output/playwright');
fs.mkdirSync(output,{recursive:true});
const runId=String(Date.now());
const pdfName=`browser-acceptance-${runId}.pdf`;
const docxName=`browser-acceptance-${runId}.docx`;
const folderName=`Browser acceptance ${runId} folder`;
const notebookName=`Browser acceptance ${runId} notebook`;

const isSearchResponse=response=>{
 try{return new URL(response.url()).pathname==='/api/v1/search'&&response.request().method()==='POST';}
 catch{return false;}
};

(async()=>{
 const session=JSON.parse(fs.readFileSync(path.join(root,'private-data/local-session.json'),'utf8'));
 const credentials=JSON.parse(fs.readFileSync(path.join(root,'private-data/login-credentials.json'),'utf8'));
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1360,height:1000}});
 const page=await context.newPage();
 const errors=[];
 let pdfId,docxId,bookUrl;
 page.on('pageerror',error=>errors.push(error.name));

 async function search(scope){
  const pending=page.waitForResponse(isSearchResponse,{timeout:180000});
  await page.getByRole('button',{name:'Buscar',exact:true}).click();
  const response=await pending;
  assert.equal(response.status(),200,`Search request for ${scope} must succeed`);
  const body=JSON.parse(response.request().postData());
  assert.equal(body.scope,scope,`Search request must submit the selected ${scope} scope`);
  await page.locator('.results-heading').waitFor({timeout:30000});
  return response.json();
 }

 async function moveToTrash(documentId){
  await page.goto(`http://127.0.0.1:3000/documents/${documentId}`);
  await page.getByRole('button',{name:'Mover a Papelera',exact:true}).click();
  await page.getByRole('heading',{name:'Mover este documento a Papelera'}).waitFor();
  await page.getByRole('button',{name:'Confirmar traslado a Papelera'}).click();
  await page.waitForURL('**/documents');
 }

 try{
  await page.goto('http://127.0.0.1:3000');
  await page.getByLabel('Correo electrónico').waitFor();
  await page.screenshot({path:path.join(output,'login.png'),fullPage:false});
  await page.getByLabel('Correo electrónico').fill(credentials.email);
  await page.getByLabel('Contraseña',{exact:true}).fill(credentials.password);
  await page.getByRole('button',{name:'Entrar al espacio'}).click();
  await page.getByRole('heading',{name:'Encuentra la norma. Comprueba la fuente.'}).waitFor();
  console.log('Browser check: authenticated');
  const workspace=page.getByLabel('Espacio de trabajo');
  if(await workspace.count()){
   const options=await workspace.locator('option').evaluateAll(nodes=>nodes.map(node=>node.value));
   if(options.includes(session.tenant_id))await workspace.selectOption(session.tenant_id);
  }
  await page.reload();
  await page.getByRole('heading',{name:'Encuentra la norma. Comprueba la fuente.'}).waitFor();
  assert.equal(await page.getByRole('radio',{name:'Normativa'}).isChecked(),true,'Normativa is the default search scope');
  await page.getByLabel('Consulta jurídica').fill('arrendamiento vivienda');
  const normative=await search('normative');
  console.log('Browser check: normative search passed');
  assert(normative.results.length>0,'Normative search must return official corpus results');
  assert(await page.getByText('Cobertura nacional pendiente de auditoría.',{exact:false}).count()>0);
  const sources=await page.locator('.result-bottom a').evaluateAll(links=>links.map(a=>a.href).filter(url=>url.includes('boe.es')));
  assert(sources.length>0&&sources.every(url=>new URL(url).hostname==='www.boe.es'));
  await page.screenshot({path:path.join(output,'search-desktop.png'),fullPage:false});

  await page.getByRole('radio',{name:'Todas las publicaciones'}).check();
  await search('all_publications');
  console.log('Browser check: all-publications search passed');
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'Mobile layout overflow');
  await page.screenshot({path:path.join(output,'search-mobile.png'),fullPage:false});
  await page.setViewportSize({width:1360,height:1000});

  await page.getByRole('link',{name:'Cobertura',exact:true}).click();
  await page.getByRole('heading',{name:'Fuentes registradas'}).waitFor();
  assert(await page.getByText('Primer lanzamiento bloqueado').count()>0);
  await page.screenshot({path:path.join(output,'coverage.png'),fullPage:false});

  await page.getByRole('link',{name:'Documentos',exact:true}).click();
  await page.getByLabel('Nombre de carpeta o cuaderno').fill(folderName);
  await page.getByRole('button',{name:'Crear carpeta'}).click();
  await page.locator('.library > .document-toolbar select').selectOption({label:folderName});
  await page.getByLabel('Nombre de carpeta o cuaderno').fill(notebookName);
  await page.getByRole('button',{name:'Crear cuaderno'}).click();
  const notebookLink=page.getByRole('link',{name:notebookName,exact:true});
  await notebookLink.waitFor();
  bookUrl=await notebookLink.getAttribute('href');
  assert(bookUrl,'Created notebook must have a workspace link');
  console.log('Browser check: folder and notebook created');

  const pdf=fs.readFileSync(path.join(root,'private-data/browser-synthetic.pdf'));
  await page.getByLabel('Archivo PDF o DOCX').setInputFiles({name:pdfName,mimeType:'application/pdf',buffer:pdf});
  await page.getByRole('button',{name:'Cargar y procesar'}).click();
  await page.getByLabel('Texto del documento').waitFor({timeout:120000});
  pdfId=new URL(page.url()).pathname.split('/').pop();
  console.log('Browser check: PDF extracted');
  assert.equal(await page.locator('iframe[title="Vista del documento original PDF"]').count(),1,'Uploaded PDF preview must open');

  await page.getByLabel('Texto del documento').evaluate(el=>{
   const start=el.value.indexOf('vivienda');
   if(start<0)throw new Error('Synthetic PDF fixture text missing');
   el.focus();el.setSelectionRange(start,start+7);
  });
  await page.keyboard.press('Shift+ArrowRight');
  await page.getByRole('button',{name:'Buscar normativa relacionada'}).click();
  await page.locator('.result-card').first().waitFor({timeout:180000});
  await page.locator('section.panel label select').selectOption({label:notebookName});
  await page.getByLabel('Tu nota').fill(`Nota vinculada a la selección ${runId}`);
  await page.getByRole('button',{name:'Guardar nota vinculada'}).click();
  await page.locator('.results > label select').selectOption({label:notebookName});
  await page.getByRole('button',{name:'Guardar referencia'}).first().click();
  await page.getByText('Referencia guardada en el cuaderno.',{exact:true}).waitFor();

  await page.getByRole('link',{name:'Documentos',exact:true}).click();
  const pdfCard=page.locator('.library-file').filter({hasText:pdfName});
  await pdfCard.getByLabel('Mover a carpeta').selectOption({label:folderName});
  await page.getByRole('link',{name:notebookName,exact:true}).click();
  await page.getByLabel('Nota del cuaderno').fill(`Nota general inicial ${runId}`);
  await page.getByRole('button',{name:'Guardar nota',exact:true}).click();
  await page.getByText(`Nota general inicial ${runId}`,{exact:true}).waitFor();
  const generalNote=page.locator('.notebook-note').filter({hasText:`Nota general inicial ${runId}`});
  await generalNote.getByRole('button',{name:'Editar nota'}).click();
  await page.getByLabel('Nota del cuaderno').fill(`Nota general editada ${runId}`);
  await page.getByRole('button',{name:'Guardar cambios'}).click();
  await page.getByText(`Nota general editada ${runId}`,{exact:true}).waitFor();
  await page.reload();
  await page.getByText(`Nota general editada ${runId}`,{exact:true}).waitFor();
  await page.getByText(`Nota vinculada a la selección ${runId}`,{exact:true}).waitFor();
  await page.getByRole('link',{name:'Referencia oficial guardada'}).waitFor();
  console.log('Browser check: notes and references saved, edited, and reloaded');

  const word=fs.readFileSync(path.join(root,'private-data/browser-synthetic.docx'));
  await page.getByRole('link',{name:'Documentos',exact:true}).click();
  await page.getByLabel('Archivo PDF o DOCX').setInputFiles({name:docxName,mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer:word});
  await page.getByRole('button',{name:'Cargar y procesar'}).click();
  await page.getByLabel('Texto del documento').waitFor({timeout:120000});
  docxId=new URL(page.url()).pathname.split('/').pop();
  const documentText=await page.getByLabel('Texto del documento').inputValue();
  assert(documentText.includes('🏠')&&documentText.includes('habitación'),'DOCX extraction must preserve Unicode text');
  await page.goto(`http://127.0.0.1:3000/documents/${docxId}?page=1`);
  await page.getByLabel('Texto del documento').waitFor();
  assert.equal(await page.getByLabel('Página / sección lógica').inputValue(),'0','Page query must select the requested first page');
  const targetOffsets=await page.getByLabel('Texto del documento').evaluate(el=>{
   const value=el.value;const phrase='arrendamiento';const start=value.indexOf(phrase);if(start<0)throw new Error('Unicode selection target missing');
   return {start,end:start+phrase.length,codePointStart:Array.from(value.slice(0,start)).length,codePointEnd:Array.from(value.slice(0,start+phrase.length)).length};
  });
  await page.getByLabel('Texto del documento').evaluate((el,range)=>{el.focus();el.setSelectionRange(range.start,range.end-1);},targetOffsets);
  await page.keyboard.press('Shift+ArrowRight');
  const selectionRequest=page.waitForRequest(request=>request.url().includes(`/api/v1/documents/${docxId}/search-related`)&&request.method()==='POST',{timeout:180000});
  await page.getByRole('button',{name:'Buscar normativa relacionada'}).click();
  const selectionPayload=JSON.parse((await selectionRequest).postData());
  assert.equal(selectionPayload.start_offset,targetOffsets.codePointStart,'Selection start must use Unicode code-point offsets');
  assert.equal(selectionPayload.end_offset,targetOffsets.codePointEnd,'Selection end must use Unicode code-point offsets');
  assert.equal(selectionPayload.selected_text,'arrendamiento');
  await page.locator('.result-card').first().waitFor({timeout:180000});
  console.log('Browser check: Unicode selection offsets matched');

  await page.goto('http://127.0.0.1:3000');
  await page.getByRole('heading',{name:'Encuentra la norma. Comprueba la fuente.'}).waitFor();
  await page.getByRole('button',{name:'Adjuntar documentos del espacio'}).click();
  await page.getByRole('checkbox',{name:new RegExp(pdfName)}).check();
  await page.getByRole('checkbox',{name:new RegExp(docxName)}).check();
  const attachmentScope=page.getByRole('radio',{name:'Documentos adjuntos'});
  await attachmentScope.waitFor();
  assert.equal(await attachmentScope.isEnabled(),true,'Attachments scope should enable for ready selected documents');
  await attachmentScope.check();
  await page.getByLabel('Consulta jurídica').fill('arrendamiento vivienda');
  const attached=await search('attachments');
  console.log('Browser check: attachment search passed');
  assert(attached.private_results?.length>0,'Attachment search must return source-backed private passages');
  assert.equal(attached.results.length,0,'Attachments mode must not mix in public legal results');
  const readerLink=page.getByRole('link',{name:'Ver documento original'}).first();
  const privateTarget=await readerLink.getAttribute('href');
  assert.match(privateTarget,/\?page=\d+/,'Private passage link must carry its source page');
  await page.goto(new URL(privateTarget,'http://127.0.0.1:3000').href);
  await page.getByLabel('Texto del documento').waitFor();
  assert.equal(await page.getByLabel('Página / sección lógica').inputValue(),'0','Private passage link must open its cited page');

  await moveToTrash(pdfId);
  await page.goto('http://127.0.0.1:3000');
  await page.getByRole('button',{name:'Adjuntar documentos del espacio'}).click();
  assert.equal(await page.getByRole('checkbox',{name:new RegExp(pdfName)}).count(),0,'Trashed documents must be absent from attachment choices');
  await page.goto('http://127.0.0.1:3000/trash');
  const trashedPdf=page.locator('.library-file').filter({hasText:pdfName});
  const trashPreviewResponse=page.waitForResponse(response=>{
   try{const url=new URL(response.url());return url.pathname===`/api/v1/documents/${pdfId}/preview`&&url.searchParams.get('trash')==='true';}
   catch{return false;}
  });
  await trashedPdf.getByRole('link',{name:pdfName}).click();
  await page.getByText(/En Papelera: puedes restaurar este documento/).waitFor();
  assert.equal((await trashPreviewResponse).status(),200,'Trash preview must use its explicit authorization route');
  await page.locator('iframe[title="Vista del documento original PDF"]').waitFor({state:'visible'});
  await page.goto('http://127.0.0.1:3000/trash');
  await page.locator('.library-file').filter({hasText:pdfName}).getByRole('button',{name:'Restaurar'}).click();
  await page.locator('.library-file').filter({hasText:pdfName}).waitFor({state:'detached'});

  await moveToTrash(pdfId);
  await page.goto('http://127.0.0.1:3000/trash');
  page.once('dialog',dialog=>dialog.accept());
  await page.locator('.library-file').filter({hasText:pdfName}).getByRole('button',{name:'Eliminar permanentemente'}).click();
  await page.locator('.library-file').filter({hasText:pdfName}).waitFor({state:'detached'});
  const permanentlyDeleted=await context.request.get(`http://127.0.0.1:3000/api/v1/documents/${pdfId}`,{headers:{'X-Tenant-ID':session.tenant_id}});
  assert.equal(permanentlyDeleted.status(),404,'Permanent deletion must revoke document access');

  await moveToTrash(docxId);
  await page.goto('http://127.0.0.1:3000/trash');
  page.once('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'Vaciar Papelera'}).click();
  await page.locator('.library-file').filter({hasText:docxName}).waitFor({state:'detached'});
  console.log('Browser check: trash, restore, permanent delete, and empty trash passed');
  const emptied=await context.request.get(`http://127.0.0.1:3000/api/v1/documents/${docxId}`,{headers:{'X-Tenant-ID':session.tenant_id}});
  assert.equal(emptied.status(),404,'Empty trash must revoke document access');

  await page.getByRole('button',{name:'Cerrar sesión'}).click();
  await page.getByLabel('Correo electrónico').waitFor();
  assert.equal((await context.request.get('http://127.0.0.1:3000/api/auth/session')).status(),401);
  assert.deepEqual(errors,[]);
  const report={status:'passed',generated_at:new Date().toISOString(),real_api:true,real_database:true,search_scopes:['normative','all_publications','attachments'],
    checks:['password-login','workspace-selection','session-refresh','official-search','publication-scope','coverage-warning','mobile-overflow',
      'folder-organization','notebook-create','linked-note-save','general-note-create-edit-reload','reference-save','pdf-preview','docx-utf8-extraction',
      'unicode-codepoint-selection','attachment-search','cited-page-navigation','trash-hides-attachment','trash-preview','restore','permanent-delete',
      'empty-trash','logout-revokes-session'],
    limitations:['Synthetic private files only. Reader write-denial is covered by the database integration test. Not a WCAG audit or professional legal evaluation.','LAYA shadow may time out under the configured two-second budget.']};
  fs.writeFileSync(path.join(root,'verification/reports/browser-check.json'),JSON.stringify(report,null,2));
  await page.screenshot({path:path.join(output,'search-final.png'),fullPage:false});
  console.log(JSON.stringify(report));
 }finally{
  await context.close();
  await browser.close();
  const cleanup=execFileSync(path.join(root,'.venv','Scripts','python.exe'),['scripts/cleanup_browser_fixtures.py','--run-id',runId],{cwd:root,encoding:'utf8'});
  process.stdout.write(cleanup);
 }
})().catch(error=>{console.error('Browser check failed:',error.name,error.message.replace(/Bearer\s+\S+/g,'Bearer [redacted]'));process.exitCode=1;});
