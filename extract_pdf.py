import pdfplumber

with pdfplumber.open(r'C:\Users\amrit\OneDrive\Desktop\project\Cross-System Data Drift & Trust Monitoring Platform.pdf') as pdf:
    for i, page in enumerate(pdf.pages):
        print(f'=== PAGE {i+1} ===')
        text = page.extract_text()
        if text:
            print(text)
        print()
