
import os
import json
import requests
from typing import Generator, List, Dict

class LLMClient:
    def __init__(self, settings: dict, db):
        self.settings = settings
        self.db = db
        self.mode = settings.get("mode", "offline")
        self.ollama_base = settings.get("ollama_base_url", "http://localhost:11434")
        self.offline_model = settings.get("offline_model", "llama3")
        self.online_model = settings.get("online_model", "gpt-4o-mini")
        self.anthropic_model = settings.get("anthropic_model", "claude-3-opus-20240229")
        self.temperature = settings.get("temperature", 0.7)
        self.max_tokens = settings.get("max_tokens", 1024)
        self.system_prompt = settings.get("system_prompt", "You are a helpful assistant.")
        self.openai_key = os.getenv("OPENAI_API_KEY", settings.get("openai_api_key", ""))
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", settings.get("anthropic_api_key", ""))

    def stream_chat(self, messages: List[Dict], session_id: str) -> Generator[str, None, None]:
        if self.mode == "offline":
            yield from self._ollama_stream(messages)
        elif self.mode == "anthropic":
            yield from self._anthropic_stream(messages)
        else:
            yield from self._openai_stream(messages)

    def _with_system(self, messages: List[Dict]) -> List[Dict]:
        has_system = any(m.get("role") == "system" for m in messages)
        if has_system:
            return messages
        return [{"role": "system", "content": self.system_prompt}] + messages

    def _ollama_stream(self, messages: List[Dict]) -> Generator[str, None, None]:
        url = f"{self.ollama_base}/api/chat"
        payload = {
            "model": self.offline_model,
            "messages": self._with_system(messages),
            "stream": True,
            "options": {"temperature": self.temperature}
        }
        with requests.post(url, json=payload, stream=True, timeout=600) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = data.get("message", {})
                chunk = msg.get("content", "")
                if chunk:
                    yield chunk

    def _openai_stream(self, messages: List[Dict]) -> Generator[str, None, None]:
        if not self.openai_key:
            raise ValueError("OpenAI API key is missing. Set it in settings or environment.")
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.online_model,
            "messages": self._with_system(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True
        }
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=600) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                data_str = line.replace("data: ", "").strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                delta = data.get("choices", [{}])[0].get("delta", {})
                piece = delta.get("content", "")
                if piece:
                    yield piece

    def _anthropic_stream(self, messages: List[Dict]) -> Generator[str, None, None]:
        if not self.anthropic_key:
            raise ValueError("Anthropic API key is missing. Set it in settings or environment.")
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        sys_prompt = None
        user_turns = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                sys_prompt = content
            elif role == "user":
                user_turns.append({"role": "user", "content": content})
            elif role == "assistant":
                user_turns.append({"role": "assistant", "content": content})

        if sys_prompt is None:
            sys_prompt = self.system_prompt

        payload = {
            "model": self.anthropic_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": sys_prompt,
            "stream": True,
            "messages": [{"role": u["role"], "content": u["content"]} for u in user_turns]
        }

        with requests.post(url, headers=headers, json=payload, stream=True, timeout=600) as r:
            r.raise_for_status()
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if not raw.startswith("data:"):
                    continue
                data_str = raw.replace("data:", "", 1).strip()
                if data_str == "[DONE]":
                    break
                try:
                    ev = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") == "content_block_delta":
                    delta = ev.get("delta", {})
                    txt = delta.get("text", "")
                    if txt:
                        yield txt
                elif "delta" in ev and isinstance(ev["delta"], dict):
                    txt = ev["delta"].get("text", "")
                    if txt:
                        yield txt
