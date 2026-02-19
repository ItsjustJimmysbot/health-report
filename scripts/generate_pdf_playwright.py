#!/usr/bin/env python3
"""
使用 Playwright 生成无页脚的 PDF（支持 ARM Mac）
"""
from playwright.sync_api import sync_playwright
import sys

def generate_pdf(html_path, pdf_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # 加载 HTML
        page.goto(f'file://{html_path}')
        
        # 等待图表渲染完成
        page.wait_for_timeout(10000)  # 10秒等待图表渲染
        
        # 生成 PDF，禁用页眉页脚
        page.pdf(
            path=pdf_path,
            format='A4',
            print_background=True,
            margin={
                'top': '1cm',
                'right': '1cm',
                'bottom': '1cm',
                'left': '1cm'
            },
            display_header_footer=False
        )
        
        browser.close()
        print(f'✅ PDF 已生成: {pdf_path}')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python generate_pdf_playwright.py <html_file> <pdf_file>')
        sys.exit(1)
    
    html_file = sys.argv[1]
    pdf_file = sys.argv[2]
    
    generate_pdf(html_file, pdf_file)
