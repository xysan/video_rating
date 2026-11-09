import httpx


class FeishuError(RuntimeError):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message
        super().__init__(f"HTTP={status} code={code} message={message}")


class FeishuClient:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport
        self.token = None

    def sanitize(self, message):
        for secret in (self.settings.FEISHU_APP_ID, self.settings.FEISHU_APP_SECRET, self.settings.FEISHU_APP_TOKEN, self.settings.FEISHU_TABLE_ID, self.token):
            if secret:
                message = message.replace(secret, "[已隐藏]")
        return message[:1000].replace("\n", " ").replace("\r", " ")

    def request(self, client, path, **kwargs):
        try:
            response = client.post(path, **kwargs)
        except httpx.HTTPError as exc:
            raise FeishuError(None, "transport_error", type(exc).__name__) from None
        try:
            body = response.json()
        except ValueError:
            raise FeishuError(response.status_code, "invalid_json", "飞书返回非 JSON 响应") from None
        if not isinstance(body, dict):
            raise FeishuError(response.status_code, "invalid_response", "飞书响应不是对象")
        if response.is_error or body.get("code") != 0:
            raise FeishuError(response.status_code, body.get("code"), self.sanitize(str(body.get("msg", body.get("message", "请求失败")))))
        return body

    def records(self):
        s = self.settings
        if not all((s.FEISHU_APP_ID, s.FEISHU_APP_SECRET, s.FEISHU_APP_TOKEN, s.FEISHU_TABLE_ID)):
            raise FeishuError(None, "missing_config", "飞书凭证配置不完整")
        with httpx.Client(base_url="https://open.feishu.cn/open-apis/", timeout=30, transport=self.transport) as client:
            body = self.request(client, "auth/v3/tenant_access_token/internal", json={"app_id": s.FEISHU_APP_ID, "app_secret": s.FEISHU_APP_SECRET})
            self.token = body.get("tenant_access_token")
            if not isinstance(self.token, str) or not self.token:
                raise FeishuError(200, "missing_token", "飞书响应缺少访问令牌")
            page_token = None
            seen = set()
            while True:
                params = {"page_size": 500}
                if page_token:
                    params["page_token"] = page_token
                body = self.request(client, f"bitable/v1/apps/{s.FEISHU_APP_TOKEN}/tables/{s.FEISHU_TABLE_ID}/records/search", params=params, json={"automatic_fields": True}, headers={"Authorization": f"Bearer {self.token}"})
                data = body.get("data")
                if not isinstance(data, dict) or not isinstance(data.get("items", []), list) or not isinstance(data.get("has_more"), bool):
                    raise FeishuError(200, "invalid_page", "飞书分页结构不完整")
                yield from data.get("items", [])
                if not data["has_more"]:
                    break
                page_token = data.get("page_token")
                if not isinstance(page_token, str) or not page_token or page_token in seen:
                    raise FeishuError(200, "invalid_cursor", "飞书分页游标缺失或重复")
                seen.add(page_token)
