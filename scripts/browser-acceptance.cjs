/* Run against backend.demo_server only; no external banking site is accessed. */
const {chromium}=require(process.env.VC_PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs');const path=require('path');const assert=require('assert');
const origin=process.env.VC_BROWSER_ORIGIN||'http://localhost:3001';
const output=path.resolve('docs/reports/final-acceptance-20261029/browser');fs.mkdirSync(output,{recursive:true});
const password='Synthetic-Test-Only-2026!';
const results=[];
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.VC_BROWSER_EXECUTABLE||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
  try{
    for(const language of ['vi','en'])for(const [account,role] of [['customer1','Customer'],['agent1','Agent'],['supervisor','Supervisor'],['admin','Admin']]){
      const context=await browser.newContext({viewport:{width:1366,height:900},locale:language==='vi'?'vi-VN':'en-GB'});
      // The local UI must remain usable when the external font CDN is unavailable.
      await context.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//,route=>route.abort());
      const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
      await page.goto(`${origin}/${language==='vi'?'VI':'EN'}/login-${language}.html`);
      await page.locator('#loginEmail').fill(`${account}@demo.invalid`);await page.locator('#loginPassword').fill(password);
      await page.locator('form button[type=submit]').click();await page.waitForURL(url=>!url.pathname.includes('login-'));
      const base=`${origin}/${language==='vi'?'VI':'EN'}`;
      await page.goto(`${base}/account-${language}.html`);
      await page.waitForFunction(()=>window.VietinWorkspace?.ready);
      const user=await page.evaluate(()=>window.VietinWorkspace.ready);assert.equal(user.role,role);
      if(role==='Agent')await page.locator('#presenceStatus').filter({hasText:language==='vi'?'Sẵn sàng':'Available'}).waitFor();
      if(role==='Supervisor'){await page.locator('#supervisorAutomation').waitFor();await page.locator('#reportPriorityList li').first().waitFor();}
      if(role==='Admin')await page.locator('input[data-key="auth.session_hours"]').waitFor();
      if(role==='Agent'||role==='Supervisor'){
        await page.locator('.support-queue details summary').first().click();
        await page.locator('.handover-messages article').first().waitFor();
      }
      await page.screenshot({path:path.join(output,`${role}-${language}-desktop.png`)});
      if(role==='Customer'){
        await page.goto(`${base}/chat-${language}.html`);await page.locator('#chatForm').waitFor({state:'visible'});
        await page.locator('#messageInput').fill('Tôi cần hướng dẫn đăng nhập bản demo.');await page.locator('#chatForm button[type=submit]').click();
        await page.waitForURL(/#[1-9]\d*$/);await page.locator('.message').filter({hasText:'[SIMULATION]'}).first().waitFor();
        await page.clock.install();
        await page.locator('#closeChat').click();await page.locator('#chatEvaluation').waitFor({state:'visible'});
        await page.clock.fastForward(61000);assert(await page.locator('#chatEvaluation').isHidden(),'Chat rating must hide after 60 seconds');
        await page.reload();await page.locator('#chatEvaluation').waitFor({state:'visible'});
        await page.locator('#chatEvaluation form button[type=submit]').click();await page.locator('#chatEvaluation p').filter({hasText:language==='vi'?'Cảm ơn':'Thank you'}).waitFor();
      }
      if(role==='Agent'){
        await page.goto(`${base}/tickets-${language}.html`);await page.locator('#createCustomer').waitFor();
        await page.locator('#title').fill('Tài khoản bức xúc — browser acceptance');await page.locator('#content').fill('Tôi bức xúc và cần được hướng dẫn đăng nhập demo.');
        await page.locator('#createForm button[type=submit]').click();await page.waitForURL(/#[1-9]\d*$/);
        // The asynchronous classifier may finish before or just after the first detail load.
        await page.getByRole('button',{name:language==='vi'?/^Nhận (ca được giao|yêu cầu)$/:/^(Accept assigned ticket|Claim ticket)$/}).click();
        await page.getByRole('button',{name:language==='vi'?'Phân tích và gợi ý bằng AI':'Analyze with AI',exact:true}).click();
        await page.locator('#aiDraft').waitFor();await page.getByRole('button',{name:language==='vi'?'Dùng bản nháp':'Use draft',exact:true}).click();
        assert((await page.locator('#reply').inputValue()).includes('[SIMULATION]'));
        await page.getByRole('button',{name:language==='vi'?'Gửi phản hồi':'Send reply',exact:true}).click();
        await page.locator('.reply').filter({hasText:'[SIMULATION]'}).first().waitFor();
      }
      await page.goto(`${base}/account-${language}.html`);await page.waitForFunction(()=>window.VietinWorkspace?.ready);await page.evaluate(()=>window.VietinWorkspace.ready);
      await page.setViewportSize({width:390,height:844});
      await page.reload();
      await page.waitForFunction(()=>window.VietinWorkspace?.ready);await page.evaluate(()=>window.VietinWorkspace.ready);
      await page.evaluate(()=>document.fonts.ready);
      await page.locator('.menu-toggle').waitFor();
      await page.waitForFunction(()=>document.querySelector('.sidebar').getBoundingClientRect().right<=1);
      await page.locator('.menu-toggle').click();
      await page.waitForFunction(()=>document.body.classList.contains('nav-open'));
      await page.keyboard.press('Escape');
      await page.waitForFunction(()=>!document.body.classList.contains('nav-open')&&document.querySelector('.sidebar').getBoundingClientRect().right<=1);
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2);
      assert(!overflow,`${role}/${language} mobile horizontal overflow`);
      await page.screenshot({path:path.join(output,`${role}-${language}-mobile.png`)});
      assert.equal(errors.length,0,errors.join('\n'));
      results.push({language,role,desktop:'PASS',mobile:'PASS',page_errors:errors,workflow:'PASS'});
      await context.close();
    }
  }finally{await browser.close();fs.writeFileSync(path.join(output,'result.json'),JSON.stringify({origin,provider:'SIMULATION',results,completed:results.length===8},null,2));}
  console.log(JSON.stringify({status:'PASS',contexts:results.length,desktop_mobile_checks:results.length*2,page_errors:0}));
})().catch(error=>{console.error(error.stack);process.exit(1);});
