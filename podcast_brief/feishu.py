from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx


@dataclass(frozen=True)
class FeishuConfig:
    """飞书应用配置"""
    app_id: str
    app_secret: str
    bitable_app_token: Optional[str] = None  # 多维表格的 app_token
    bitable_table_id: Optional[str] = None   # 表格的 table_id
    domain: Optional[str] = None             # 飞书域名（例如：rcns5ppx1h0z）
    folder_token: Optional[str] = None       # Daily Brief 文档保存的文件夹 token


def get_feishu_config() -> Optional[FeishuConfig]:
    """
    从环境变量读取飞书配置。
    如果未配置，返回 None。
    """
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    
    if not app_id or not app_secret:
        return None
    
    return FeishuConfig(
        app_id=app_id,
        app_secret=app_secret,
        bitable_app_token=os.getenv("FEISHU_BITABLE_APP_TOKEN"),
        bitable_table_id=os.getenv("FEISHU_BITABLE_TABLE_ID"),
        domain=os.getenv("FEISHU_DOMAIN"),  # 可选：用于生成文档链接
        folder_token=os.getenv("FEISHU_FOLDER_TOKEN"),  # 可选：Daily Brief 保存文件夹
    )


class FeishuClient:
    """
    飞书 API 客户端。
    
    文档：https://open.feishu.cn/document/home/introduction-to-custom-app-development/self-built-application-development-process
    """
    
    BASE_URL = "https://open.feishu.cn/open-apis"
    
    def __init__(self, config: FeishuConfig):
        self.config = config
        self._token: Optional[str] = None
        self._client = httpx.Client(timeout=30.0)
    
    def _get_tenant_access_token(self) -> str:
        """
        获取 tenant_access_token（应用级别访问凭证）。
        文档：https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal
        """
        if self._token:
            return self._token
        
        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.config.app_id,
            "app_secret": self.config.app_secret,
        }
        
        resp = self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") != 0:
            raise Exception(f"飞书认证失败: {data.get('msg')}")
        
        self._token = data["tenant_access_token"]
        return self._token
    
    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict:
        """
        通用 API 请求方法。
        """
        token = self._get_tenant_access_token()
        url = f"{self.BASE_URL}/{endpoint}"
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        
        resp = self._client.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"飞书 API 错误: {data.get('msg')}")
        
        return data
    
    def add_bitable_record(
        self,
        app_token: str,
        table_id: str,
        fields: dict[str, Any],
    ) -> dict:
        """
        向多维表格添加一条记录。
        
        文档：https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/create
        
        Args:
            app_token: 多维表格的 app_token（从飞书链接中获取）
            table_id: 表格的 table_id
            fields: 字段值字典，例如 {"标题": "xxx", "发布时间": "2026-02-11"}
        
        Returns:
            创建的记录信息
        """
        endpoint = f"bitable/v1/apps/{app_token}/tables/{table_id}/records"
        payload = {"fields": fields}
        
        return self._request("POST", endpoint, json=payload)
    
    def batch_add_bitable_records(
        self,
        app_token: str,
        table_id: str,
        records: list[dict[str, Any]],
    ) -> dict:
        """
        批量添加记录（最多 500 条）。
        
        文档：https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_create
        """
        endpoint = f"bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
        payload = {"records": [{"fields": r} for r in records]}
        
        return self._request("POST", endpoint, json=payload)
    
    def search_bitable_records(
        self,
        app_token: str,
        table_id: str,
        field_name: str,
        field_value: str,
    ) -> list[dict]:
        """
        搜索多维表格记录。
        
        文档：https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/search
        """
        endpoint = f"bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
        payload = {
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_name": field_name,
                        "operator": "is",
                        "value": [field_value]
                    }
                ]
            }
        }
        
        result = self._request("POST", endpoint, json=payload)
        return result.get("data", {}).get("items", [])
    
    def create_docx(
        self,
        folder_token: Optional[str] = None,
        title: str = "Untitled",
    ) -> dict:
        """
        创建飞书文档。
        
        文档：https://open.feishu.cn/document/server-docs/docs/docs-v2/document/create
        
        Args:
            folder_token: 文档所在文件夹的 token（可选）
            title: 文档标题
        
        Returns:
            文档信息（包括 document_id）
        """
        endpoint = "docx/v1/documents"
        payload = {"title": title}
        if folder_token:
            payload["folder_token"] = folder_token
        
        return self._request("POST", endpoint, json=payload)
    
    def update_docx_content(
        self,
        document_id: str,
        content_blocks: list[dict],
    ) -> dict:
        """
        更新飞书文档内容（追加块）。
        
        文档：https://open.feishu.cn/document/server-docs/docs/docs-v2/document-block/create
        
        Args:
            document_id: 文档 ID
            content_blocks: 内容块列表
        
        Returns:
            创建结果
        """
        # 飞书文档 API：向 page 块添加子块
        # endpoint: POST /docx/v1/documents/{document_id}/blocks/{block_id}/children
        # 对于新创建的文档，page 的 block_id 等于 document_id
        
        endpoint = f"docx/v1/documents/{document_id}/blocks/{document_id}/children"
        payload = {
            "children": content_blocks,
            "index": -1,  # 追加到末尾
        }
        
        return self._request("POST", endpoint, json=payload)
    
    def close(self):
        """关闭 HTTP 客户端"""
        self._client.close()


def send_feishu_webhook_message(
    webhook_url: str,
    title: str,
    content_lines: list[str],
    doc_url: Optional[str] = None,
) -> None:
    """
    通过 Webhook 发送飞书消息卡片。
    
    Args:
        webhook_url: 飞书自定义机器人的 Webhook URL
        title: 消息标题
        content_lines: 消息内容（每行一个字符串）
        doc_url: 可选的文档链接
    """
    if not webhook_url:
        return
    
    # 构建消息内容
    content_text = "\n".join(content_lines)
    
    # 飞书消息卡片格式
    card_content = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": "blue",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": content_text,
                },
            }
        ],
    }
    
    # 如果有文档链接，添加按钮
    if doc_url:
        card_content["elements"].append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📄 查看 Daily Brief"},
                    "type": "primary",
                    "url": doc_url,
                }
            ],
        })
    
    payload = {
        "msg_type": "interactive",
        "card": card_content,
    }
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()
    except Exception as e:
        # 发送失败不影响主流程，只打印警告
        print(f"⚠️  飞书 Webhook 发送失败: {e}")
