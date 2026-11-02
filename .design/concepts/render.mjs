import { chromium } from '../../desktop/web_bridge/vendor/playwright-core/index.mjs';
import { fileURLToPath } from 'node:url';
const dir=fileURLToPath(new URL('.',import.meta.url));
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,chromiumSandbox:true});
const page=await browser.newPage({viewport:{width:1440,height:960},deviceScaleFactor:1});
const results=[];
for(const name of ['islands','studio','workbench']){
 await page.goto('file://'+dir+name+'.html');await page.evaluate(()=>document.fonts.ready);
 await page.screenshot({path:dir+name+'.png',fullPage:true});
 const bounds=await page.evaluate(()=>({width:document.documentElement.scrollWidth,viewport:innerWidth,clipped:[...document.querySelectorAll('.conversation,.inspector,.diff-code')].map(e=>({name:e.className,scroll:e.scrollHeight,client:e.clientHeight,width:e.scrollWidth,clientWidth:e.clientWidth}))}));
 await page.locator('[data-panel="ECU controls"]').first().click();await page.locator('.modal').waitFor({state:'visible'});
 if(name==='islands')await page.screenshot({path:dir+'islands-ecu.png'});
 await page.keyboard.press('Escape');
 await page.locator('[data-action="details"]').click();
 if(!await page.locator('.process-details').isVisible())throw Error('Details failed');
 await page.locator('[data-action="send"]').click();
 if(!await page.locator('.toast').isVisible())throw Error('Preview send failed');
 results.push({name,...bounds,interactions:'ECU open / Escape / process details / mock send passed'});
}
console.log(JSON.stringify(results,null,2));await browser.close();
