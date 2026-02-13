"""测试飞书文档API - 使用正确的 block_type"""
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
    doc_result = client.create_docx(title="Daily Brief 测试")
    doc_id = doc_result["data"]["document"]["document_id"]
    print(f"✓ 文档创建成功: {doc_id}")
    
    # 根据飞书官方文档，block_type 的定义：
    # 1 = page（页面）
    # 2 = text（文本段落）
    # 3 = heading1（一级标题）
    # 4 = heading2（二级标题）
    # 5 = heading3（三级标题）
    
    print("\n尝试写入文本块（block_type: 2）...")
    endpoint = f"docx/v1/documents/{doc_id}/blocks/{doc_id}/children"
    
    # 使用 text block（block_type: 2）
    payload = {
        "children": [{
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": "这是测试内容"}}],
                "style": {}
            }
        }],
        "index": -1
    }
    
    result = client._request("POST", endpoint, json=payload)
    print(f"✓ 写入成功!")
    print(f"  结果: {result}")
    print(f"\n文档链接: https://rcns5ppx1h0z.feishu.cn/docx/{doc_id}")
    print("请打开链接查看效果！")
    
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
