import asyncio
from pyppeteer import launch

async def main():
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()
    
    page.on('console', lambda msg: print(f'CONSOLE {msg.type}: {msg.text}'))
    
    await page.goto('http://127.0.0.1:5000/services', {'waitUntil': 'networkidle2'})
    print("Navigated to Services")
    
    await asyncio.sleep(1)
    
    # Click Home link
    print("Clicking Home...")
    await page.evaluate('''() => {
        const link = Array.from(document.querySelectorAll('a')).find(el => el.textContent.trim() === 'Home');
        if (link) link.click();
    }''')
    
    await asyncio.sleep(2)
    
    # Check if page is stuck
    is_animating = await page.evaluate('document.documentElement.classList.contains("is-animating")')
    print("is-animating:", is_animating)
    
    # Click About link
    print("Clicking About...")
    await page.evaluate('''() => {
        const link = Array.from(document.querySelectorAll('a')).find(el => el.textContent.trim() === 'About');
        if (link) link.click();
    }''')
    
    await asyncio.sleep(2)
    is_animating2 = await page.evaluate('document.documentElement.classList.contains("is-animating")')
    print("is-animating after About:", is_animating2)
    
    await browser.close()

asyncio.run(main())
