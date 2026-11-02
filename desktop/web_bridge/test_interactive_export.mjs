import {chromium} from './vendor/playwright-core/index.mjs';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../',import.meta.url));
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,chromiumSandbox:true});
try{
 const page=await browser.newPage({viewport:{width:1000,height:1100}}),errors=[],requests=[];page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(!r.url().startsWith('file:'))requests.push(r.url())});
 await page.goto('file://'+root+'build/previews/desktop-interactive-example.html');await page.waitForFunction(()=>window.visualTest);
 const before=await page.locator('#readouts').innerText();await page.getByRole('spinbutton',{name:'Amplitude value',exact:true}).fill('2.5');await page.getByRole('spinbutton',{name:'Amplitude value',exact:true}).dispatchEvent('input');const after=await page.locator('#readouts').innerText();if(before===after)throw Error('Slider readout did not change');
 const t0=await page.evaluate(()=>visualTest.state().t);await page.getByRole('button',{name:'Play',exact:true}).click();await page.waitForFunction(t=>visualTest.state().t>t,t0);await page.getByRole('button',{name:'Pause',exact:true}).click();
 await page.getByRole('button',{name:'Reset',exact:true}).click();if((await page.evaluate(()=>visualTest.state().amplitude))!==1)throw Error('Reset failed');
 await page.emulateMedia({reducedMotion:'reduce'});await page.getByRole('button',{name:'Play',exact:true}).click();if(!(await page.locator('#status').innerText()).includes('Reduced motion'))throw Error('Reduced motion was not respected');
 await page.setViewportSize({width:480,height:1000});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Narrow export overflow');
 if(errors.length||requests.length)throw Error(JSON.stringify({errors,requests}));await page.screenshot({path:root+'build/previews/desktop-interactive-export.png',fullPage:true});
 console.log(JSON.stringify({sliders:true,readouts:true,animation:true,reset:true,narrow_width:480,network_requests:requests.length,page_errors:errors.length}));
}finally{await browser.close()}
