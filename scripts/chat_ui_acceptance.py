import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.async_api import async_playwright
from hub.config import ARTIFACTS
async def wait(page,expr,timeout=90000,polling=200):
 for _ in range(timeout//polling):
  if await page.evaluate(expr):return
  await asyncio.sleep(polling/1000)
 raise RuntimeError('UI condition timed out: '+expr)
async def main():
 async with async_playwright() as p:
  b=await p.chromium.connect_over_cdp('http://127.0.0.1:9223',no_defaults=True)
  pages=[p for c in b.contexts for p in c.pages]
  page=next(p for p in pages if p.url.startswith('http://127.0.0.1:8876'))
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.set_viewport_size({'width':1440,'height':900})
  await page.reload();await page.set_viewport_size({'width':1440,'height':900});await wait(page,"document.querySelector('#health').textContent.includes('qwen')",polling=200)
  await page.locator('#add-project').dispatch_event('click')
  await page.locator('#folder-path').fill('E:/AI/repos/sandbox',force=True)
  await page.locator('#folder-path-form').evaluate('(f)=>f.requestSubmit()')
  await page.wait_for_timeout(500)
  await page.locator('#folder-choose').dispatch_event('click')
  await page.wait_for_timeout(500)
  await page.locator('#goal').fill('Remember this project code: BLUE_ORCHID_47. Reply with that code only. Do not use tools.')
  await page.locator('#composer').evaluate('(f)=>f.requestSubmit()')
  await wait(page,"document.querySelector('.message.assistant')?.textContent.includes('BLUE_ORCHID_47')",timeout=90000,polling=200)
  await page.locator('#goal').fill('What project code did I ask you to remember? Reply only with the code. Do not use tools.')
  await page.locator('#composer').evaluate('(f)=>f.requestSubmit()')
  await wait(page,"document.querySelectorAll('.message.assistant').length===2",timeout=90000,polling=200)
  replies=await page.locator('.message.assistant').all_text_contents()
  assert 'BLUE_ORCHID_47' in replies[-1],replies
  await page.reload();await page.wait_for_timeout(1000)
  await page.locator('#chats button').filter(has_text='Remember this project code').first.dispatch_event('click')
  await wait(page,"document.querySelectorAll('.message.assistant').length===2",polling=200)
  desktop=await page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
  await page.set_viewport_size({'width':390,'height':844})
  await page.wait_for_timeout(500)
  mobile=await page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth,menu:getComputedStyle(document.querySelector("#menu")).display})')
  assert mobile['scroll']<=mobile['width'],mobile
  assert mobile['menu']!='none'
  try:await page.screenshot(path=str(ARTIFACTS/'chat-mobile.png'),timeout=3000)
  except Exception:pass
  report={'two_turn_memory':True,'reload_history':True,'desktop':desktop,'mobile':mobile,'page_errors':errors}
  (ARTIFACTS/'chat-ui-acceptance.json').write_text(json.dumps(report,indent=2))
  print(json.dumps(report),flush=True)
asyncio.run(main())
