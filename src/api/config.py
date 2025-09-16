import yaml
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, validator
from pathlib import Path


class APIEndpoint(BaseModel):
    name: str
    base_url: str
    endpoints: Dict[str, str]
    headers: Dict[str, str]
    request_format: Dict[str, Any]

    def format_url(self, endpoint: str, **kwargs) -> str:
        """格式化完整的请求URL"""
        base = self.base_url.format(**kwargs)
        endpoint_path = self.endpoints.get(endpoint, "")
        endpoint_path = endpoint_path.format(**kwargs)
        return f"{base}{endpoint_path}"

    def format_headers(self, **kwargs) -> Dict[str, str]:
        """格式化请求头"""
        return {k: v.format(**kwargs) for k, v in self.headers.items()}

    def format_request_body(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """格式化请求体"""
        body = json.loads(json.dumps(self.request_format))

        def replace_placeholders(obj, prompt_text):
            if isinstance(obj, dict):
                return {k: replace_placeholders(v, prompt_text) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholders(item, prompt_text) for item in obj]
            elif isinstance(obj, str):
                return obj.replace("{prompt}", prompt_text)
            return obj

        return replace_placeholders(body, prompt)


class TestConfig(BaseModel):
    name: str
    concurrent_levels: List[int]
    requests_per_level: int
    timeout: int
    retry_count: int
    ramp_up_time: int
    cool_down_time: int


class ConfigManager:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.api_configs = self._parse_api_configs()
        self.test_configs = self._parse_test_configs()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _parse_api_configs(self) -> Dict[str, APIEndpoint]:
        """解析API配置"""
        api_configs = {}
        for name, config in self.config.get('api_configs', {}).items():
            api_configs[name] = APIEndpoint(**config)
        return api_configs

    def _parse_test_configs(self) -> Dict[str, TestConfig]:
        """解析测试配置"""
        test_configs = {}
        for name, config in self.config.get('test_configs', {}).items():
            test_configs[name] = TestConfig(**config)
        return test_configs

    def get_api_config(self, name: str) -> Optional[APIEndpoint]:
        """获取指定的API配置"""
        return self.api_configs.get(name)

    def get_test_config(self, name: str) -> Optional[TestConfig]:
        """获取指定的测试配置"""
        return self.test_configs.get(name)

    def list_api_configs(self) -> List[str]:
        """列出所有可用的API配置"""
        return list(self.api_configs.keys())

    def list_test_configs(self) -> List[str]:
        """列出所有可用的测试配置"""
        return list(self.test_configs.keys())

    def get_monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        return self.config.get('monitoring', {})

    def get_reporting_config(self) -> Dict[str, Any]:
        """获取报告配置"""
        return self.config.get('reporting', {})

    def get_data_config(self) -> Dict[str, Any]:
        """获取数据配置"""
        return self.config.get('data', {})


class PromptManager:
    def __init__(self, prompt_file: str = "data/prompts.jsonl"):
        self.prompt_file = Path(prompt_file)
        self.prompts = self._load_prompts()
        self.current_index = 0

    def _load_prompts(self) -> List[str]:
        """从JSONL文件加载提示词"""
        if not self.prompt_file.exists():
            raise FileNotFoundError(f"提示词文件不存在: {self.prompt_file}")

        prompts = []
        with open(self.prompt_file, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                if 'question' in data:
                    prompts.append(data['question'])

        if not prompts:
            raise ValueError("提示词文件中没有找到有效的问题")

        return prompts

    def get_next_prompt(self) -> str:
        """获取下一个提示词（循环获取）"""
        prompt = self.prompts[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.prompts)
        return prompt

    def get_prompt_count(self) -> int:
        """获取提示词总数"""
        return len(self.prompts)

    def reset_index(self):
        """重置索引到开始位置"""
        self.current_index = 0