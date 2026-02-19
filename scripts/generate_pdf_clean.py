#!/usr/bin/env python3
"""
使用 Playwright 生成无页脚 URL 的 PDF
"""
import asyncio
from playwright.async_api import async_playwright
import sys

async def generate_pdf(html_path: str, pdf_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # 加载 HTML
        await page.goto(f'file://{html_path}')
        
        # 等待图表渲染
        await page.wait_for_timeout(5000)
        
        # 生成 PDF（无页眉页脚）
        await page.pdf(
            path=pdf_path,
            format='A4',
            print_background=True,
            margin={
                'top': '1cm',
                'right': '1cm',
                'bottom': '1cm',
                'left': '1cm'
            },
            display_header_footer=False  # 禁用页眉页脚
        )
        
        await browser.close()
        print(f'✅ PDF 已生成: {pdf_path}')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python generate_pdf_clean.py <html_file> <pdf_file>')
        sys.exit(1)
    
    html_file = sys.argv[1]
    pdf_file = sys.argv[2]
    
    asyncio.run(generate_pdf(html_file, pdf_file))
