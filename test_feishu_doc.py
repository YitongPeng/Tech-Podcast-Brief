"""测试飞书文档API的最小示例"""
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
    # 1. 创建文档
    print("创建文档...")
    doc_result = client.create_docx(title="测试文档")
    doc_id = doc_result["data"]["document"]["document_id"]
    print(f"✓ 文档创建成功: {doc_id}")
    print(f"  完整返回: {doc_result}")
    
    # 2. 获取文档信息
    print("\n获取文档信息...")
    doc_info = client._request("GET", f"docx/v1/documents/{doc_id}")
    print(f"  文档信息: {doc_info}")
    
    # 3. 获取文档块列表
    print("\n获取文档块列表...")
    blocks_info = client._request("GET", f"docx/v1/documents/{doc_id}/blocks", params={"page_size": 10})
    print(f"  块列表: {blocks_info}")
    
    if blocks_info.get("data", {}).get("items"):
        print(f"\n找到 {len(blocks_info['data']['items'])} 个块:")
        for item in blocks_info['data']['items']:
            print(f"  - block_id: {item.get('block_id')}, block_type: {item.get('block_type')}")
    
    # 4. 尝试不同的 endpoint 格式
    block_id = doc_id  # 使用文档 ID 作为块 ID
    
    print(f"\n尝试方式 1: 使用完整路径 /blocks/{block_id}/children/batch_create...")
    try:
        endpoint1 = f"docx/v1/documents/{doc_id}/blocks/{block_id}/children/batch_create"
        payload1 = {
            "children": [
                {
                    "block_type": 2,  # paragraph
                    "paragraph": {
                        "elements": [{"text_run": {"content": "测试内容"}}]
                    }
                }
            ],
            "index": -1
        }
        result = client._request("POST", endpoint1, json=payload1)
        print(f"✓ 成功!")
        print(f"  结果: {result}")
        print(f"  文档链接: https://rcns5ppx1h0z.feishu.cn/docx/{doc_id}")
    except Exception as e:
        print(f"✗ 失败: {e}")
        
        print(f"\n尝试方式 2: 使用 /blocks/batch_create (不带 block_id)...")
        try:
            endpoint2 = f"docx/v1/documents/{doc_id}/blocks/batch_create"
            payload2 = {
                "block_id": doc_id,
                "children": [
                    {
                        "block_type": 2,
                        "paragraph": {
                            "elements": [{"text_run": {"content": "测试内容2"}}]
                        }
                    }
                ],
                "index": -1
            }
            result = client._request("POST", endpoint2, json=payload2)
            print(f"✓ 成功!")
            print(f"  结果: {result}")
            print(f"  文档链接: https://rcns5ppx1h0z.feishu.cn/docx/{doc_id}")
        except Exception as e2:
            print(f"✗ 失败: {e2}")
            
            print(f"\n尝试方式 3: 创建单个块（不用 batch）...")
            try:
                endpoint3 = f"docx/v1/documents/{doc_id}/blocks/{block_id}/children"
                payload3 = {
                    "block_type": 2,
                    "paragraph": {
                        "elements": [{"text_run": {"content": "测试内容3"}}]
                    }
                }
                result = client._request("POST", endpoint3, json=payload3)
                print(f"✓ 成功!")
                print(f"  结果: {result}")
                print(f"  文档链接: https://rcns5ppx1h0z.feishu.cn/docx/{doc_id}")
            except Exception as e3:
                print(f"✗ 失败: {e3}")
                print("\n所有方式都失败了，可能是权限问题。")
                print("请检查飞书应用的文档编辑权限是否已开通并发布。")
    
except Exception as e:
    print(f"✗ 错误: {e}")
finally:
    client.close()
