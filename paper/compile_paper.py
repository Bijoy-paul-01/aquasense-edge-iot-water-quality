"""
Compilation script for AquaSense Conference Paper.
Generates publication figures and compiles HTML/LaTeX to PDF.
"""

import os
import sys
import subprocess

def compile_pdf():
    paper_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(paper_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    html_file = os.path.join(paper_dir, "AquaSense_IEEE_Conference_Paper.html")
    pdf_file = os.path.join(paper_dir, "AquaSense_IEEE_Conference_Paper.pdf")
    
    # 1. First ensure figures exist
    from ml.generate_paper_figures import generate_all_figures
    generate_all_figures()
    
    # 2. Browser binary paths
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    
    browser_bin = None
    for p in chrome_paths:
        if os.path.exists(p):
            browser_bin = p
            break
            
    if not browser_bin:
        print("[ERROR] Neither Chrome nor Edge executable was found for headless printing.")
        return False
        
    print(f"[Compiler] Found rendering engine: {browser_bin}")
    print(f"[Compiler] Compiling {html_file} -> {pdf_file}...")
    
    cmd = [
        browser_bin,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_file}",
        html_file
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(pdf_file) and os.path.getsize(pdf_file) > 10000:
        size_kb = os.path.getsize(pdf_file) / 1024
        print(f"[SUCCESS] Generated conference paper PDF: {pdf_file} ({size_kb:.1f} KB)")
        return True
    else:
        print(f"[ERROR] Failed to compile PDF: {res.stderr or res.stdout}")
        return False

if __name__ == '__main__':
    compile_pdf()
