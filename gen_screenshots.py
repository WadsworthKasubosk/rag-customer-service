"""Render frontend screenshots, each in a fresh page to avoid state leakage."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path("thesis_assets")
OUT.mkdir(exist_ok=True)
HTML = Path("app/templates/index.html").resolve()


STUB_JS = r"""
(() => {
    const origFetch = window.fetch;
    const stubs = {
        '/api/config/current':   {api_key_preview: 'sk-d2b****537e', base_url: 'https://api.deepseek.com', model: 'deepseek-chat', configured: true},
        '/api/config/llm':       {api_key_preview: 'sk-d2b****537e', base_url: 'https://api.deepseek.com', model: 'deepseek-chat', configured: true},
        '/api/config/save':      {api_key_preview: 'sk-d2b****537e', model: 'deepseek-chat'},
        '/api/config/test':      {success: true, model: 'deepseek-chat', elapsed_seconds: 0.42, total_tokens: 18},
        '/api/knowledge/status': {document_count: 3, chunk_count: 218, vector_count: 218, ready: true},
        '/api/knowledge/stats':  {document_count: 3, chunk_count: 218, vector_count: 218},
        '/api/feedback/stats':   {total_messages: 156, avg_rating: 4.6, satisfaction_rate: 0.92, resolution_rate: 0.87, avg_response_time: 0.5, total: 156, average_rating: 4.6},
        '/api/graph/stats':      {node_count: 50, edge_count: 80, nodes: 50, edges: 80},
    };
    window.fetch = async (url, opts) => {
        const path = (typeof url === 'string') ? url.split('?')[0] : (url.url || '');
        for (const k of Object.keys(stubs)) {
            if (path.endsWith(k)) {
                return new Response(JSON.stringify(stubs[k]),
                    {status: 200, headers: {'Content-Type': 'application/json'}});
            }
        }
        return new Response('{}', {status: 200, headers: {'Content-Type': 'application/json'}});
    };
})();
"""


async def fresh_page(ctx):
    page = await ctx.new_page()
    await page.goto(f"file:///{HTML.as_posix()}")
    await page.wait_for_timeout(800)
    return page


async def shoot():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900},
                                         device_scale_factor=2)
        await ctx.add_init_script(STUB_JS)

        # Fig 4-1 / 4-3: Model config
        page = await fresh_page(ctx)
        await page.evaluate("""() => {
            document.getElementById('provider-select').value = 'deepseek';
            document.getElementById('api-key-input').value = 'sk-d2b1234567890abcdef537e';
            document.getElementById('base-url-input').value = 'https://api.deepseek.com';
            document.getElementById('model-input').value = 'deepseek-chat';
            document.getElementById('config-status').innerHTML =
                '<span style="color:#10b981;">✓ 连接成功 · deepseek-chat · 0.42s · 18 tokens</span>';
            const h = document.getElementById('header-status');
            h.className = 'conn-badge connected';
            h.textContent = '已连接';
        }""")
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "fig_4_1_overview.png"))
        await page.screenshot(path=str(OUT / "fig_4_3_config.png"))
        await page.close()

        # Fig 4-4: KB tab
        page = await fresh_page(ctx)
        await page.evaluate("""() => {
            switchTab('kb');
            document.getElementById('kb-badge').className = 'kb-badge success';
            document.getElementById('kb-text').textContent = '已就绪';
            document.getElementById('kb-detail').textContent = '向量数：218';
            document.getElementById('upload-msg').innerHTML =
                '<span style="color:#10b981;">✓ 已成功导入 3 份文档,共 218 个文本片段</span>';
            const h = document.getElementById('header-status');
            h.className = 'conn-badge connected';
            h.textContent = '已连接';
        }""")
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "fig_4_4_kb.png"))
        await page.close()

        # Fig 4-6: Demo data
        page = await fresh_page(ctx)
        await page.evaluate("""() => {
            switchTab('demo');
            document.getElementById('demo-status').innerHTML =
                '<span style="color:#10b981;">✓ 已初始化 8 商品 · 5 促销 · 10 维修工单 · 20 物流订单</span>';
            const r = document.getElementById('demo-result');
            r.style.display = 'block';
            document.getElementById('demo-repair-ids').innerHTML =
                '<b>维修工单 (10 条)</b><br>WX20260320001 · WX20260320002 · WX20260321003<br>WX20260322004 · WX20260322005 · WX20260323006 ...';
            document.getElementById('demo-order-ids').innerHTML =
                '<b>物流订单 (20 条)</b><br>DD20260320001 · DD20260320002 · DD20260321005<br>DD20260321006 · DD20260322008 · DD20260322009 ...';
            const h = document.getElementById('header-status');
            h.className = 'conn-badge connected'; h.textContent = '已连接';
        }""")
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "fig_4_6_demo.png"))
        await page.close()

        # Fig 4-7: Stats
        page = await fresh_page(ctx)
        await page.evaluate("""() => {
            switchTab('stats');
            document.getElementById('stat-total').textContent = '156';
            document.getElementById('stat-time').textContent = '0.5s';
            document.getElementById('stat-rating').textContent = '4.6';
            document.getElementById('stat-satisfaction').textContent = '92%';
            document.getElementById('stat-resolution').textContent = '87%';
            const h = document.getElementById('header-status');
            h.className = 'conn-badge connected'; h.textContent = '已连接';
        }""")
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "fig_4_7_stats.png"))
        await page.close()

        # Fig 4-5: KG tab (panel state only; visualization uses standalone diagram)
        page = await fresh_page(ctx)
        await page.evaluate("""() => {
            switchTab('kg');
            document.getElementById('kg-badge').className = 'kb-badge success';
            document.getElementById('kg-stats-text').textContent = '50 节点 · 80 关系';
            document.getElementById('kg-status').innerHTML =
                '<span style="color:#10b981;">✓ 知识图谱已加载,共 50 个节点 · 80 条关系</span>';
            const h = document.getElementById('header-status');
            h.className = 'conn-badge connected'; h.textContent = '已连接';
        }""")
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "fig_4_5_kg_panel.png"))
        await page.close()

        # Fig 4-8: Chat with mock conversation
        page = await fresh_page(ctx)
        await page.evaluate("""() => {
            const m = document.getElementById('messages');
            m.innerHTML = '';
            const tpl = (role, content, sources, cat) => {
                const av = role === 'bot' ? 'AI' : '我';
                const cls = role === 'bot' ? 'bot' : 'user';
                let html = `<div class="message ${cls}"><div class="av av-${cls}">${av}</div><div class="bw">`;
                if (cat) html += `<div style="margin-bottom:6px;"><span style="background:#3730A3;color:white;padding:2px 8px;border-radius:10px;font-size:11px;">${cat}</span></div>`;
                html += `<div class="bubble">${content}</div>`;
                if (sources) html += `<div style="margin-top:6px;padding:8px;background:#f3f4f6;border-radius:6px;font-size:11px;color:#475569;line-height:1.6;"><b>📎 参考来源</b><br>${sources}</div>`;
                html += `</div></div>`;
                return html;
            };
            m.innerHTML += tpl('bot', '您好,我是智能客服 <strong>小星</strong>,很高兴为您服务。<br>请问有什么可以帮您?');
            m.innerHTML += tpl('user', 'S14 Pro 16+512 多少钱,现在有优惠吗?');
            m.innerHTML += tpl('bot',
                '<b>星辰S14 Pro 16+512GB</b> 当前价格信息:<br>• 官方价: <b>¥5,999</b><br>• 促销价: <b>¥5,599</b> (双十一活动,立减 ¥400)<br>• 颜色: 星空黑 / 钛金灰 / 极光蓝<br>• 库存状态: 充足<br><br>目前正处于双十一促销期,购买即可享受 9 折优惠。',
                '【结构化知识】products 表 sku_id=1003 (相似度 1.00)<br>【参考资料】产品规格说明书.txt (相似度 0.87)',
                '电商咨询');
            m.innerHTML += tpl('user', 'WX20260320001 修好了吗?');
            m.innerHTML += tpl('bot',
                '为您查询工单 <b>WX20260320001</b>:<br>• 送修产品: 星辰S14<br>• 故障描述: 屏幕碎裂<br>• 当前状态: <b>维修中</b><br>• 预计还需: 2 天<br><br>修复完成后我们会第一时间通知您。',
                '【实时查询结果】repair_tickets WX20260320001',
                '维修跟踪');
            m.scrollTop = m.scrollHeight;
            const h = document.getElementById('header-status');
            h.className = 'conn-badge connected'; h.textContent = '已连接';
        }""")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "fig_4_8_chat.png"))

        # Fig 4-9: Rating bar zoomed
        await page.evaluate("""() => {
            document.querySelectorAll('.star').forEach((s,i) => { s.style.color = '#F59E0B'; });
            document.getElementById('rating-hint').textContent = '已评 5 星 · 已标记已解决 · 感谢反馈!';
            document.getElementById('rating-hint').style.color = '#10b981';
            const ok = document.querySelector('.resolve-btn[data-resolved="true"]');
            if (ok) ok.classList.add('active');
        }""")
        await page.wait_for_timeout(300)
        bar = await page.query_selector('.rating-bar')
        if bar:
            await bar.screenshot(path=str(OUT / "fig_4_9_rating.png"))
        await page.close()

        # Fig 5-1: end-to-end mosaic
        page = await fresh_page(ctx)
        await page.evaluate("""() => {
            const m = document.getElementById('messages');
            m.innerHTML = '';
            const tpl = (role, content, sources, cat) => {
                const av = role === 'bot' ? 'AI' : '我';
                const cls = role === 'bot' ? 'bot' : 'user';
                let html = `<div class="message ${cls}"><div class="av av-${cls}">${av}</div><div class="bw">`;
                if (cat) html += `<div style="margin-bottom:6px;"><span style="background:#3730A3;color:white;padding:2px 8px;border-radius:10px;font-size:11px;">${cat}</span></div>`;
                html += `<div class="bubble">${content}</div>`;
                if (sources) html += `<div style="margin-top:6px;padding:8px;background:#f3f4f6;border-radius:6px;font-size:11px;color:#475569;line-height:1.6;"><b>📎 参考来源</b><br>${sources}</div>`;
                html += `</div></div>`;
                return html;
            };
            m.innerHTML += tpl('user', '怎么重启手机?');
            m.innerHTML += tpl('bot',
                '重启星辰 S14 / S14 Pro 的步骤:<br>1. 长按电源键约 5 秒<br>2. 屏幕出现滑动条后,向上滑动关机<br>3. 关机后短按电源键即可开机<br><br>如长按无响应,可同时按住电源键 + 音量减键 10 秒强制重启。',
                '产品规格说明书.txt (相似度 0.89)', '产品问答');
            m.innerHTML += tpl('user', '屏幕碎了能保修吗?');
            m.innerHTML += tpl('bot',
                '关于屏幕保修政策:<br>• <b>非人为损坏</b>: 自购机起 1 年内免费保修<br>• <b>人为损坏(摔碎)</b>: 不在免费保修范围,需付费维修<br>• <b>付费维修参考价</b>: 屏幕更换约 ¥499<br><br>如需送修,可联系客服寄送或前往就近售后服务点。',
                '【结构化知识】保修政策、屏幕维修费用<br>【参考资料】保修政策.txt (相似度 0.91)', '售后服务');
            m.innerHTML += tpl('user', 'DD20260320001 到哪了?');
            m.innerHTML += tpl('bot',
                '为您查询订单 <b>DD20260320001</b>:<br>• 承运商: 顺丰速运<br>• 当前状态: <b>已到达成都转运中心,运输中</b><br>• 预计送达: 明日 12:00 前<br><br>下一站: 成都市青羊区营业网点。',
                '【实时查询结果】tracking_orders + tracking_events DD20260320001',
                '物流跟踪');
            m.scrollTop = m.scrollHeight;
            const h = document.getElementById('header-status');
            h.className = 'conn-badge connected'; h.textContent = '已连接';
        }""")
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT / "fig_5_1_e2e.png"))
        await page.close()

        await browser.close()
        print("All screenshots saved.")


asyncio.run(shoot())
