#!/usr/bin/env python3
"""
使用 Playwright 生成 PDF 报告（解决中文乱码问题）
"""
import asyncio
from playwright.async_api import async_playwright
import sys
from pathlib import Path

async def generate_pdf(html_path: str, pdf_path: str):
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # 加载 HTML 文件
        await page.goto(f"file://{html_path}")
        
        # 等待字体和图表加载完成
        await page.wait_for_timeout(3000)
        
        # 生成 PDF
        await page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={
                "top": "1cm",
                "right": "1cm", 
                "bottom": "1cm",
                "left": "1cm"
            }
        )
        
        await browser.close()
        print(f"✅ PDF 已生成: {pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_pdf_playwright.py <html_file> <pdf_file>")
        sys.exit(1)
    
    html_file = sys.argv[1]
    pdf_file = sys.argv[2]
    
    asyncio.run(generate_pdf(html_file, pdf_file))
