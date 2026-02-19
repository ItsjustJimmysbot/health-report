#!/usr/bin/env python3
"""
使用 Chrome DevTools Protocol 生成无页脚的 PDF
"""
import asyncio
from pyppeteer import launch
import sys

async def generate_pdf(html_path, pdf_path):
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()
    
    # 加载 HTML
    await page.goto(f'file://{html_path}', waitUntil='networkidle0')
    
    # 等待图表渲染完成
    await asyncio.sleep(8)
    
    # 生成 PDF，禁用页眉页脚
    await page.pdf({
        'path': pdf_path,
        'format': 'A4',
        'printBackground': True,
        'margin': {
            'top': '1cm',
            'right': '1cm',
            'bottom': '1cm',
            'left': '1cm'
        },
        'displayHeaderFooter': False
    })
    
    await browser.close()
    print(f'✅ PDF 已生成: {pdf_path}')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python generate_pdf_pyppeteer.py <html_file> <pdf_file>')
        sys.exit(1)
    
    html_file = sys.argv[1]
    pdf_file = sys.argv[2]
    
    asyncio.run(generate_pdf(html_file, pdf_file))
