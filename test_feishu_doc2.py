"""测试飞书文档API - 简化版"""
import os
from dotenv import load_dotenv
from podcast_brief.feishu import FeishuClient, FeishuConfig

load_dotenv()

config = FeishuConfig(
    app_id=os.getenv("FEISHU_APP_ID"),
    app_secret=os.getenv("FEISHU_APP_SECRET"),
)

client = FeishuClient(config)

try:
    # 创建文档
    print("创建文档...")
    doc_result = client.create_docx(title="Daily Brief — 2026-02-11")
    doc_id = doc_result["data"]["document"]["document_id"]
    print(f"✓ 文档创建成功: {doc_id}")
    print(f"  文档链接: https://rcns5ppx1h0z.feishu.cn/docx/{doc_id}")
    
    # 尝试最简单的写入 - 直接用 POST 请求
    print("\n写入标题...")
    endpoint = f"docx/v1/documents/{doc_id}/blocks/{doc_id}/children"
    
    # 尝试不同的 payload 结构
    payloads_to_try = [
        # 结构 1: 简单的 text
        {
            "children": [{
                "block_type": 2,
                "paragraph": {
                    "elements": [{"text_run": {"content": "生成时间：2026-02-11"}}]
                }
            }],
            "index": -1
        },
        # 结构 2: 带 block 包装
        {
            "block": {
                "block_type": 2,
                "paragraph": {
                    "elements": [{"text_run": {"content": "生成时间：2026-02-11"}}]
                }
            },
            "index": -1
        },
        # 结构 3: 最简单
        {
            "block_type": 2,
            "paragraph": {
                "elements": [{"text_run": {"content": "生成时间：2026-02-11"}}]
            }
        },
    ]
    
    for i, payload in enumerate(payloads_to_try, 1):
        try:
            print(f"\n尝试结构 {i}...")
            print(f"  Payload: {payload}")
            result = client._request("POST", endpoint, json=payload)
            print(f"✓ 成功！使用结构 {i}")
            print(f"  结果: {result}")
            break
        except Exception as e:
            print(f"✗ 结构 {i} 失败: {e}")
            if i == len(payloads_to_try):
                print("\n所有结构都失败了。可能需要检查：")
                print("1. 应用权限是否包含 docx:document:write")
                print("2. 应用版本是否已发布")
                print("3. API 版本是否正确")
    
except Exception as e:
    print(f"✗ 错误: {e}")
finally:
    client.close()
