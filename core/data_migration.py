"""
数据存储迁移管理器 - 配置驱动方案

使用 JSON 配置文件管理数据存储位置，避免文件系统操作带来的占用问题。
"""
import os
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataMigrationError(Exception):
    """数据迁移异常"""
    pass


class DataMigrationManager:
    """数据存储迁移管理器 - 配置驱动方案"""
    
    CONFIG_FILE = ".dayflow.json"
    CONFIG_KEY_DATA_ROOT = "data_root"
    CONFIG_KEY_OLD_DATA_ROOT = "old_data_root_to_delete"
    
    def __init__(self):
        self.config_file = Path.home() / self.CONFIG_FILE
        self.default_data_dir = self._get_default_data_dir()
        logger.info(f"数据迁移管理器初始化，当前数据目录: {self.default_data_dir}")
    
    def _get_config_file(self) -> Path:
        """获取配置文件路径"""
        return Path.home() / self.CONFIG_FILE
    
    def _read_config(self) -> Optional[dict]:
        """
        读取配置文件
        
        Returns:
            配置字典，如果文件不存在或解析失败则返回 None
        """
        config_file = self._get_config_file()
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}")
            return None
    
    def _write_config(self, config: dict) -> None:
        """
        原子写入配置文件
        
        Args:
            config: 要写入的配置字典
            
        Raises:
            DataMigrationError: 写入失败时抛出
        """
        config_file = self._get_config_file()
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=config_file.parent,
                prefix=f'.{self.CONFIG_FILE}.',
                delete=False
            ) as temp_file:
                json.dump(config, temp_file, indent=2, ensure_ascii=False)
                temp_file_path = Path(temp_file.name)
            
            # 原子重命名
            temp_file_path.replace(config_file)
            logger.info(f"配置文件写入成功: {config_file}")
            
        except Exception as e:
            logger.error(f"写入配置文件失败: {e}")
            raise DataMigrationError(f"写入配置文件失败: {str(e)}")
    
    def _get_default_data_dir(self) -> Path:
        """
        获取默认数据目录 - 支持配置驱动
        
        优先级：
        1. 检查 ~/.dayflow.json 配置文件中的 data_root 字段
        2. 如果配置文件存在且路径有效，返回配置路径
        3. 否则返回默认的 LOCALAPPDATA/Dayflow
        
        Returns:
            数据目录路径
        """
        config = self._read_config()
        if config:
            data_root = config.get(self.CONFIG_KEY_DATA_ROOT)
            if data_root:
                try:
                    config_path = Path(data_root)
                    if config_path.exists() and config_path.is_dir():
                        logger.info(f"使用配置文件中的数据目录: {config_path}")
                        return config_path
                    else:
                        logger.warning(
                            f"配置文件中的数据目录不存在或无效: {config_path}，"
                            f"将回退到默认路径"
                        )
                except Exception as e:
                    logger.warning(f"解析配置文件路径失败: {e}，将回退到默认路径")
        
        # 回退到默认路径
        appdata_local = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Dayflow')
        default_path = Path(appdata_local)
        logger.info(f"使用默认数据目录: {default_path}")
        return default_path
    
    def get_current_data_path(self) -> Tuple[Path, bool]:
        """
        获取当前数据路径
        
        Returns:
            (实际路径, 是否为配置驱动)
        """
        config = self._read_config()
        if config and config.get(self.CONFIG_KEY_DATA_ROOT):
            return self.default_data_dir, True
        return self.default_data_dir, False
    
    def get_disk_space_info(self, target_path: Path) -> Tuple[int, int]:
        """
        获取磁盘空间信息
        
        Returns:
            (可用空间, 总空间) 字节
        """
        try:
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                str(target_path),
                ctypes.byref(free_bytes),
                ctypes.byref(total_bytes),
                None
            )
            
            return free_bytes.value, total_bytes.value
        except Exception as e:
            logger.error(f"获取磁盘空间失败: {e}")
            return 0, 0
    
    def _get_directory_size(self, path: Path) -> int:
        """计算目录大小（字节）"""
        total_size = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception as e:
            logger.error(f"计算目录大小失败: {e}")
        return total_size
    
    def _verify_data_integrity(self, source_path: Path, target_path: Path) -> bool:
        """
        验证数据完整性
        
        Args:
            source_path: 源路径
            target_path: 目标路径
            
        Returns:
            验证是否成功
        """
        try:
            # 检查关键文件是否存在
            db_file = target_path / "dayflow.db"
            if not db_file.exists():
                logger.error(f"目标路径缺少数据库文件: {db_file}")
                return False
            
            # 检查数据库文件大小是否一致
            source_db = source_path / "dayflow.db"
            if source_db.exists():
                source_size = source_db.stat().st_size
                target_size = db_file.stat().st_size
                
                if source_size != target_size:
                    logger.error(
                        f"数据库文件大小不一致: "
                        f"源={source_size} 字节, 目标={target_size} 字节"
                    )
                    return False
            
            logger.info("数据完整性验证通过")
            return True
            
        except Exception as e:
            logger.error(f"数据完整性验证失败: {e}")
            return False
    
    def validate_target_path(self, target_path: Path) -> Tuple[bool, str]:
        """
        验证目标路径是否有效
        
        Returns:
            (是否有效, 错误消息)
        """
        try:
            # 检查是否与当前路径相同
            actual_path, _ = self.get_current_data_path()
            if actual_path.resolve() == target_path.resolve():
                return False, "目标路径与当前数据路径相同，无需迁移"
            
            # 检查路径是否存在
            if not target_path.exists():
                return False, "目标路径不存在"
            
            # 检查是否为目录
            if not target_path.is_dir():
                return False, "目标路径不是有效的目录"
            
            # 检查是否有写入权限
            test_file = target_path / ".permission_test"
            try:
                test_file.touch()
                test_file.unlink()
            except Exception:
                return False, "目标路径没有写入权限"
            
            # 检查磁盘空间
            current_size = self._get_directory_size(self.default_data_dir)
            free_space, _ = self.get_disk_space_info(target_path)
            
            if current_size > free_space:
                return False, (
                    f"目标磁盘空间不足。"
                    f"需要: {current_size / (1024**3):.2f} GB，"
                    f"可用: {free_space / (1024**3):.2f} GB"
                )
            
            # 检查目标路径是否包含数据库文件
            db_file = target_path / "dayflow.db"
            if db_file.exists():
                return False, "目标路径已包含数据库文件，请选择空目录"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"验证目标路径失败: {e}")
            return False, f"路径验证失败: {str(e)}"
    
    def migrate_data(self, target_path: Path) -> None:
        """
        迁移数据到目标路径 - 配置驱动方案
        
        流程：
        1. 静默复制数据到目标路径
        2. 验证数据完整性
        3. 更新配置文件，写入新的 data_root
        4. 保留原数据文件夹不动（避免占用问题）
        
        Args:
            target_path: 目标路径
            
        Raises:
            DataMigrationError: 迁移失败时抛出
        """
        try:
            logger.info(f"开始数据迁移: {self.default_data_dir} -> {target_path}")
            
            # === 步骤1：静默复制数据 ===
            logger.info(f"正在复制数据到目标路径: {target_path}")
            if target_path.exists():
                shutil.rmtree(target_path)
            shutil.copytree(self.default_data_dir, target_path)
            logger.info(f"数据复制完成")
            
            # === 步骤2：验证数据完整性 ===
            if not self._verify_data_integrity(self.default_data_dir, target_path):
                raise DataMigrationError("数据完整性验证失败，目标目录数据不完整")
            logger.info("数据完整性验证通过")
            
            # === 步骤3：更新配置文件 ===
            logger.info(f"更新配置文件，设置新的数据路径: {target_path}")
            config = self._read_config() or {}
            config[self.CONFIG_KEY_DATA_ROOT] = str(target_path.resolve())
            
            # 记录原始数据路径，用于启动时删除
            old_data_root = self.default_data_dir.resolve()
            config[self.CONFIG_KEY_OLD_DATA_ROOT] = str(old_data_root)
            logger.info(f"记录原始数据路径，将在下次启动时删除: {old_data_root}")
            
            self._write_config(config)
            logger.info("配置文件更新成功")
            
            logger.info("数据迁移完成！")
            
        except Exception as e:
            logger.error(f"数据迁移失败: {e}")
            raise DataMigrationError(f"数据迁移失败: {str(e)}")
    
    def backup_data(self) -> Path:
        """
        备份数据
        
        Returns:
            备份目录路径
        """
        try:
            backup_dir = Path.home() / "Desktop" / f"Dayflow_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"创建数据备份: {backup_dir}")
            
            actual_path, _ = self.get_current_data_path()
            if actual_path.exists():
                shutil.copytree(actual_path, backup_dir)
                logger.info(f"数据备份成功: {backup_dir}")
            else:
                logger.warning(f"数据路径不存在，跳过备份: {actual_path}")
            
            return backup_dir
        except Exception as e:
            logger.error(f"备份数据失败: {e}")
            raise DataMigrationError(f"备份数据失败: {str(e)}")
    
    def cleanup_old_data(self) -> bool:
        """
        清理旧数据文件夹
        
        在程序启动时调用，检查配置文件中是否有待删除的旧数据路径。
        如果有且当前使用的不是该路径，则删除旧数据文件夹并清除配置标记。
        
        Returns:
            是否执行了清理操作
        """
        try:
            config = self._read_config()
            if not config:
                return False
            
            old_data_root_str = config.get(self.CONFIG_KEY_OLD_DATA_ROOT)
            if not old_data_root_str:
                return False
            
            old_data_root = Path(old_data_root_str)
            
            # 检查旧数据路径是否与当前路径相同
            current_path = self.default_data_dir.resolve()
            if old_data_root == current_path:
                logger.info(f"旧数据路径与当前路径相同，跳过删除: {old_data_root}")
                return False
            
            # 检查旧数据路径是否存在
            if not old_data_root.exists():
                logger.info(f"旧数据路径不存在，清除配置标记: {old_data_root}")
                config.pop(self.CONFIG_KEY_OLD_DATA_ROOT, None)
                self._write_config(config)
                return True
            
            # 删除旧数据文件夹
            logger.info(f"开始删除旧数据文件夹: {old_data_root}")
            try:
                shutil.rmtree(old_data_root)
                logger.info(f"旧数据文件夹删除成功: {old_data_root}")
            except Exception as e:
                logger.error(f"删除旧数据文件夹失败: {e}，将清除配置标记")
            
            # 清除配置标记
            config.pop(self.CONFIG_KEY_OLD_DATA_ROOT, None)
            self._write_config(config)
            logger.info("旧数据路径配置标记已清除")
            
            return True
            
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return False
