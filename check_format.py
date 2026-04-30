# -*- coding: utf-8 -*-
"""检查代码段格式与字体"""
import docx
from docx.oxml.ns import qn

DOCX = r'C:/Users/da983/Documents/xwechat_files/wxid_gc6r9mc9tebt22_e63d/msg/file/2026-04/正文基于RAG技术的智能客服系统的设计与实现_修订版.docx'
doc = docx.Document(DOCX)

CODE_INDICATORS = [
    'RecursiveCharacterTextSplitter(',
    '_RULES = {',
    'def rag_query_stream',
    '@router.post("/stream")',
    'const reader = res.body.getReader',
]

for i, p in enumerate(doc.paragraphs):
    for indicator in CODE_INDICATORS:
        if indicator in p.text:
            # Inspect runs - count breaks and check fonts
            run_count = len(p.runs)
            breaks = 0
            fonts = set()
            for r in p.runs:
                if r._element.findall(qn('w:br')):
                    breaks += len(r._element.findall(qn('w:br')))
                f = r.font.name or '<inherited>'
                fonts.add(f)
            print(f'Para {i} [{indicator[:30]}]: runs={run_count}, breaks={breaks}, fonts={fonts}')
            break
