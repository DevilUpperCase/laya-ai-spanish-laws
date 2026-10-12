from pathlib import Path
from urllib.parse import urlparse
import os
import re
import ipaddress
from pydantic import model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    app_env: str = "development"
    database_url: str = Field(default="",repr=False)
    admin_database_url: str = Field(default="",repr=False)
    ingest_database_url: str = Field(default="",repr=False)
    worker_database_url: str = Field(default="",repr=False)
    auth_issuer: str = "http://127.0.0.1:8000/local-auth"
    auth_audience: str = "laya-juridico"
    auth_jwks_url: str = ""
    auth_public_key_path: Path = ROOT / "private-data/auth/public.pem"
    auth_private_key_path: Path = ROOT / "private-data/auth/private.pem"
    auth_algorithm: str = "RS256"
    supabase_auth_url: str = ""
    browser_session_seconds: int = Field(default=3600,ge=300,le=28800)
    internal_api_key: str = Field(default="",repr=False)
    laya_base_url: str = "http://127.0.0.1:8001"
    laya_api_key: str = Field(default="",repr=False)
    laya_model_revision: str = ""
    laya_timeout_seconds: float = 2
    search_sql_timeout_seconds: int = Field(default=30,ge=1,le=120)
    laya_circuit_failures: int = 5
    laya_circuit_open_seconds: int = 30
    laya_mode: str = "shadow"
    laya_rerank_enabled: bool = False
    embedding_model: str = "BAAI/bge-m3"
    embedding_model_revision: str = ""
    embedding_model_path: Path = ROOT / "model-cache/bge-m3"
    embedding_dimensions: int = 1024
    embedding_threads: int = Field(default=4,ge=1,le=64)
    embedding_batch_size: int = Field(default=8,ge=1,le=64)
    private_storage_path: Path = ROOT / "private-data/objects"
    deletion_journal_path: Path = ROOT / "private-data/deletion-journal"
    public_storage_path: Path = ROOT / "private-data/legal-originals"
    upload_max_bytes: int = 20 * 1024 * 1024
    upload_max_pages: int = 300
    document_max_chars: int = 2_000_000
    clamav_host: str = ""
    clamav_port: int = 3310
    ocr_enabled: bool = False
    ocr_data_path: Path = ROOT / "model-cache/ocr"
    ocr_model_revision: str = ""
    ocr_language: str = "spa+cat+eus+glg"
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]

    @model_validator(mode="after")
    def enforce_constraints(self):
        if self.auth_algorithm != "RS256" or self.laya_mode != "shadow" or self.laya_rerank_enabled:
            raise ValueError("Only verified RS256 authentication and shadow LAYA are approved")
        if self.embedding_dimensions != 1024 or self.laya_timeout_seconds <= 0:
            raise ValueError("Invalid embedding dimensions or deadline")
        if self.ocr_enabled and not re.fullmatch(r"[0-9a-f]{40}",self.ocr_model_revision):
            raise ValueError("Enabled OCR requires immutable local language artifacts")
        for name in ("LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING", "SEARCH_CHECKPOINTS_ENABLED"):
            if os.environ.get(name, "false").lower() in {"1", "true", "yes"}:
                raise ValueError("Private tracing and checkpointing are prohibited")
        for url in (self.laya_base_url, self.auth_jwks_url):
            if url and urlparse(url).scheme not in {"http", "https"}:
                raise ValueError("Invalid internal service URL")
        if self.supabase_auth_url:
            auth_endpoint=urlparse(self.supabase_auth_url)
            if auth_endpoint.scheme not in {'http','https'} or auth_endpoint.username or auth_endpoint.password:
                raise ValueError('Invalid self-hosted auth endpoint')
            if auth_endpoint.hostname!='localhost':
                try:auth_address=ipaddress.ip_address(auth_endpoint.hostname or '')
                except ValueError:raise ValueError('Auth requires a local/private IP literal') from None
                if not auth_address.is_loopback and not any(auth_address in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','fc00::/7')):
                    raise ValueError('Auth endpoint outside private service boundary')
        endpoint=urlparse(self.laya_base_url)
        if endpoint.username or endpoint.password:raise ValueError("URL credentials prohibited")
        if endpoint.hostname!="localhost":
            try:address=ipaddress.ip_address(endpoint.hostname or "")
            except ValueError:raise ValueError("LAYA requires a local/private IP literal") from None
            networks=("10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","fc00::/7")
            if not address.is_loopback and not any(address in ipaddress.ip_network(n) for n in networks):
                raise ValueError("LAYA endpoint is outside the private service boundary")
        if self.app_env == "production":
            if not all((self.database_url, self.internal_api_key, self.laya_api_key,
                        self.laya_model_revision, self.embedding_model_revision,
                        self.clamav_host, self.auth_issuer, self.auth_audience)):
                raise ValueError("Production credentials, model pins, and malware scanner required")
            if not self.auth_jwks_url and not self.auth_public_key_path.is_file():
                raise ValueError("Production JWT verification key required")
            if any(not re.fullmatch(r"[0-9a-f]{40}", v)
                   for v in (self.laya_model_revision, self.embedding_model_revision)):
                raise ValueError("Immutable model revision SHA required")
        return self
