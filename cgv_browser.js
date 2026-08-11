const puppeteer = require('puppeteer');
const [,, ymd] = process.argv;
const theaters = [{name:'용산아이파크몰', code:'0013'}, {name:'천호', code:'0199'}];
(async()=>{
  const browser = await puppeteer.launch({headless:'new', args:['--no-sandbox','--disable-setuid-sandbox','--disable-geolocation']});
  const out=[];
  for (const t of theaters) {
    const page=await browser.newPage();
    try {
      const responsePromise=page.waitForResponse(r=>r.url().includes('searchMovScnInfo') && r.request().method()==='GET' && new URL(r.url()).searchParams.get('scnYmd')===ymd,{timeout:25000});
      await page.goto(`https://cgv.co.kr/cnm/movieBook/cinema?siteNo=${t.code}&siteNm=${encodeURIComponent(t.name)}&scnYmd=${ymd}`,{waitUntil:'domcontentloaded',timeout:25000}).catch(()=>{});
      try {
        const response=await responsePromise;
        const body=await response.json();
        for(const x of (body.data||[])) if(x.tcscnsGradCd==='03') out.push({theater:t.name,movie:x.movNm||'',ymd:x.scnYmd||ymd,time:(x.scnsrtTm||'').replace(/^(\d{2})(\d{2})$/,'$1:$2'),url:`https://cgv.co.kr/cnm/movieBook/cinema?siteNo=${t.code}&siteNm=${encodeURIComponent(t.name)}&scnYmd=${ymd}`,seats:Number(x.frSeatCnt??-1)});
      } catch(e) {
        const rows=await page.$$('[class*="startTimeItem"]');
        for(const row of rows){ const txt=(await row.evaluate(el=>el.innerText||'')).trim(); if(!txt) continue; const m=txt.match(/(\d{1,2}:\d{2})/); if(m) out.push({theater:t.name,movie:txt.split('\n')[0],ymd,time:m[1],url:page.url(),seats:-1}); }
      }
    } catch(e) { console.error(`${t.name}: ${e.message}`); } finally { await page.close(); }
  }
  await browser.close(); console.log(JSON.stringify(out));
})().catch(e=>{console.error(e);process.exit(1)});
