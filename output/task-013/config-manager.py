#!/usr/bin/env python3
"""
统一配置管理系统核心实现
"""

import json
import hashlib
import hmac
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from cryptography.fernet import Fernet

@dataclass
class ConfigVersion:
    version: int
    value: str
    encrypted: bool
    created_at: str
    created_by: str
    comment: str = ""

@dataclass
class ConfigKey:
    key: str
    description: str = ""
    is_sensitive: bool = False
    versions: List[ConfigVersion] = field(default_factory=list)
    
    def get_latest(self) -> ConfigVersion:
        return self.versions[-1]

@dataclass
class ConfigEnvironment:
    env_name: str
    keys: Dict[str, ConfigKey] = field(default_factory=dict)

@dataclass
class ConfigApplication:
    app_name: str
    envs: Dict[str, ConfigEnvironment] = field(default_factory=dict)

class ConfigManager:
    def __init__(self, encryption_key: bytes = None):
        self.apps: Dict[str, ConfigApplication] = {}
        # 如果没提供，生成一个新密钥
        if encryption_key is None:
            encryption_key = Fernet.generate_key()
        self.cipher = Fernet(encryption_key)
    
    def encrypt(self, plaintext: str) -> str:
        """加密敏感配置"""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """解密敏感配置"""
        return self.cipher.decrypt(ciphertext.encode()).decode()
    
    def create_app(self, app_name: str) -> ConfigApplication:
        """创建应用"""
        app = ConfigApplication(app_name)
        self.apps[app_name] = app
        return app
    
    def create_env(self, app_name: str, env_name: str) -> ConfigEnvironment:
        """创建环境"""
        app = self.apps.get(app_name)
        if not app:
            app = self.create_app(app_name)
        env = ConfigEnvironment(env_name)
        app.envs[env_name] = env
        return env
    
    def set_config(
        self,
        app_name: str,
        env_name: str,
        key: str,
        value: str,
        created_by: str,
        is_sensitive: bool = False,
        comment: str = "",
    ) -> ConfigVersion:
        """设置配置，新增版本"""
        # 找到或创建应用环境
        app = self.apps.get(app_name)
        if not app:
            app = self.create_app(app_name)
        env = app.envs.get(env_name)
        if not env:
            env = self.create_env(app_name, env_name)
        config_key = env.keys.get(key)
        
        if not config_key:
            config_key = ConfigKey(key=key, is_sensitive=is_sensitive)
            env.keys[key] = config_key
        
        # 如果敏感，加密存储
        encrypted = False
        store_value = value
        if is_sensitive:
            store_value = self.encrypt(value)
            encrypted = True
        
        version = ConfigVersion(
            version=len(config_key.versions) + 1,
            value=store_value,
            encrypted=encrypted,
            created_at=datetime.utcnow().isoformat(),
            created_by=created_by,
            comment=comment,
        )
        
        config_key.versions.append(version)
        return version
    
    def get_config(
        self,
        app_name: str,
        env_name: str,
        key: str,
        decrypt: bool = True,
    ) -> Optional[str]:
        """获取配置最新值"""
        app = self.apps.get(app_name)
        if not app:
            return None
        env = app.envs.get(env_name)
        if not env:
            return None
        config_key = env.keys.get(key)
        if not config_key:
            return None
        
        latest = config_key.get_latest()
        if latest.encrypted and decrypt:
            return self.decrypt(latest.value)
        return latest.value
    
    def get_config_history(
        self,
        app_name: str,
        env_name: str,
        key: str,
    ) -> List[ConfigVersion]:
        """获取配置历史版本"""
        app = self.apps.get(app_name)
        if not app:
            return []
        env = app.envs.get(env_name)
        if not env:
            return []
        config_key = env.keys.get(key)
        if not config_key:
            return []
        return config_key.versions
    
    def rollback(
        self,
        app_name: str,
        env_name: str,
        key: str,
        to_version: int,
        rolled_by: str,
    ) -> bool:
        """回滚到指定版本"""
        app = self.apps.get(app_name)
        if not app:
            return False
        env = app.envs.get(env_name)
        if not env:
            return False
        config_key = env.keys.get(key)
        if not config_key:
            return False
        
        target_version = next((v for v in config_key.versions if v.version == to_version), None)
        if not target_version:
            return False
        
        # 添加新版本，内容和目标版本一样，表示回滚
        self.set_config(
            app_name, env_name, key,
            target_version.value,
            rolled_by,
            target_version.encrypted,
            comment=f"Rollback to version {to_version}"
        )
        return True
    
    def validate_config_format(self, config_str: str, format_type: str = "json") -> bool:
        """验证配置格式"""
        if format_type == "json":
            try:
                json.loads(config_str)
                return True
            except json.JSONDecodeError:
                return False
        # 可以添加yaml等格式验证
        return True
    
    def export_all_configs(self, app_name: str, env_name: str) -> Dict[str, str]:
        """导出当前环境所有配置（解密敏感配置需要权限）"""
        result = {}
        app = self.apps.get(app_name)
        if not app:
            return result
        env = app.envs.get(env_name)
        if not env:
            return result
        
        for key, config_key in env.keys.items():
            latest = config_key.get_latest()
            if latest.encrypted:
                result[key] = self.decrypt(latest.value)
            else:
                result[key] = latest.value
        
        return result

if __name__ == "__main__":
    # 使用示例
    manager = ConfigManager()
    
    # 设置普通配置
    manager.set_config(
        "user-service", "production",
        "port", "8080",
        created_by="oc-coze",
        comment="服务端口"
    )
    
    # 设置敏感配置
    manager.set_config(
        "user-service", "production",
        "db_password", "mysecretpassword",
        created_by="oc-coze",
        is_sensitive=True,
        comment="数据库密码"
    )
    
    # 读取
    print("port:", manager.get_config("user-service", "production", "port"))
    print("db_password:", manager.get_config("user-service", "production", "db_password"))
    
    # 查看历史
    history = manager.get_config_history("user-service", "production", "port")
    print(f"port 版本数: {len(history)}")
