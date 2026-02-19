#!/usr/bin/env python3
"""
使用 Playwright 生成无页脚的 PDF（支持 ARM Mac）
增加渲染时间确保 Chart.js 图表完全加载
"""
from playwright.sync_api import sync_playwright
import sys

def generate_pdf(html_path, pdf_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # 加载 HTML
        page.goto(f'file://{html_path}')
        
        # 等待 Chart.js 从 CDN 加载并完成渲染
        # 先等待网络空闲
        page.wait_for_load_state('networkidle')
        
        # 再额外等待 15 秒确保图表渲染完成
        page.wait_for_timeout(15000)
        
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
