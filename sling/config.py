"""Configuration models for Sling."""

from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GeneralConfig(BaseModel):
    """General application settings."""
    output_dir: Path = Field(default=Path("./scans"))
    temp_dir: Path = Field(default=Path("./tmp"))
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    max_parallel: int = Field(default=4, ge=1, le=16)


class ToolPathsConfig(BaseModel):
    """External tool paths (auto-detected if not set)."""
    subfinder: str = "subfinder"
    shuffledns: str = "shuffledns"
    puredns: str = "puredns"
    dnsx: str = "dnsx"
    naabu: str = "naabu"
    tew: str = "tew"
    httpx: str = "httpx"
    katana: str = "katana"


class WordlistConfig(BaseModel):
    """Wordlist configuration."""
    resolvers: Path = Path("lists/resolvers.txt")
    subdomains: Path = Path("lists/subdomains-top1million-20000.txt")
    auto_update: bool = True


class DNSPassiveConfig(BaseModel):
    """Passive DNS enumeration settings."""
    enabled: bool = True
    timeout: int = Field(default=300, ge=10)


class DNSActiveConfig(BaseModel):
    """Active DNS bruteforce settings."""
    enabled: bool = True
    timeout: int = Field(default=600, ge=10)


class DNSResolutionConfig(BaseModel):
    """DNS resolution settings."""
    enabled: bool = True
    timeout: int = Field(default=300, ge=10)


class DNSConfig(BaseModel):
    """DNS enumeration and resolution configuration."""
    passive: DNSPassiveConfig = Field(default_factory=DNSPassiveConfig)
    active: DNSActiveConfig = Field(default_factory=DNSActiveConfig)
    resolution: DNSResolutionConfig = Field(default_factory=DNSResolutionConfig)


class PortScanConfig(BaseModel):
    """Port scanning configuration."""
    enabled: bool = True
    ports: str = Field(default="top-1000", description="Port range: 'top-100', 'top-1000', 'full', or comma-separated")
    rate: int = Field(default=1000, ge=1, description="Packets per second")
    timeout: int = Field(default=600, ge=10)


class HTTPProbeConfig(BaseModel):
    """HTTP probing configuration."""
    enabled: bool = True
    timeout: int = Field(default=30, ge=5)


class PortConfig(BaseModel):
    """Port scanning and HTTP discovery configuration."""
    scan: PortScanConfig = Field(default_factory=PortScanConfig)
    http_probe: HTTPProbeConfig = Field(default_factory=HTTPProbeConfig)


class CrawlConfig(BaseModel):
    """Crawling configuration."""
    enabled: bool = True
    depth: int = Field(default=2, ge=0, le=10)
    timeout: int = Field(default=600, ge=10)
    js_extraction: bool = True


class Config(BaseSettings):
    """Main configuration model."""
    model_config = SettingsConfigDict(
        yaml_file="config.yaml",
        yaml_file_encoding="utf-8",
        env_prefix="SLING_",
        env_nested_delimiter="__",
    )

    general: GeneralConfig = Field(default_factory=GeneralConfig)
    tools: ToolPathsConfig = Field(default_factory=ToolPathsConfig)
    wordlists: WordlistConfig = Field(default_factory=WordlistConfig)
    dns: DNSConfig = Field(default_factory=DNSConfig)
    port: PortConfig = Field(default_factory=PortConfig)
    crawl: CrawlConfig = Field(default_factory=CrawlConfig)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure paths are absolute
        self.general.output_dir = self.general.output_dir.resolve()
        self.general.temp_dir = self.general.temp_dir.resolve()
        self.wordlists.resolvers = self.wordlists.resolvers.resolve()
        self.wordlists.subdomains = self.wordlists.subdomains.resolve()