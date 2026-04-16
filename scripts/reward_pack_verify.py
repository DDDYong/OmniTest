"""
-------------------------------------------------
File:           reward_pack_verify.py
Author:         duanyang
Date:           2026/3/31
-------------------------------------------------
Description:
This file contains the bonus_pack_verify module, which...
-------------------------------------------------
"""
import random
from typing import Dict, List, Any, Optional

from config.config_manager import config_manager
from scripts.reward_type_mapper import RewardTypeMapper
from utils import logger, util
from utils.api import ApiClient
from utils.db.mysql_client import MySQLClient
from utils.decorator import wait_with_jitter
from utils.file import FileHandler


class RewardPackVerification:
    """
    奖励包验证模块
    """

    SUPPORTED_UNITS = {"天", "小时", "个"}
    SEX_RULES = {0: "不限性别", 1: "男", 2: "女"}
    ACTOR_RULES = {0: "不限身份", 1: "非陪伴师", 2: "陪伴师"}

    def __init__(self, activity_number: int, activity_config_path: str, reward_pack_rank_mapping: Optional[
        Dict[int, int]] = None):
        """
        初始化活动奖励验证模块

        Args:
            activity_number: 活动ID
            activity_config_path: 活动奖励配置文件路径
        """
        self.activity_number = activity_number
        self.activity_config_path = activity_config_path
        self.reward_pack_rank_mapping = reward_pack_rank_mapping or {}
        self.reward_pack_rank_mapping_by_activity: Dict[int, Dict[int, int]] = {}
        self.logger = logger
        self.filehandler = FileHandler()
        self.api_client = ApiClient()
        self.db = MySQLClient(config_manager.get_mysql_config())
        self.reward_mapper = RewardTypeMapper()

        # 缓存字典, 减少重复的文件读取和数据库查询
        self._cache = {
            "activity_reward_config_doc": [],
            "activity_reward_config_db": [],
            "expected_rewards": {},  # {(ranking, activity_type): expected_rewards}
            "activity_ranking_data": {},  # 榜单用户排名数据
            "user_expected_rewards": {},  # {user_id: {rank_type: {ranking: expected_rewards}}}
        }

    @staticmethod
    def _safe_int(value: Any) -> Any:
        """尽量转为整数, 失败时返回原值"""
        try:
            if value is None or value == "":
                return value
            return int(value)
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _get_rank_scope(activity_type_name: str) -> str:
        """根据榜单名称识别榜单语义类型"""
        normalized_name = str(activity_type_name or "").strip()
        if "日榜" in normalized_name:
            return "day"
        if "总榜" in normalized_name:
            return "total"
        return "unknown"

    @staticmethod
    def _normalize_activity_type_name(activity_type_name: Any) -> str:
        """标准化榜单名称, 作为复合键的一部分"""
        return str(activity_type_name or "").strip()

    def _build_rank_key(self, config: Dict[str, Any]) -> str:
        """基于 rank_category 和 activityType_name 构造唯一榜单键"""
        rank_category = self._safe_int(config.get("rank_category"))
        activity_type_name = self._normalize_activity_type_name(config.get("activityType_name", ""))
        return f"{activity_type_name}_{rank_category}"

    def _build_activity_config_map(self, activity_reward_config: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """构建榜单唯一键到配置的映射"""
        activity_config_map: Dict[str, Dict[str, Any]] = {}
        for config in activity_reward_config:
            if not isinstance(config, dict):
                continue
            rank_key = self._build_rank_key(config)
            if rank_key in activity_config_map:
                self.logger.warning(f"检测到重复榜单配置键: {rank_key}, 后面的配置将覆盖前面的配置")
            activity_config_map[rank_key] = config
        return activity_config_map

    def _find_config_by_rank_type(self, activity_type: Any, activity_reward_config: List[Dict[str, Any]]) -> Optional[
        Dict[str, Any]]:
        """根据运行态榜单键查找对应配置, 兼容旧的 rank_category 传参"""
        normalized_activity_type = str(activity_type)
        activity_config_map = self._build_activity_config_map(activity_reward_config)
        if normalized_activity_type in activity_config_map:
            return activity_config_map[normalized_activity_type]

        matched_configs = [
            config for config in activity_reward_config
            if isinstance(config, dict) and str(self._safe_int(config.get("rank_category"))) == normalized_activity_type
        ]
        if len(matched_configs) == 1:
            return matched_configs[0]
        if len(matched_configs) > 1:
            self.logger.warning(
                f"榜单类型 {activity_type} 对应多个配置, 请使用复合键区分: "
                f"{[self._build_rank_key(config) for config in matched_configs]}"
            )
        return None

    def _normalize_filter_rank_types(self, filter_rank_types: Optional[List[Any]],
                                     activity_reward_config: List[Dict[str, Any]]) -> Optional[List[str]]:
        """兼容旧的 rank_category 过滤参数, 统一转换为复合键列表"""
        if filter_rank_types is None:
            return None

        normalized_rank_types: List[str] = []
        for rank_type in filter_rank_types:
            normalized_rank_type = str(rank_type)
            if "__" in normalized_rank_type:
                normalized_rank_types.append(normalized_rank_type)
                continue

            matched_configs = [
                config for config in activity_reward_config
                if isinstance(config, dict) and str(self._safe_int(config.get("rank_category"))) == normalized_rank_type
            ]
            normalized_rank_types.extend(self._build_rank_key(config) for config in matched_configs)

        return list(dict.fromkeys(normalized_rank_types))

    def _extract_rank_category_from_rank_type(self, activity_type: Any) -> Any:
        """从运行态榜单键中提取 rank_category"""
        normalized_activity_type = str(activity_type)
        rank_category = normalized_activity_type.split("__", 1)[0]
        return self._safe_int(rank_category)

    def _get_activity_type_name_by_rank_type(self, activity_type: Any,
                                             activity_reward_config: List[Dict[str, Any]]) -> str:
        """根据运行态榜单键获取榜单名称"""
        config = self._find_config_by_rank_type(activity_type, activity_reward_config)
        if config:
            return config.get("activityType_name", "未知榜单")
        return f"未知({activity_type})"

    def _extract_pack_id(self, data: Dict[str, Any]) -> Any:
        """提取奖励包ID"""
        for key in ("rewardPackId", "bonusPackId", "reward_pack_id", "bonus_pack_id", "packId", "pack_id"):
            if key in data and data.get(key) not in (None, ""):
                return self._safe_int(data.get(key))
        return None

    def _map_db_rank_number(self, rank_number: Any, activity_type: Any = None) -> Any:
        """将数据库中的奖励包ID映射为排名, 优先使用YAML中的奖励包映射"""
        mapped_value = self._safe_int(rank_number)

        if activity_type is not None:
            normalized_activity_type = self._safe_int(activity_type)
            activity_mapping = self.reward_pack_rank_mapping_by_activity.get(normalized_activity_type, {})
            if mapped_value in activity_mapping:
                return activity_mapping[mapped_value]

        if mapped_value in self.reward_pack_rank_mapping:
            return self.reward_pack_rank_mapping[mapped_value]
        return mapped_value

    @staticmethod
    def _extract_reward_value(reward: Dict[str, Any]) -> Any:
        """提取奖励数值, 兼容旧的valid_days和新的rewardCount/amount"""
        for key in ("rewardCount", "valid_days", "amount", "count"):
            if key in reward and reward.get(key) is not None:
                return reward.get(key)
        return 0

    @classmethod
    def _get_reward_unit(cls, unit: Any) -> str:
        """奖励单位只处理 天/小时/个, 未配置时默认按天处理"""
        if unit in (None, ""):
            return "天"
        normalized_unit = str(unit).strip()
        if normalized_unit in cls.SUPPORTED_UNITS:
            return normalized_unit
        return normalized_unit

    @staticmethod
    def _is_duration_unit(unit: Any) -> bool:
        """判断unit是否表示时长"""
        return RewardPackVerification._get_reward_unit(unit) in {"天", "小时"}

    def _normalize_reward_item(self, reward: Dict[str, Any]) -> Dict[str, Any]:
        """归一化奖励项, 兼容旧/新配置结构"""
        normalized_reward = dict(reward)
        reward_type = self._safe_int(normalized_reward.get("rewardType", 0)) or 0
        reward_id = self._safe_int(normalized_reward.get("rewardId", 0)) or 0
        reward_value = self._extract_reward_value(normalized_reward)

        normalized_reward["rewardType"] = reward_type
        normalized_reward["rewardId"] = reward_id
        normalized_reward["rewardCount"] = self._safe_int(reward_value)
        normalized_reward.setdefault("valid_days", self._safe_int(reward_value))
        normalized_reward[
            "unit"] = self._get_reward_unit(normalized_reward.get("unit", normalized_reward.get("rewardUnit")))
        normalized_reward["sex"] = self._safe_int(normalized_reward.get("sex", 0)) or 0
        normalized_reward["actor"] = self._safe_int(normalized_reward.get("actor", 0)) or 0
        normalized_reward.setdefault("rewardType_name", self.reward_mapper.get_reward_type_name(reward_type))
        normalized_reward.setdefault("reward_desc", normalized_reward.get("rewardType_desc") or self.reward_mapper.get_reward_type_desc(reward_type))
        return normalized_reward

    def _build_reward_pack_map(self, config: Dict[str, Any]) -> Dict[Any, List[Dict[str, Any]]]:
        """构建奖励包ID到奖励列表的映射"""
        reward_packs = config.get("reward_packs") or config.get("bonus_packs") or config.get("rewardPackages") or []
        reward_pack_map: Dict[Any, List[Dict[str, Any]]] = {}

        if isinstance(reward_packs, dict):
            for pack_id, pack_data in reward_packs.items():
                normalized_pack_id = self._safe_int(pack_id)
                rewards = pack_data.get("rewards", []) if isinstance(pack_data, dict) else (pack_data or [])
                reward_pack_map[normalized_pack_id] = [self._normalize_reward_item(reward) for reward in rewards]
            return reward_pack_map

        for pack in reward_packs:
            if not isinstance(pack, dict):
                continue
            pack_id = self._extract_pack_id(pack)
            if pack_id is None:
                pack_id = self._safe_int(pack.get("id"))
            if pack_id is None:
                continue
            reward_pack_map[pack_id] = [self._normalize_reward_item(reward) for reward in pack.get("rewards", [])]

        return reward_pack_map

    def _build_rank_pack_mapping(self, config: Dict[str, Any]) -> Dict[int, Any]:
        """构建排名到奖励包ID的映射"""
        rank_pack_mapping: Dict[int, Any] = {}
        activity_type = self._safe_int(config.get("activityType"))
        reward_details = config.get("reward_details", [])
        for reward_detail in reward_details:
            if not isinstance(reward_detail, dict):
                continue
            rank = self._safe_int(reward_detail.get("rank"))
            pack_id = self._extract_pack_id(reward_detail)
            if isinstance(rank, int) and pack_id is not None:
                rank_pack_mapping[rank] = pack_id

        explicit_mapping = (
                config.get("reward_pack_mapping")
                or config.get("bonus_pack_mapping")
                or config.get("rank_reward_pack_mapping")
                or config.get("rank_bonus_pack_mapping")
        )
        if isinstance(explicit_mapping, dict):
            for rank, pack_id in explicit_mapping.items():
                normalized_rank = self._safe_int(rank)
                if isinstance(normalized_rank, int):
                    rank_pack_mapping[normalized_rank] = self._safe_int(pack_id)
        elif isinstance(explicit_mapping, list):
            for mapping_item in explicit_mapping:
                if not isinstance(mapping_item, dict):
                    continue
                normalized_rank = self._safe_int(mapping_item.get("rank"))
                pack_id = self._extract_pack_id(mapping_item)
                if isinstance(normalized_rank, int) and pack_id is not None:
                    rank_pack_mapping[normalized_rank] = pack_id

        if rank_pack_mapping:
            self.reward_pack_rank_mapping = dict(rank_pack_mapping)
            if isinstance(activity_type, int):
                self.reward_pack_rank_mapping_by_activity[activity_type] = dict(rank_pack_mapping)
        return rank_pack_mapping

    @staticmethod
    def _build_doc_match_key(activity_type: Any, rank: Any, reward_type: Any, reward_desc: str,
                             sex: Any = 0, actor: Any = 0) -> str:
        """构造文档/数据库匹配key, 包含描述以支持同类型多奖励并存"""
        normalized_desc = (reward_desc or "").strip()
        query_key = f"{activity_type}_{rank}_{reward_type}_{normalized_desc}"
        if reward_type == 2:
            if sex == 1 or "(男)" in normalized_desc:
                query_key += "_男"
            elif sex == 2 or "(女)" in normalized_desc:
                query_key += "_女"
        if reward_type in {5, 16}:
            if actor == 1:
                query_key += "_非陪伴师"
            elif actor == 2:
                query_key += "_陪伴师"
        return query_key

    def _get_rewards_for_rank(self, config: Dict[str, Any], ranking: int) -> List[Dict[str, Any]]:
        """根据排名从旧结构或奖励包结构中展开奖励"""
        reward_details = config.get("reward_details", [])
        reward_detail_dict = {
            self._safe_int(reward_detail.get("rank")): reward_detail
            for reward_detail in reward_details
            if isinstance(reward_detail, dict) and isinstance(self._safe_int(reward_detail.get("rank")), int)
        }

        if ranking in reward_detail_dict:
            rewards = reward_detail_dict[ranking].get("rewards", [])
            if rewards:
                return [self._normalize_reward_item(reward) for reward in rewards]

        rank_pack_mapping = self._build_rank_pack_mapping(config)
        reward_pack_map = self._build_reward_pack_map(config)
        reward_pack_id = rank_pack_mapping.get(ranking)
        if reward_pack_id is None and ranking in reward_detail_dict:
            reward_pack_id = self._extract_pack_id(reward_detail_dict[ranking])
        if reward_pack_id is None:
            return []

        return [dict(reward) for reward in reward_pack_map.get(reward_pack_id, [])]

    def _build_doc_pack_name_map(self, activity_reward_config: List[Dict[str, Any]]) -> Dict[Any, str]:
        """从YAML配置中提取奖励包ID到奖励包名称的映射"""
        pack_name_map: Dict[Any, str] = {}
        for config in activity_reward_config:
            reward_packs = config.get("reward_packs") or []
            for reward_pack in reward_packs:
                if not isinstance(reward_pack, dict):
                    continue
                pack_id = self._extract_pack_id(reward_pack)
                if pack_id is None:
                    continue
                pack_name_map[pack_id] = reward_pack.get("rewardPackName") or reward_pack.get("packName") or ""
        return pack_name_map

    def _build_doc_pack_activity_map(self, activity_reward_config: List[Dict[str, Any]]) -> Dict[Any, Dict[str, Any]]:
        """从YAML配置中提取奖励包ID到榜单信息的映射"""
        pack_activity_map: Dict[Any, Dict[str, Any]] = {}
        for config in activity_reward_config:
            activity_type = self._safe_int(config.get("activityType"))
            activity_type_name = config.get("activityType_name", "")
            reward_packs = config.get("reward_packs") or []
            for reward_pack in reward_packs:
                if not isinstance(reward_pack, dict):
                    continue
                pack_id = self._extract_pack_id(reward_pack)
                if pack_id is None:
                    continue
                pack_activity_map[pack_id] = {
                    "activityType": activity_type,
                    "activityType_name": activity_type_name,
                }
        return pack_activity_map

    def _get_doc_pack_ids(self, activity_reward_config: List[Dict[str, Any]]) -> List[int]:
        """从YAML配置中提取所有奖励包ID"""
        pack_ids: List[int] = []
        for config in activity_reward_config:
            reward_packs = config.get("reward_packs") or []
            for reward_pack in reward_packs:
                if not isinstance(reward_pack, dict):
                    continue
                pack_id = self._extract_pack_id(reward_pack)
                if isinstance(pack_id, int) and pack_id not in pack_ids:
                    pack_ids.append(pack_id)
        return pack_ids

    def get_activity_reward_config_doc(self, activity_config_path: str) -> List[Dict[str, Any]]:
        """
        获取活动文档中的奖励配置

        Args:
            activity_config_path: 活动奖励配置文件路径

        Returns:
            dict: 奖励配置
        """
        # 检查缓存中是否已有文档配置, 避免重复读取YAML文件
        if not self._cache["activity_reward_config_doc"]:
            self.logger.info("获取活动文档中的奖励配置")
            activity_reward_config = self.filehandler.read_yaml(activity_config_path)
            for config in activity_reward_config:
                if isinstance(config, dict):
                    self._build_rank_pack_mapping(config)
            self.logger.info(f"文档配置: {activity_reward_config}")
            self._cache["activity_reward_config_doc"] = activity_reward_config
        else:
            self.logger.debug("使用缓存的活动文档奖励配置")
            activity_reward_config = self._cache["activity_reward_config_doc"]
        return activity_reward_config

    def get_activity_reward_config_db(self) -> List[Dict[str, Any]]:
        """
        获取数据库中的奖励配置, 并根据服务端映射处理奖励类型

        Returns:
            List[Dict]: 处理后的奖励配置列表
        """
        # 检查缓存中是否已有数据库配置, 避免重复查询数据库
        if not self._cache["activity_reward_config_db"]:
            self.logger.info("获取数据库中的奖励配置")

            activity_reward_config = self.get_activity_reward_config_doc(self.activity_config_path)
            pack_ids = self._get_doc_pack_ids(activity_reward_config)
            if not pack_ids:
                self.logger.warning("YAML中未找到可用的奖励包ID配置")
                return []

            placeholders = ", ".join(["%s"] * len(pack_ids))
            query = f"""
                SELECT activityType AS rewardPackId, rankNumber, rewardType, rewardId, rewardCount, sex, actor, unit
                FROM `kong_test`.`reward_option_config`
                WHERE activityNumber = %s and rewardType IN (1, 2, 3, 5, 6, 9, 10, 12, 15, 16)
                  AND activityType IN ({placeholders})
            """
            rewards = self.db.execute_query(query, (self.activity_number, *pack_ids))

            if not rewards:
                self.logger.warning(f"未找到活动 {self.activity_number} 的奖励配置")
                activity_reward_config = []
            else:
                # 处理奖励配置
                db_reward_config = []
                pack_name_map = self._build_doc_pack_name_map(activity_reward_config)
                pack_activity_map = self._build_doc_pack_activity_map(activity_reward_config)
                for reward in rewards:
                    reward["rewardPackId"] = self._safe_int(reward.get("rewardPackId"))
                    reward["rewardPackName"] = pack_name_map.get(reward["rewardPackId"], "")
                    reward["originRankNumber"] = self._safe_int(reward.get("rankNumber"))
                    reward["activityType"] = pack_activity_map.get(reward["rewardPackId"], {}).get("activityType")
                    reward["activityType_name"] = pack_activity_map.get(
                        reward["rewardPackId"], {}).get("activityType_name", "")
                    reward_type = reward.get("rewardType", 0)

                    # 根据服务端映射处理奖励类型
                    reward["rewardType_name"] = self.reward_mapper.get_reward_type_name(reward_type)
                    reward["rewardType_desc"] = self.reward_mapper.get_reward_type_desc(reward_type)
                    reward.setdefault("reward_desc", reward.get("rewardType_desc"))
                    db_reward_config.append(reward)

                activity_reward_config = db_reward_config

            self.logger.info(f"数据库配置: {activity_reward_config}")
            self._cache["activity_reward_config_db"] = activity_reward_config
        else:
            self.logger.debug("使用缓存的数据库奖励配置")
            activity_reward_config = self._cache["activity_reward_config_db"]
        return activity_reward_config

    def verify_db_vs_doc(self, doc_config, db_config):
        """
        校验每个奖励配置在文档数据库中是否一致

        Args:
            doc_config: 文档配置
            db_config: 数据库配置

        Returns:
            Dict: 差异汇总字典
        """

        doc_quick_query = {}
        for config in doc_config:
            reward_packs = config.get("reward_packs") or []
            for reward_pack in reward_packs:
                if not isinstance(reward_pack, dict):
                    continue
                reward_pack_id = self._extract_pack_id(reward_pack)
                reward_pack_name = reward_pack.get("rewardPackName") or reward_pack.get("packName") or ""
                for reward in reward_pack.get("rewards", []):
                    normalized_reward = self._normalize_reward_item(reward)
                    reward_type_doc = normalized_reward.get("rewardType")
                    reward_sex_doc = self._safe_int(normalized_reward.get("sex", 0)) or 0
                    reward_actor_doc = self._safe_int(normalized_reward.get("actor", 0)) or 0
                    bucket_key = (reward_pack_id, reward_type_doc, reward_sex_doc, reward_actor_doc)

                    doc_quick_query.setdefault(bucket_key, []).append({
                        "rewardPackId_doc": reward_pack_id,
                        "rewardPackName_doc": reward_pack_name,
                        "rewardId_doc": normalized_reward.get("rewardId"),
                        "reward_value_doc": normalized_reward.get("rewardCount"),
                        "unit_doc": self._get_reward_unit(normalized_reward.get("unit")),
                        "sex_doc": reward_sex_doc,
                        "actor_doc": reward_actor_doc,
                        "rewardType_name_doc": normalized_reward.get("rewardType_name"),
                        "rewardType_desc_doc": normalized_reward.get("reward_desc", ""),
                    })

        differences = {
            "db_exist_doc_not": [],
            "rewardId_mismatch": [],
            "reward_value_mismatch": [],
            "unit_mismatch": []
        }

        for db_item in db_config:
            reward_pack_id_db = self._safe_int(db_item.get("rewardPackId"))
            reward_pack_name_db = db_item.get("rewardPackName", "")
            reward_type_db = db_item.get("rewardType")
            reward_id_db = db_item.get("rewardId")
            reward_count_db = db_item.get("rewardCount")
            reward_type_name_db = db_item.get("rewardType_name")
            reward_type_desc_db = db_item.get("rewardType_desc")
            reward_desc_db = db_item.get("reward_desc") or reward_type_desc_db or ""
            reward_type_sex_db = self._safe_int(db_item.get("sex", 0)) or 0
            reward_type_actor_db = self._safe_int(db_item.get("actor", 0)) or 0
            unit_db = self._get_reward_unit(db_item.get("unit"))

            bucket_key = (reward_pack_id_db, reward_type_db, reward_type_sex_db, reward_type_actor_db)
            doc_candidates = doc_quick_query.get(bucket_key, [])

            if not doc_candidates:
                differences["db_exist_doc_not"].append({
                    "db_info": {
                        "activityType": db_item.get("activityType"),
                        "activityType_name": db_item.get("activityType_name", ""),
                        "rewardPackId": reward_pack_id_db,
                        "rewardPackName": reward_pack_name_db,
                        "rewardType": reward_type_db,
                        "rewardType_name": reward_type_name_db,
                        "rewardType_desc": reward_type_desc_db,
                        "rewardId": reward_id_db,
                        "rewardCount": reward_count_db,
                        "sex": reward_type_sex_db,
                        "actor": reward_type_actor_db,
                        "unit": unit_db,
                    },
                    "reason": "该奖励在数据库中存在, 但文档配置中无对应记录"
                })
                continue

            exact_doc_info = next(
                (
                    item for item in doc_candidates
                    if item["rewardId_doc"] == reward_id_db
                       and item.get("reward_value_doc") == reward_count_db
                       and str(item.get("unit_doc")) == str(unit_db)
                ),
                None,
            )
            doc_info = exact_doc_info or next(
                (item for item in doc_candidates if item["rewardId_doc"] == reward_id_db),
                None,
            ) or doc_candidates[0]

            if doc_info["rewardId_doc"] != reward_id_db:
                differences["rewardId_mismatch"].append({
                    "common_info": {
                        "rewardPackId": reward_pack_id_db,
                        "rewardPackName_doc": doc_info["rewardPackName_doc"],
                        "rewardType": reward_type_db,
                        "rewardType_name_doc": doc_info["rewardType_name_doc"],
                        "rewardType_name_db": reward_type_name_db,
                        "rewardType_desc_db": reward_type_desc_db,
                        "rewardType_desc_doc": doc_info["rewardType_desc_doc"],
                    },
                    "rewardId_doc": doc_info["rewardId_doc"],
                    "rewardId_db": reward_id_db,
                    "reason": "奖励ID不一致(数据库配置的奖励ID与文档不匹配)"
                })

            if reward_type_db in {1, 6}:
                if reward_count_db != 1:
                    differences["reward_value_mismatch"].append({
                        "common_info": {
                            "rewardPackId": reward_pack_id_db,
                            "rewardPackName_doc": doc_info["rewardPackName_doc"],
                            "rewardType": reward_type_db,
                            "rewardType_name_doc": doc_info["rewardType_name_doc"],
                            "rewardType_desc_db": reward_type_desc_db,
                            "rewardType_desc_doc": doc_info["rewardType_desc_doc"],
                        },
                        "rewardId_db": reward_id_db,
                        "reward_value_doc": 1,
                        "rewardCount_db": reward_count_db,
                        "reason": "永久奖励数量错误(应为1个)"
                    })
                continue

            if doc_info.get("reward_value_doc") != reward_count_db:
                differences["reward_value_mismatch"].append({
                    "common_info": {
                        "rewardPackId": reward_pack_id_db,
                        "rewardPackName_doc": doc_info["rewardPackName_doc"],
                        "rewardType": reward_type_db,
                        "rewardType_name_doc": doc_info["rewardType_name_doc"],
                        "rewardType_desc_db": reward_type_desc_db,
                        "rewardType_desc_doc": doc_info["rewardType_desc_doc"],
                    },
                    "rewardId_db": reward_id_db,
                    "reward_value_doc": doc_info.get("reward_value_doc"),
                    "rewardCount_db": reward_count_db,
                    "reason": "奖励数值不一致"
                })

            if doc_info.get("unit_doc") not in (None, "") or unit_db not in (None, ""):
                if str(doc_info.get("unit_doc")) != str(unit_db):
                    differences["unit_mismatch"].append({
                        "common_info": {
                            "rewardPackId": reward_pack_id_db,
                            "rewardPackName_doc": doc_info["rewardPackName_doc"],
                            "rewardType": reward_type_db,
                            "rewardType_name_doc": doc_info["rewardType_name_doc"],
                            "rewardType_desc_db": reward_type_desc_db,
                            "rewardType_desc_doc": doc_info["rewardType_desc_doc"],
                        },
                        "rewardId_db": reward_id_db,
                        "unit_doc": doc_info.get("unit_doc"),
                        "unit_db": unit_db,
                        "reason": "奖励单位不一致"
                    })

        self.logger.info(f"共校验数据库奖励配置: {len(db_config)}条")

        if differences["db_exist_doc_not"]:
            self.logger.info(f"[差异: 数据库存在、文档无] 共{len(differences["db_exist_doc_not"])}条")
            for item in differences["db_exist_doc_not"]:
                db = item["db_info"]
                self.logger.info(
                    f"奖励包: {db["rewardPackName"]} (ID={db["rewardPackId"]}) | 奖励类型: {db["rewardType_desc"]} "
                    f"(Type={db["rewardType"]}) | 数据库rewardId: {db["rewardId"]} | 原因: {item["reason"]}"
                )

        if differences["rewardId_mismatch"]:
            self.logger.info(f"[差异: rewardId不匹配] 共{len(differences["rewardId_mismatch"])}条")
            for item in differences["rewardId_mismatch"]:
                common = item["common_info"]
                self.logger.info(
                    f"奖励包: {common["rewardPackName_doc"]} (ID={common["rewardPackId"]}) | 奖励类型: "
                    f"{common["rewardType_desc_doc"]} (Type={common["rewardType"]}) | 文档rewardId: {item["rewardId_doc"]} "
                    f"| 数据库rewardId: {item["rewardId_db"]}"
                )

        if differences["reward_value_mismatch"]:
            self.logger.info(f"[差异: 奖励数值不匹配] 共{len(differences["reward_value_mismatch"])}条")
            for item in differences["reward_value_mismatch"]:
                common = item["common_info"]
                self.logger.error(
                    f"奖励包: {common["rewardPackName_doc"]} (ID={common["rewardPackId"]}) | 奖励类型: "
                    f"{common["rewardType_desc_doc"]} (Type={common["rewardType"]}) | 奖励rewardId: {item["rewardId_db"]} "
                    f"| 文档数值: {item["reward_value_doc"]} | 数据库数值: {item["rewardCount_db"]} | 原因: {item["reason"]}"
                )

        if differences["unit_mismatch"]:
            self.logger.info(f"[差异: 奖励单位不匹配] 共{len(differences["unit_mismatch"])}条")
            for item in differences["unit_mismatch"]:
                common = item["common_info"]
                self.logger.info(
                    f"奖励包: {common["rewardPackName_doc"]} (ID={common["rewardPackId"]}) | 奖励类型: "
                    f"{common["rewardType_desc_doc"]} (Type={common["rewardType"]}) | 奖励rewardId: {item["rewardId_db"]} "
                    f"| 文档unit: {item["unit_doc"]} | 数据库unit: {item["unit_db"]}"
                )

        if not any(differences.values()):
            self.logger.info("✅ 数据库配置所有奖励均在文档中存在, 且rewardId、数值、unit完全一致!")
        else:
            self.logger.warning(f"❌ 发现 {sum(len(v) for v in differences.values())} 条差异, 请检查文档和数据库配置!")

        return differences

    def get_activity_ranking_data(self, filter_rank_types: Optional[List[str]] = None) -> List[Dict]:
        """
        获取活动榜单数据 - 用户排名及对应奖励
        Args:
            filter_rank_types: 可选, 要获取的榜单类型列表
        Returns:
            List[Dict]: 格式化后的榜单数据
        """
        activity_reward_config = self.get_activity_reward_config_doc(self.activity_config_path)
        normalized_filter_rank_types = self._normalize_filter_rank_types(filter_rank_types, activity_reward_config)
        cache_key = tuple(normalized_filter_rank_types) if normalized_filter_rank_types is not None else None

        if cache_key in self._cache.get("activity_ranking_data", {}):
            self.logger.debug(f"使用缓存的活动榜单数据 (过滤条件: {normalized_filter_rank_types})")
            return self._cache["activity_ranking_data"][cache_key]

        all_ranked_data = []

        for config in activity_reward_config:
            if not isinstance(config, dict):
                continue

            rank_key = self._build_rank_key(config)
            if normalized_filter_rank_types is not None and rank_key not in normalized_filter_rank_types:
                continue

            rank_category = config.get("rank_category", "0")
            activity_type_name = config.get("activityType_name", "")
            rank_coverage = config.get("rank_coverage", 10)
            rank_scope = self._get_rank_scope(activity_type_name)

            if rank_scope == "day":
                query = """select nowTime from `kong_test`.`activity_gift_medal` where id = %s"""
                result = self.db.get_one(query, (self.activity_number,))
                stage = util.format_time(
                    util.get_time_delta(datetime_obj = result.get("nowTime"), days = -1),
                    format_str = "%Y%m%d"
                )
            elif rank_scope == "total":
                stage = "-1"
            else:
                self.logger.warning(f"未知榜单类型: {activity_type_name}, 跳过处理")
                continue

            self.logger.info(f"处理榜单配置: {activity_type_name}, 阶段={stage}, TopN={rank_coverage}")

            try:
                raw_data = self._query_ranking_data(rank_category, stage, rank_coverage)

                if len(raw_data) < rank_coverage:
                    self.logger.warning(f"现有数据不足TopN({rank_coverage}), 当前只有{len(raw_data)}条, 需要补足数据")
                    missing_count = rank_coverage - len(raw_data)
                    inserted_count = self._insert_test_ranking_data(rank_category, stage, missing_count)

                    if inserted_count > 0:
                        self.logger.info(f"成功插入{inserted_count}条测试数据, 重新查询榜单数据")
                        raw_data = self._query_ranking_data(rank_category, stage, rank_coverage)
                    else:
                        self.logger.warning("复制数据失败, 使用现有数据进行处理")

                if raw_data:
                    ranked_data = self._process_ranking_data(raw_data, rank_key, activity_type_name)
                    self.logger.debug(f"成功获取到 {len(ranked_data)} 条榜单数据, 排名范围: 1-{rank_coverage}")
                    all_ranked_data.extend(ranked_data)
                else:
                    self.logger.warning("没有获取到榜单数据, 跳过处理")

            except Exception as e:
                self.logger.error(f"获取活动榜单数据失败: {str(e)}")
                raise

        self.logger.info(f"总共获取到 {len(all_ranked_data)} 条榜单数据")

        # 将结果存入缓存
        if "activity_ranking_data" not in self._cache:
            self._cache["activity_ranking_data"] = {}
        self._cache["activity_ranking_data"][cache_key] = all_ranked_data

        return all_ranked_data

    def get_user_expected_rewards(self, ranking_data: List[Dict], activity_reward_config: List[Dict[str, Any]],
                                  filter_rank_types: Optional[List[str]] = None, exclude_accumulate_types: Optional[
                List[int]] = None) -> Dict:
        """
        获取用户预期奖励，考虑用户角色、性别等因素

        Args:
            ranking_data: 榜单数据
            activity_reward_config: 活动奖励配置
            filter_rank_types: 可选, 要处理的榜单类型列表
            exclude_accumulate_types: 可选, 不需要累加的奖励类型列表

        Returns:
            Dict: 用户预期奖励字典, 结构为:
                  {
                      user_id: {
                          rank_type: {
                              ranking: [reward1, reward2, ...]
                          },
                          aggregate: {
                              0: [accumulated_reward1, accumulated_reward2, ...]
                          }
                      }
                  }
        """
        normalized_filter_rank_types = self._normalize_filter_rank_types(filter_rank_types, activity_reward_config)
        cache_key = f"{hash(str(ranking_data))}_{hash(str(activity_reward_config))}_{hash(str(normalized_filter_rank_types))}"

        # 检查缓存
        if "user_expected_rewards" in self._cache and cache_key in self._cache["user_expected_rewards"]:
            self.logger.debug("使用缓存的用户预期奖励")
            return self._cache["user_expected_rewards"][cache_key]

        # 设置默认需要不累加的奖励类型
        if exclude_accumulate_types is None:
            exclude_accumulate_types = [1, 6]

        # 收集所有需要查询的用户ID
        user_ids = []
        for user_data in ranking_data:
            user_id = user_data.get("user_id")
            rank_type = user_data.get("rank_type")

            # 指定过滤条件, 只处理指定的榜单类型
            if normalized_filter_rank_types is not None and rank_type not in normalized_filter_rank_types:
                continue

            if user_id not in user_ids:
                user_ids.append(user_id)

        # 批量查询用户角色和性别信息
        user_role_map = {}
        user_sex_map = {}
        if user_ids:
            placeholders = ", ".join(["%s"] * len(user_ids))
            user_query = f"""
                SELECT userid, role, sex FROM `kong_test`.`user` 
                WHERE userid IN ({placeholders})
            """
            users = self.db.execute_query(user_query, tuple(user_ids))

            # 构建用户ID到角色和性别的映射
            for user_info in users:
                user_role_map[user_info["userid"]] = user_info["role"]
                user_sex_map[user_info["userid"]] = user_info["sex"]
                self.logger.debug(f"用户[{user_info['userid']}] 角色: {user_info['role']}, 性别: {user_info['sex']}")

        user_expected_rewards = {}
        # 记录同一用户同一奖励类型和ID的累计有效期
        user_reward_aggregate = {}

        for user_data in ranking_data:
            user_id = user_data.get("user_id")
            ranking = user_data.get("ranking")
            rank_type = user_data.get("rank_type")

            # 指定过滤条件, 只处理指定的榜单类型
            if normalized_filter_rank_types is not None and rank_type not in normalized_filter_rank_types:
                continue

            # 获取用户应得奖励
            expected_rewards = self.get_expected_rewards_by_ranking(ranking, rank_type, activity_reward_config)

            # 根据用户角色、性别和榜单类型筛选奖励
            user_role = user_role_map.get(user_id, 0)
            user_sex = user_sex_map.get(user_id, 0)
            self.logger.debug(f"用户[{user_id}] 角色: {user_role}, 性别: {user_sex}")
            self.logger.debug(f"原始奖励列表: {expected_rewards}")

            filtered_rewards = []
            for reward in expected_rewards:
                reward_type = reward.get("rewardType")
                reward_id = reward.get("rewardId")
                valid_days = self._safe_int(reward.get("valid_days", 0)) or 0
                reward_desc = reward.get("reward_desc", "")
                reward_unit = self._get_reward_unit(reward.get("unit"))
                reward_actor = self._safe_int(reward.get("actor", 0)) or 0
                reward_sex = self._safe_int(reward.get("sex", 0)) or 0

                # 头像框奖励区分男女用户
                if reward_type == 2:
                    if reward_sex == 1 and user_sex != 1:
                        self.logger.debug(f"跳过奖励: 头像框奖励性别不匹配")
                        continue
                    elif reward_sex == 2 and user_sex != 2:
                        self.logger.debug(f"跳过奖励: 头像框奖励性别不匹配")
                        continue

                # 贵族和超级会员奖励区分用户角色
                if reward_type in {5, 16}:
                    self.logger.debug(f"检查奖励: 类型={reward_type}, 名称={reward_desc}, 角色要求={reward_actor}, 用户角色={user_role}")
                    if reward_actor == 1 and user_role == 5:
                        self.logger.debug(f"跳过奖励: 普通用户专属奖励, 用户是陪伴师")
                        continue
                    if reward_actor == 2 and user_role != 5:
                        self.logger.debug(f"跳过奖励: 陪伴师专属奖励, 用户不是陪伴师")
                        continue
                    self.logger.debug(f"保留奖励: 类型={reward_type}, 名称={reward_desc}")

                filtered_rewards.append(reward)

            # 处理需要累加的奖励
            for reward in filtered_rewards:
                reward_type = reward.get("rewardType")
                reward_name = RewardTypeMapper.get_reward_type_desc(reward_type)
                reward_id = reward.get("rewardId")
                valid_days = self._safe_int(reward.get("valid_days", 0)) or 0
                reward_desc = reward.get("reward_desc", "")
                reward_unit = self._get_reward_unit(reward.get("unit"))

                should_accumulate = reward_type not in exclude_accumulate_types
                if reward_type == 5:
                    should_accumulate = user_role == 5
                elif reward_type == 16:
                    should_accumulate = user_role == 0

                if should_accumulate:
                    if user_id not in user_reward_aggregate:
                        user_reward_aggregate[user_id] = {}
                    if isinstance(reward_id, dict):
                        reward_id = reward_id.get("id", str(reward_id))
                    reward_key = (reward_type, reward_id)
                    reward_info = user_reward_aggregate[user_id].setdefault(reward_key, {
                        "reward_id": reward_id,
                        "reward_type": reward_type,
                        "reward_name": reward_name,
                        "valid_days": 0,
                        "reward_desc": reward_desc,
                        "unit": reward_unit,
                        "accumulated_days": []
                    })
                    reward_info["accumulated_days"].append(valid_days)
                    reward_info["valid_days"] += valid_days

            # 构建原始奖励结构
            if user_id not in user_expected_rewards:
                user_expected_rewards[user_id] = {}
            if rank_type not in user_expected_rewards[user_id]:
                user_expected_rewards[user_id][rank_type] = {}
            user_expected_rewards[user_id][rank_type][ranking] = filtered_rewards

        # 构建累加后的预期奖励结构
        for user_id in user_role_map.keys():
            if user_id not in user_expected_rewards:
                user_expected_rewards[user_id] = {}

            # 添加需要累加的奖励
            if user_id in user_reward_aggregate:
                for key, reward_info in user_reward_aggregate[user_id].items():
                    reward_type, reward_id = key  # 解包键, 获取 reward_type 和 reward_id
                    if "aggregate" not in user_expected_rewards[user_id]:
                        user_expected_rewards[user_id]["aggregate"] = {}
                    # 使用0作为排名标识
                    accumulated_reward = {
                        "rewardType": reward_type,
                        "rewardId": reward_info["reward_id"],
                        "valid_days": reward_info["valid_days"],
                        "reward_desc": reward_info["reward_desc"],
                        "unit": reward_info.get("unit"),
                        "is_accumulated": True  # 标记为累加后的奖励
                    }
                    user_expected_rewards[user_id]["aggregate"].setdefault(0, []).append(accumulated_reward)
                    # 构建累加表达式
                    accumulated_days = reward_info.get("accumulated_days", [])
                    if len(accumulated_days) > 1:
                        expr = " + ".join(map(str, accumulated_days))
                        self.logger.debug(f"用户[{user_id}] 奖励类型[ {reward_info["reward_desc"]} ]  已累加, 累计有效期[ {expr} = {reward_info["valid_days"]} ]天")
                    else:
                        self.logger.debug(f"用户[{user_id}] 奖励类型[ {reward_info["reward_desc"]} ] 有效期[ {reward_info["valid_days"]} ]天")
                self.logger.debug("-" * 50)

        # 存入缓存
        if "user_expected_rewards" not in self._cache:
            self._cache["user_expected_rewards"] = {}
        self._cache["user_expected_rewards"][cache_key] = user_expected_rewards

        # 输出用户这一次应该获得的所有奖励
        for user_id, rewards_by_type in user_expected_rewards.items():
            self.logger.info(f"用户[{user_id}] 本次应获得的所有奖励:")
            # 输出各榜单类型的奖励
            for rank_type, rewards_by_ranking in rewards_by_type.items():
                if rank_type == "aggregate":
                    continue  # 累加奖励单独处理
                for ranking, rewards in rewards_by_ranking.items():
                    if rewards:
                        self.logger.info(f"  榜单类型[{rank_type}] 排名[{ranking}] 奖励: {rewards}")
            # 输出累加后的奖励
            aggregate_rewards = rewards_by_type.get("aggregate", {}).get(0, [])
            if aggregate_rewards:
                self.logger.info(f"  累加奖励: {aggregate_rewards}")
            self.logger.info("-" * 50)

        return user_expected_rewards

    def _query_ranking_data(self, rank_category: str, stage: str, rank_coverage: int) -> List[Dict]:
        """
        查询榜单数据

        Args:
            rank_category: 榜单分类
            stage: 活动阶段(赛段/日期), 默认前一天
            rank_coverage: 要获取的榜单Top N用户, 默认10

        Returns:
            List[Dict]: 格式化后的榜单数据
        """
        query = """
            SELECT number, userId, intimateId, category, stage, year, month, day, value
            FROM `kong_test`.`activity_rank`
            WHERE number = %s AND category = %s AND stage = %s
            ORDER BY value DESC LIMIT %s
        """
        return self.db.execute_query(query, (self.activity_number, rank_category, stage, rank_coverage))

    def _insert_test_ranking_data(self, ranking_category: str, stage: str, count: int) -> int:
        """
        插入测试榜单数据

        Args:
            ranking_category: 榜单分类
            stage: 活动阶段(赛段/日期), 默认前一天, 20260119表示日榜
            count: 要插入的测试数据数量

        Returns:
            int: 成功插入的测试数据数量
        """
        # 从满足条件的榜单数据中取一条数据作为模板
        inserted_count = 0

        existing_users_query = """
                    SELECT * FROM `kong_test`.`activity_rank` 
                    WHERE number = %s and category = %s order by id desc
                """
        existing_users = self.db.execute_query(existing_users_query, (self.activity_number, ranking_category))
        template_data = existing_users[0] if existing_users else None
        if not template_data:
            self.logger.warning("未找到符合条件的模板数据, 无法进行复制")
            return 0
        # 解析stage参数获取年、月、日
        if len(stage) == 8:
            year = int(stage[:4])
            month = int(stage[4:6])
            day = int(stage[6:8])
        else:
            year = -1
            month = -1
            day = -1
        self.logger.info(f"找到模板数据, 开始复制生成 {count} 条测试数据")

        # 构建已存在的用户对集合
        existing_user_pairs = set()
        existing_user_ids = set()
        for user in existing_users:
            existing_user_pairs.add((user["userId"], user["intimateId"]))
            existing_user_ids.add(user["userId"])
            existing_user_ids.add(user["intimateId"])

        # 同类型榜单的日榜/总榜
        # 检查同一类型的其他榜单是否有数据
        other_stage_query = """
                        SELECT * FROM `kong_test`.`activity_rank` 
                        WHERE number = %s and category = %s and day = %s
                        ORDER BY id DESC LIMIT %s
                   """
        other_stage_data = self.db.execute_query(other_stage_query, (self.activity_number, ranking_category,
                                                                     -1 if len(stage) == 8 else 0, count))

        # 同一类型的其他榜单有数据
        if other_stage_data:
            # 先复制所有可用的其他榜单数据
            copy_count = min(len(other_stage_data), count)
            self.logger.info(f"发现同一类型的其他榜单有{len(other_stage_data)}条数据, 复制其中{copy_count}条")

            for i in range(copy_count):
                insert_query = """
                                INSERT INTO `kong_test`.`activity_rank` 
                                (userId, intimateId, number, category, stage, year, month, day, value, 
                                 value1, value2, value3, value4, value5, value6, value7, valueTime, 
                                 source, display, completed, created, updated)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                        %s, %s, %s, %s, %s, %s, %s, %s, 
                                        %s, %s, %s, %s, %s)
                            """
                try:
                    self.db.execute_update(
                        insert_query,
                        (
                            other_stage_data[i]["userId"], other_stage_data[i]["intimateId"],
                            self.activity_number, ranking_category, stage, year, month, day,
                            template_data["value"] * random.uniform(0.8, 1.2), template_data["value1"],
                            template_data["value2"],
                            template_data["value3"], template_data["value4"], template_data["value5"],
                            template_data["value6"], template_data["value7"], template_data["valueTime"],
                            template_data["source"], template_data["display"], template_data["completed"],
                            template_data["created"], template_data["updated"]

                        )
                    )
                    inserted_count += 1
                    existing_user_pairs.add((other_stage_data[i]["userId"], other_stage_data[i]["intimateId"]))
                    existing_user_ids.add(other_stage_data[i]["userId"])
                    existing_user_ids.add(other_stage_data[i]["intimateId"])
                    self.logger.info(f"复制榜单数据 {other_stage_data[i]["userId"]} - {other_stage_data[i]["intimateId"]}")
                except Exception as e:
                    self.logger.error(f"复制榜单数据 {other_stage_data[i]["userId"]} - {other_stage_data[i]["intimateId"]} 失败: {str(e)}")

            self.logger.info(f"已复制插入 {inserted_count} 条测试数据")

            # 满足榜单数量要求, 直接返回
            if inserted_count >= count:
                return inserted_count
            else:
                # 还需要生成的随机数据数量
                remaining_count = count - inserted_count
        else:
            # 没有其他榜单数据, 全部使用随机数据生成
            remaining_count = count

        # 生成剩余的随机数据
        if remaining_count > 0:
            self.logger.info(f"使用随机数据生成剩余的 {remaining_count} 条测试数据")

            # 随机获取不在排行榜中的用户ID
            if existing_user_ids:
                placeholders = ", ".join(["%s"] * len(existing_user_ids))
                random_users_query = f"""
                                    SELECT userid FROM `kong_test`.`user`
                                    WHERE status = 0 and role = 5 and userid NOT IN ({placeholders})
                                    ORDER BY lastLoginDate desc LIMIT %s
                                """
                random_users = self.db.execute_query(random_users_query, tuple(existing_user_ids) + (
                    remaining_count * 2,))
            else:
                random_users_query = """
                                    SELECT userid FROM `kong_test`.`user`
                                    WHERE status = 0 and role = 5
                                    ORDER BY lastLoginDate desc LIMIT %s
                                """
                random_users = self.db.execute_query(random_users_query, (remaining_count * 2,))
            for i in range(remaining_count):
                if template_data["userId"] == template_data["intimateId"]:  # 单人榜
                    # 生成唯一的单人记录
                    max_attempts = 3  # 最多尝试3次
                    for attempt in range(max_attempts):
                        user_id = random_users[i + attempt]["userid"]
                        intimate_id = user_id
                        user_pair = (user_id, intimate_id)

                        # 检查用户对是否已存在
                        if user_pair not in existing_user_pairs:
                            existing_user_pairs.add(user_pair)
                            break
                    else:
                        self.logger.warning(f"无法为第 {i + 1} 条记录生成唯一的单人记录, 已跳过")
                        continue
                else:  # 双人榜
                    # 生成唯一的用户对
                    max_attempts = 3  # 最多尝试3次
                    for attempt in range(max_attempts):
                        # 尝试不同的随机用户组合
                        user_id = random_users[i + attempt]["userid"]
                        intimate_id = random_users[remaining_count + i + attempt]["userid"]

                        # 跳过自己和自己的组合
                        if user_id == intimate_id:
                            continue

                        # 确保userId < intimateId
                        if user_id > intimate_id:
                            user_id, intimate_id = intimate_id, user_id

                        user_pair = (user_id, intimate_id)
                        # 检查用户对是否已存在
                        if user_pair not in existing_user_pairs:
                            existing_user_pairs.add(user_pair)
                            break
                    else:
                        self.logger.warning(f"无法为第 {i + 1} 条记录生成唯一的用户对, 已跳过")
                        continue

                # 构建复制插入SQL, 只修改关键字段
                insert_query = """
                            INSERT INTO `kong_test`.`activity_rank` 
                            (userId, intimateId, number, category, stage, year, month, day, value, 
                             value1, value2, value3, value4, value5, value6, value7, valueTime, 
                             source, display, completed, created, updated)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                    %s, %s, %s, %s, %s, %s, %s, %s, 
                                    %s, %s, %s, %s, %s)
                        """
                try:
                    self.db.execute_update(
                        insert_query,
                        (
                            user_id, intimate_id,
                            self.activity_number, ranking_category, stage, year, month, day,
                            template_data["value"], template_data["value1"], template_data["value2"],
                            template_data["value3"], template_data["value4"], template_data["value5"],
                            template_data["value6"], template_data["value7"], template_data["valueTime"],
                            template_data["source"], template_data["display"], template_data["completed"],
                            template_data["created"], template_data["updated"]
                        )
                    )
                    inserted_count += 1
                    self.logger.info(f"生成随机榜单数据 {user_id} - {intimate_id}")
                except Exception as e:
                    self.logger.error(f"生成随机榜单数据 {user_id} - {intimate_id} 失败: {str(e)}")

            self.logger.info(f"共插入 {inserted_count} 条测试数据")
        return inserted_count

    def _process_ranking_data(self, raw_data: List[Dict], rank_type: str, activity_type_name: str) -> List[Dict]:
        """
        处理榜单数据(单人和双人分别处理)

        Args:
            raw_data: 原始榜单数据列表
            rank_type: 榜单唯一键
            activity_type_name: 榜单名称

        Returns:
            List[Dict]: 处理后的榜单数据列表
        """
        ranked_data = []

        for index, item in enumerate(raw_data, 1):
            if item.get("userId") == item.get("intimateId"):
                ranked_item = {
                    "number": item.get("number"),
                    "category": item.get("category"),
                    "rank_type": rank_type,
                    "activityType_name": activity_type_name,
                    "rank_day": item.get("day"),
                    "stage": item.get("stage"),
                    "user_id": item.get("userId"),
                    "value": item.get("value"),
                    "ranking": index,
                }
                ranked_data.append(ranked_item)
            else:
                ranked_item_user1 = {
                    "number": item.get("number"),
                    "category": item.get("category"),
                    "rank_type": rank_type,
                    "activityType_name": activity_type_name,
                    "rank_day": item.get("day"),
                    "stage": item.get("stage"),
                    "user_id": item.get("userId"),
                    "value": item.get("value"),
                    "ranking": index,
                }
                ranked_item_user2 = {
                    "number": item.get("number"),
                    "category": item.get("category"),
                    "rank_type": rank_type,
                    "activityType_name": activity_type_name,
                    "rank_day": item.get("day"),
                    "stage": item.get("stage"),
                    "user_id": item.get("intimateId"),
                    "value": item.get("value"),
                    "ranking": index,
                }
                ranked_data.extend([ranked_item_user1, ranked_item_user2])
        self.logger.info(f"榜单数据处理完成: {ranked_data}")
        return ranked_data

    def get_expected_rewards_by_ranking(self, ranking: int, activity_type: Any,
                                        activity_reward_config: List[Dict[str, Any]]) -> List[Dict]:
        """
        根据排名获取应得的奖励配置

        Args:
            ranking: 排名
            activity_type: 榜单类型
            activity_reward_config: 活动奖励配置

        Returns:
            List[Dict]: 应得的奖励列表
        """
        try:
            ranking = int(ranking)
        except (TypeError, ValueError) as e:
            self.logger.error(f"无效的排名参数: ranking={ranking}, activity_type={activity_type}, 错误: {str(e)}")
            return []

        normalized_activity_type = str(activity_type)
        cache_key = (ranking, normalized_activity_type)
        if cache_key in self._cache["expected_rewards"]:
            return self._cache["expected_rewards"][cache_key]

        expected_rewards = []
        self.logger.debug(f"查找排名 {ranking} 在榜单类型 {normalized_activity_type} 的奖励配置")

        config = self._find_config_by_rank_type(normalized_activity_type, activity_reward_config)
        if config:
            activity_type_name = config.get("activityType_name", "未知榜单")
            self.logger.debug(f"找到匹配的榜单类型配置: {activity_type_name}")

            rewards = self._get_rewards_for_rank(config, ranking)
            if rewards:
                expected_rewards.extend(rewards)
                self.logger.debug(f"找到排名 {ranking} 的奖励配置, 共 {len(rewards)} 个奖励")
            else:
                self.logger.warning(f"在榜单类型 {normalized_activity_type} 中未找到排名 {ranking} 的奖励配置")
                available_ranks = sorted(self._build_rank_pack_mapping(config).keys())
                if not available_ranks:
                    available_ranks = sorted(
                        self._safe_int(reward_detail.get("rank"))
                        for reward_detail in config.get("reward_details", [])
                        if isinstance(self._safe_int(reward_detail.get("rank")), int)
                    )
                self.logger.warning(f"该榜单可用的排名: {available_ranks}")
        else:
            activity_type_name = f"未知({normalized_activity_type})"
            self.logger.warning(f"未找到榜单类型 {normalized_activity_type} 的配置")
            available_activity_types = list(self._build_activity_config_map(activity_reward_config).keys())
            self.logger.warning(f"可用的榜单类型: {available_activity_types}")

        self._cache["expected_rewards"][cache_key] = expected_rewards
        self.logger.info(f"获取{activity_type_name}排名 {ranking} 应下发的奖励: {expected_rewards}")
        return expected_rewards

    def clear_user_rewards(self, ranking_data: List[Dict], activity_reward_config: List[Dict[str, Any]],
                           filter_rank_types: Optional[List[str]] = None) -> None:
        """
        清除榜单用户奖励

        Args:
            ranking_data: 榜单数据
            activity_reward_config: 活动奖励配置
            filter_rank_types: 可选, 要清除的榜单类型列表
        """
        normalized_filter_rank_types = self._normalize_filter_rank_types(filter_rank_types, activity_reward_config)

        # 获取用户预期奖励(使用缓存)
        user_expected_rewards = self.get_user_expected_rewards(ranking_data, activity_reward_config, filter_rank_types)

        # 收集需要清除的各种奖励
        dress_to_clear = []
        medal_to_clear = []
        title_to_clear = []
        noble_to_clear = []
        vip_to_clear = []
        super_vip_to_clear = []
        nice_number_to_clear = []

        # 遍历用户数据, 收集需要清除的奖励
        for user_data in ranking_data:
            user_id = user_data.get("user_id")
            ranking = user_data.get("ranking")
            activity_type = user_data.get("rank_type")

            # 指定过滤条件, 只处理指定的榜单类型
            if normalized_filter_rank_types is not None and activity_type not in normalized_filter_rank_types:
                continue

            # 从缓存中获取用户应得奖励
            expected_rewards = user_expected_rewards.get(user_id, {}).get(activity_type, {}).get(ranking, [])
            # 获取累加奖励
            aggregate_rewards = user_expected_rewards.get(user_id, {}).get("aggregate", {}).get(0, [])
            all_rewards = expected_rewards + aggregate_rewards

            if not all_rewards:
                self.logger.warning(f"用户 {user_id} 排名 {ranking} 未找到对应的奖励配置")
                continue

            self.logger.info(f"准备清除用户 {user_id} (榜单{activity_type} 排名{ranking}) 的已有奖励")
            # 根据应得奖励类型统计需要清除的记录
            for reward in all_rewards:
                reward_type = reward.get("rewardType")
                reward_id = reward.get("rewardId")

                if reward_type in {2, 3, 9, 10, 12, 14}:
                    # 装扮类奖励
                    dress_to_clear.append((user_id, reward_id))
                elif reward_type == 1:
                    # 勋章
                    medal_to_clear.append((user_id, reward_id))
                elif reward_type == 15:
                    # 荣誉称号
                    title_to_clear.append((user_id, reward_id))
                elif reward_type in {16, 17}:
                    # 贵族 - 16为公爵, 17为子爵
                    nobleman_id = 7 if reward_type == 16 else 4
                    noble_to_clear.append((user_id, nobleman_id))
                elif reward_type == 4:
                    # VIP
                    vip_to_clear.append((user_id,))
                elif reward_type == 5:
                    # 超级VIP
                    super_vip_to_clear.append((user_id,))
                elif reward_type == 6:
                    # 靓号
                    nice_number_to_clear.append((user_id, reward_id))
                else:
                    self.logger.warning(f"未知的奖励类型: {reward_type}, 无法清除")

        # 批量执行清除操作
        if dress_to_clear:
            query = "DELETE FROM `kong_test`.`user_dress` WHERE userId = %s and dressId = %s"
            affected_rows = self.db.execute_many(query, dress_to_clear)
            self.logger.info(f"批量清除装扮奖励, 共影响 {affected_rows} 条记录")

        if medal_to_clear:
            query = "DELETE FROM `kong_test`.`user_medal` WHERE userId = %s and medalId = %s"
            affected_rows = self.db.execute_many(query, medal_to_clear)
            self.logger.info(f"批量清除勋章奖励, 共影响 {affected_rows} 条记录")

        if title_to_clear:
            query = "DELETE FROM `kong_test`.`user_honor_title` WHERE userId = %s and honorTitleId = %s"
            affected_rows = self.db.execute_many(query, title_to_clear)
            self.logger.info(f"批量清除荣誉称号奖励, 共影响 {affected_rows} 条记录")

        if noble_to_clear:
            query = "UPDATE `kong_test`.`user_nobleman_level` SET isNobleman = 0, noblemanExpire = UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL 1 DAY)) WHERE userId = %s and noblemanId = %s"
            affected_rows = self.db.execute_many(query, noble_to_clear)
            self.logger.info(f"批量清除贵族奖励, 共影响 {affected_rows} 条记录")

        if vip_to_clear:
            query = "UPDATE `kong_test`.`user` SET isVip = 0, vipExpire = UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL 1 DAY)) * 1000 WHERE userId = %s"
            affected_rows = self.db.execute_many(query, vip_to_clear)
            self.logger.info(f"批量清除VIP奖励, 共影响 {affected_rows} 条记录")

        if super_vip_to_clear:
            query = "UPDATE `kong_test`.`user` SET isSuperVip = 0, superVipExpire = UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL 1 DAY)) * 1000 WHERE userId = %s"
            affected_rows = self.db.execute_many(query, super_vip_to_clear)
            self.logger.info(f"批量清除超级VIP奖励, 共影响 {affected_rows} 条记录")

        if nice_number_to_clear:
            query = "DELETE FROM `kong_test`.`user_gift` WHERE userId = %s and giftId = %s"
            affected_rows = self.db.execute_many(query, nice_number_to_clear)
            self.logger.info(f"批量清除靓号奖励, 共影响 {affected_rows} 条记录")

    def get_scheduled_tasks(self) -> List[Dict]:
        """
        获取活动定时任务配置

        Returns:
            List[Dict]: 定时任务配置列表
        """
        activity_name = self.db.get_one("select activityName from `kong_test`.`activity_gift_medal` where id = %s", (
            self.activity_number,
        ))

        # 根据活动名称获取定时任务ID, 并对ID进行处理
        scheduled_tasks = self.db.execute_query("select job_desc as taskName, REPLACE(executor_handler, '#', '@') AS taskId from `xxl_job`.`xxl_job_info` where SUBSTRING_INDEX(SUBSTRING_INDEX(job_desc, '【', -1), '】', 1) = %s", (
            activity_name["activityName"],
        ))
        # scheduled_tasks = [{'taskName': '圣诞日榜', 'taskId': 'A@ACTIVITY_DAY_END'},
        #                    {'taskName': '圣诞总榜', 'taskId': 'A@ACTIVITY_END'}, ]
        if not scheduled_tasks:
            self.logger.warning(f"活动: {activity_name['activityName']} 未配置定时任务")
            return []
        self.logger.info(f"活动: {activity_name['activityName']} 已配置 {len(scheduled_tasks)} 个定时任务")
        return scheduled_tasks

    def execute_scheduled_task(self, task: Dict[str, Any]) -> bool:
        """
        执行定时任务下发榜单奖励

        Returns:
            bool: 是否执行成功
        """
        params = {
            "expression": task["taskId"]
        }
        response = self.api_client.get(url = "/api/xxl-job/execute", params = params)
        try:
            resp = response.json()
            if resp.get("code") == 200:
                self.logger.info(f"定时任务 {task["taskName"]} 执行成功")
            else:
                self.logger.error(f"定时任务 {task["taskName"]} 执行失败: {resp.get("err")}")
                return False
        except Exception as e:
            self.logger.error(f"定时任务 {task["taskName"]} 执行异常: {str(e)}")
            return False

        return True

    @wait_with_jitter(base_delay = 2, jitter_factor = 0.3)
    def validate_reward_distribution(self, ranking_data: List[Dict], activity_reward_config: List[Dict[str, Any]],
                                     filter_rank_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        验证奖励下发情况

        Args:
            ranking_data: 榜单数据
            activity_reward_config: 活动奖励配置
            filter_rank_types: 可选, 要验证的榜单类型列表

        Returns:
            Dict[str, Any]: 验证结果
        """
        validation_result = {
            "total_users": [],
            "users_with_correct_rewards": [],
            "users_with_incorrect_rewards": [],
            "users_without_rewards": [],
            "reward_validation_details": []
        }
        normalized_filter_rank_types = self._normalize_filter_rank_types(filter_rank_types, activity_reward_config)

        # 按用户ID分组处理, 过滤符合filter_rank_types的榜单数据
        user_ranking_dict = {}
        for data in ranking_data:
            rank_type = data.get("rank_type")
            # 检查是否需要过滤榜单类型
            if normalized_filter_rank_types is not None and rank_type not in normalized_filter_rank_types:
                continue

            user_id = data.get("user_id")
            if user_id not in user_ranking_dict:
                user_ranking_dict[user_id] = []
            user_ranking_dict[user_id].append(data)

        validation_result["total_users"] = list(user_ranking_dict.keys())

        # 如果没有用户数据, 直接返回
        if not user_ranking_dict:
            return validation_result

        # 获取所有用户预期奖励
        user_expected_rewards = self.get_user_expected_rewards(ranking_data, activity_reward_config)

        # 收集所有需要验证的奖励
        all_user_ids = list(user_ranking_dict.keys())

        # 批量查询所有需要验证的数据
        dress_query_results = self._batch_query_dress_rewards(all_user_ids)
        medal_query_results = self._batch_query_medal_rewards(all_user_ids)
        title_query_results = self._batch_query_title_rewards(all_user_ids)
        noble_query_results = self._batch_query_noble_rewards(all_user_ids)
        vip_query_results = self._batch_query_vip_rewards(all_user_ids)
        nice_number_query_results = self._batch_query_nice_number_rewards(all_user_ids)

        # 遍历每个用户进行验证
        for user_id, user_data_list in user_ranking_dict.items():
            user_rankings = []
            for user_data in user_data_list:
                ranking = user_data.get("ranking")
                rank_type = user_data.get("rank_type")
                rank_type_name = self._get_activity_type_name_by_rank_type(rank_type, activity_reward_config)
                user_rankings.append({
                    "rank": ranking,
                    "rank_type": rank_type,
                    "rank_type_name": rank_type_name
                })

            user_validation = {
                "user_id": user_id,
                "rankings": user_rankings,  # 存储用户的所有排名信息
                "actual_rewards": [],
                "validation_results": [],
                "all_correct": True,
                "status": ""
            }

            # 检查用户是否在所有符合条件的榜单中都没有奖励配置
            has_any_reward = False

            # 收集需要验证的奖励
            rewards_to_validate = {}

            # 检查是否有累加奖励
            aggregate_rewards = user_expected_rewards.get(user_id, {}).get("aggregate", {}).get(0, [])
            if aggregate_rewards:
                has_any_reward = True
                for reward in aggregate_rewards:
                    reward_type = reward.get("rewardType")
                    reward_id = reward.get("rewardId")
                    # 使用 (reward_type, reward_id) 作为唯一键
                    key = (reward_type, reward_id)
                    if key not in rewards_to_validate:
                        rewards_to_validate[key] = reward

            # 遍历用户的所有符合条件的榜单数据
            for user_data in user_data_list:
                ranking = user_data.get("ranking")
                activity_type = user_data.get("rank_type")

                # 获取用户应得奖励
                expected_rewards = user_expected_rewards.get(user_id, {}).get(activity_type, {}).get(ranking, [])

                if expected_rewards:
                    has_any_reward = True
                    for reward in expected_rewards:
                        reward_type = reward.get("rewardType")
                        reward_id = reward.get("rewardId")
                        # 使用 (reward_type, reward_id) 作为唯一键
                        key = (reward_type, reward_id)
                        if key not in rewards_to_validate:
                            rewards_to_validate[key] = reward

            # 对去重后的奖励进行验证
            for key, reward in rewards_to_validate.items():
                reward_type = reward.get("rewardType")
                reward_id = reward.get("rewardId")
                valid_days = reward.get("valid_days")
                reward_desc = reward.get("reward_desc")
                unit = reward.get("unit")

                # 使用批量查询结果进行验证
                is_valid, validation_msg = self._batch_validate_single_reward(
                    user_id, reward_type, reward_id, valid_days, reward_desc, unit,
                    dress_query_results, medal_query_results, title_query_results,
                    noble_query_results, vip_query_results, nice_number_query_results
                )

                user_validation["actual_rewards"].append({
                    "reward_type": reward_type,
                    "reward_id": reward_id,
                    "valid_days": valid_days,
                    "is_valid": is_valid
                })

                user_validation["validation_results"].append({
                    "reward_type": reward_type,
                    "reward_id": reward_id,
                    "is_valid": is_valid,
                    "message": validation_msg
                })

                if not is_valid:
                    user_validation["all_correct"] = False

            # 统计验证结果
            if not has_any_reward:
                validation_result["users_without_rewards"].append(user_id)
            elif user_validation["all_correct"]:
                validation_result["users_with_correct_rewards"].append(user_id)
                user_validation["status"] = "correct"
            else:
                validation_result["users_with_incorrect_rewards"].append(user_id)
                user_validation["status"] = "incorrect"

                validation_result["reward_validation_details"].append(user_validation)

        # 输出验证摘要
        self.logger.info("=== 奖励下发验证结果 ===")
        self.logger.info(f"总用户数: {len(validation_result["total_users"])}" + (
            f" {validation_result["total_users"]}" if len(validation_result["total_users"]) > 0 else ""))
        if len(validation_result["users_with_correct_rewards"]) > 0:
            self.logger.info(f"✅ 奖励下发正确的用户数: {len(validation_result["users_with_correct_rewards"])}" + (
                f" {validation_result["users_with_correct_rewards"]}"))
        if len(validation_result["users_with_incorrect_rewards"]) > 0:
            self.logger.error(f"❌ 奖励下发错误的用户数: {len(validation_result["users_with_incorrect_rewards"])}" + (
                f" {validation_result["users_with_incorrect_rewards"]}"))
        if len(validation_result["users_without_rewards"]) > 0:
            self.logger.error(f"⚠️ 无奖励配置的用户数: {len(validation_result["users_without_rewards"])}" + (
                f" {validation_result["users_without_rewards"]}"))

        # 输出详细的错误奖励信息
        if len(validation_result["users_with_incorrect_rewards"]) > 0:
            self.logger.error("❌ 详细错误奖励信息:")
            for user_validation in validation_result["reward_validation_details"]:
                user_id = user_validation["user_id"]
                # 格式化排名信息
                rankings_info = []
                for rank_info in user_validation["rankings"]:
                    rankings_info.append(f"{rank_info["rank_type_name"]}第{rank_info["rank"]}名")
                rankings_str = ", ".join(rankings_info)

                self.logger.error(f"  用户ID: {user_id} ({rankings_str})")
                for reward_validation in user_validation["validation_results"]:
                    if not reward_validation["is_valid"]:
                        reward_type = reward_validation["reward_type"]
                        reward_id = reward_validation["reward_id"]
                        error_msg = reward_validation["message"]
                        self.logger.error(f"    - 奖励类型: {self.reward_mapper.get_reward_type_desc(reward_type)}, 奖励ID: {reward_id}, 错误原因: {error_msg}")

        return validation_result

    def _batch_query_dress_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询装扮奖励
        """
        if not user_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(user_ids))
        query = f"""
            SELECT userId, dressId, category, 
                   timestampdiff(hour, FROM_UNIXTIME(valid/1000), FROM_UNIXTIME(expire/1000)) as validHour,
                   CEIL(timestampdiff(hour, FROM_UNIXTIME(valid/1000), FROM_UNIXTIME(expire/1000)) / 24) as validDay 
            FROM `kong_test`.`user_dress` 
            WHERE userId IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询
        result_dict = {}
        for row in results:
            user_id = row["userId"]
            dress_id = row["dressId"]
            category = row["category"]
            valid_hour = row["validHour"]
            valid_day = row["validDay"]

            if user_id not in result_dict:
                result_dict[user_id] = {}
            if dress_id not in result_dict[user_id]:
                result_dict[user_id][dress_id] = {}

            # 如果相同装扮已存在, 累计有效期; 否则直接设置
            if category in result_dict[user_id][dress_id]:
                result_dict[user_id][dress_id][category] = {
                    "hour": result_dict[user_id][dress_id][category]["hour"] + valid_hour,
                    "day": result_dict[user_id][dress_id][category]["day"] + valid_day}
            else:
                result_dict[user_id][dress_id][category] = {"hour": valid_hour, "day": valid_day}

        return result_dict

    def _batch_query_medal_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询勋章奖励
        """
        if not user_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(user_ids))
        query = f"""SELECT userId, medalId FROM `kong_test`.`user_medal` WHERE userId IN ({placeholders})"""
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询: {user_id: {medal_id: True}}
        result_dict = {}
        for row in results:
            user_id = row["userId"]
            medal_id = row["medalId"]

            if user_id not in result_dict:
                result_dict[user_id] = {}
            result_dict[user_id][medal_id] = True

        return result_dict

    def _batch_query_title_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询荣誉称号奖励
        """
        if not user_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(user_ids))
        query = f"""
            SELECT userId, honorTitleId, 
                   timestampdiff(hour, valid, expire) as validHour,
                   CEIL(timestampdiff(hour, valid, expire) / 24) as validDay
            FROM `kong_test`.`user_honor_title` 
            WHERE userId IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询: {user_id: {title_id: {"hour": valid_hour, "day": valid_day}}}
        result_dict = {}
        for row in results:
            user_id = row["userId"]
            title_id = row["honorTitleId"]
            valid_hour = row["validHour"]
            valid_day = row["validDay"]

            if user_id not in result_dict:
                result_dict[user_id] = {}
            result_dict[user_id][title_id] = {"hour": valid_hour, "day": valid_day}

        return result_dict

    def _batch_query_noble_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询贵族奖励
        """
        if not user_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(user_ids))
        query = f"""
            SELECT userId, noblemanId, 
                   COALESCE(timestampdiff(hour, FROM_UNIXTIME(noblemanValid), FROM_UNIXTIME(noblemanExpire)), 0) as validHour,
                   COALESCE(CEIL(timestampdiff(hour, FROM_UNIXTIME(noblemanValid), FROM_UNIXTIME(noblemanExpire)) / 24), 0) as validDay 
            FROM `kong_test`.`user_nobleman_level` 
            WHERE userId IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询: {user_id: {nobleman_id: {"hour": valid_hour, "day": valid_day}}}
        result_dict = {}
        for row in results:
            user_id = row["userId"]
            nobleman_id = row["noblemanId"]
            valid_hour = row["validHour"]
            valid_day = row["validDay"]

            if user_id not in result_dict:
                result_dict[user_id] = {}
            result_dict[user_id][nobleman_id] = {"hour": valid_hour, "day": valid_day}

        return result_dict

    def _batch_query_vip_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询会员奖励
        """
        if not user_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(user_ids))
        query = f"""
            SELECT userId, isVip, isSuperVip, 
                   timestampdiff(hour, FROM_UNIXTIME(vipValid/1000), FROM_UNIXTIME(vipExpire/1000)) as vipValidHour,
                   CEIL(timestampdiff(hour, FROM_UNIXTIME(vipValid/1000), FROM_UNIXTIME(vipExpire/1000)) / 24) as vipValidDay,
                   timestampdiff(hour, FROM_UNIXTIME(superVipValid/1000), FROM_UNIXTIME(superVipExpire/1000)) as superVipValidHour,
                   CEIL(timestampdiff(hour, FROM_UNIXTIME(superVipValid/1000), FROM_UNIXTIME(superVipExpire/1000)) / 24) as superVipValidDay
            FROM `kong_test`.`user` 
            WHERE userId IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询: {user_id: {'Vip': {'valid': bool, 'valid_hour': int, 'valid_day': int}, 'SuperVip': {'valid': bool, 'valid_hour': int, 'valid_day': int}}}
        result_dict = {}
        for row in results:
            user_id = row["userId"]
            result_dict[user_id] = {
                "Vip": {
                    "valid": bool(row["isVip"]),
                    "valid_hour": row["vipValidHour"],
                    "valid_day": row["vipValidDay"]
                },
                "SuperVip": {
                    "valid": bool(row["isSuperVip"]),
                    "valid_hour": row["superVipValidHour"],
                    "valid_day": row["superVipValidDay"]
                }
            }

        return result_dict

    def _batch_query_nice_number_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询靓号奖励
        """
        if not user_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(user_ids))
        query = f"""
            SELECT userId, giftId 
            FROM `kong_test`.`user_gift` 
            WHERE userId IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询: {user_id: {gift_id: True}}
        result_dict = {}
        for row in results:
            user_id = row["userId"]
            gift_id = row["giftId"]

            if user_id not in result_dict:
                result_dict[user_id] = {}
            result_dict[user_id][gift_id] = True

        return result_dict

    @staticmethod
    def _batch_validate_single_reward(user_id: int, reward_type: int, reward_id: int,
                                      valid_days: int, reward_desc: str, unit: Any, dress_results: Dict,
                                      medal_results: Dict, title_results: Dict, noble_results: Dict,
                                      vip_results: Dict, nice_number_results: Dict) -> tuple[bool, str]:
        """
        使用批量查询结果验证单个奖励
        """
        try:
            # 勋章奖励
            if reward_type == 1:
                user_medals = medal_results.get(user_id, {})
                if reward_id not in user_medals:
                    return False, f"勋章 {reward_id} 未下发"
                return True, "勋章验证通过"

            # 装扮奖励(头像框、座驾等)
            elif reward_type in {2, 3, 9, 10, 12, 14}:
                # 确定装扮类型
                dress_type_map = {
                    2: 2,  # 头像框
                    3: 1,  # 座驾
                    9: 4,  # 房间聊天气泡
                    10: 5,  # 主页特效
                    12: 3,  # 私聊气泡
                    14: 6  # 进场特效
                }
                dress_type = dress_type_map.get(reward_type)

                user_dresses = dress_results.get(user_id, {})
                if reward_id not in user_dresses or dress_type not in user_dresses[reward_id]:
                    return False, f"{reward_desc}装扮 {reward_id} 未下发或已过期"

                # 验证有效期
                if RewardPackVerification._is_duration_unit(unit) and valid_days > 0:
                    actual_expire = user_dresses[reward_id][dress_type]["day"] if unit == "天" else \
                    user_dresses[reward_id][dress_type]["hour"]
                    if abs(actual_expire - valid_days) > 0:
                        return False, f"{reward_desc}装扮有效期不匹配, 实际有效期: {actual_expire} != {valid_days}"

                return True, f"{reward_desc}装扮验证通过"

            # 荣誉称号
            elif reward_type == 15:
                user_titles = title_results.get(user_id, {})
                if reward_id not in user_titles:
                    return False, f"荣誉称号 {reward_id} 未下发或已过期"

                # 验证有效期
                if RewardPackVerification._is_duration_unit(unit) and valid_days > 0:
                    title_info = user_titles[reward_id]
                    actual_expire = title_info["day"] if unit == "天" else title_info["hour"]
                    if abs(actual_expire - valid_days) > 0:
                        return False, f"荣誉称号有效期不匹配, 实际有效期: {actual_expire} != {valid_days}"

                return True, "荣誉称号验证通过"

            # 贵族奖励
            elif reward_type in {16, 17}:
                nobleman_id = 7 if reward_type == 16 else 4
                noble_type = "公爵" if nobleman_id == 7 else "子爵"

                user_nobles = noble_results.get(user_id, {})
                if nobleman_id not in user_nobles:
                    return False, f"{noble_type}贵族未下发或已过期"

                # 验证有效期
                if RewardPackVerification._is_duration_unit(unit) and valid_days > 0:
                    actual_expire = user_nobles[nobleman_id]["day"] if unit == "天" else user_nobles[nobleman_id][
                        "hour"]
                    if actual_expire is None:
                        return False, f"{noble_type}贵族有效期为None, 无法验证"
                    if abs(actual_expire - valid_days) > 0:
                        return False, f"{noble_type}贵族有效期不匹配, 实际有效期: {actual_expire} != {valid_days}"

                return True, f"{noble_type}贵族验证通过"

            # VIP奖励
            elif reward_type == 4:
                user_vip = vip_results.get(user_id, {})
                if "Vip" not in user_vip or not user_vip["Vip"].get("valid"):
                    return False, "VIP未下发"

                # 验证有效期
                if RewardPackVerification._is_duration_unit(unit) and valid_days > 0:
                    actual_expire = user_vip["Vip"].get("valid_day" if unit == "天" else "valid_hour", 0)
                    if abs(actual_expire - valid_days) > 0:
                        return False, f"VIP有效期不匹配, 实际有效期: {actual_expire} != {valid_days}"

                return True, "VIP验证通过"

            # 超级VIP奖励
            elif reward_type == 5:
                user_vip = vip_results.get(user_id, {})
                if "SuperVip" not in user_vip or not user_vip["SuperVip"].get("valid"):
                    return False, "超级VIP未下发"

                # 验证有效期
                if RewardPackVerification._is_duration_unit(unit) and valid_days > 0:
                    actual_expire = user_vip["SuperVip"].get("valid_day" if unit == "天" else "valid_hour", 0)
                    if abs(actual_expire - valid_days) > 0:
                        return False, f"超级VIP有效期不匹配, 实际有效期: {actual_expire} != {valid_days}"

                return True, "超级VIP验证通过"

            # 靓号奖励
            elif reward_type == 6:
                user_nice_numbers = nice_number_results.get(user_id, {})
                if reward_id not in user_nice_numbers:
                    return False, f"{reward_desc} - {reward_id} 未下发"

                return True, f"{reward_desc}验证通过"

            else:
                return False, f"未知奖励类型: {reward_type}"

        except Exception as e:
            return False, f"验证过程中发生错误: {str(e)}"

    def validate(self):
        """
        执行完整的奖励验证流程

        Returns:
            bool: 验证是否通过
        """
        self.logger.info("=" * 50)
        self.logger.info("=== 开始活动榜单奖励验证 ===")

        try:
            # 1、获取活动文档中的奖励配置
            activity_reward_config_doc = self.get_activity_reward_config_doc(self.activity_config_path)

            # 2、获取数据库表中的奖励配置
            activity_reward_config_db = self.get_activity_reward_config_db()

            # 3、比较奖励配置是否一致
            self.verify_db_vs_doc(activity_reward_config_doc, activity_reward_config_db)

            # 4、获取活动定时任务
            scheduled_tasks = self.get_scheduled_tasks()

            # 5、构建榜单唯一键到配置元信息的映射
            activity_type_map = {}
            for config in activity_reward_config_doc:
                if not isinstance(config, dict):
                    continue
                rank_key = self._build_rank_key(config)
                activity_type_map[rank_key] = {
                    "rank_category": self._safe_int(config.get("rank_category")),
                    "activityType_name": config.get("activityType_name", ""),
                    "rank_scope": self._get_rank_scope(config.get("activityType_name", "")),
                }
            self.logger.info(f"活动榜单类型映射: {activity_type_map}")

            # 6、定时任务与榜单类型的映射
            task_rank_type_map = {}
            new_scheduled_tasks = []
            for task in scheduled_tasks:
                task_name = task["taskName"]
                task_id = task["taskId"]
                task_rank_type_map[task_id] = []
                if "@ACTIVITY_DAY_END" in task_id or "@ACTIVITY_END_DAY" in task_id:
                    for rank_key, rank_meta in activity_type_map.items():
                        if rank_meta.get("rank_scope") == "day":
                            task_rank_type_map[task_id].append(rank_key)
                elif "@ACTIVITY_END" in task_id:
                    for rank_key, rank_meta in activity_type_map.items():
                        if rank_meta.get("rank_scope") == "total":
                            task_rank_type_map[task_id].append(rank_key)

                if task_rank_type_map[task_id]:
                    new_scheduled_tasks.append(task)
                else:
                    self.logger.warning(f"无法识别定时任务 {task_name} 对应的榜单")

            # 6、执行定时任务和验证
            all_tasks_successful = True
            all_validation_result = []
            for task in new_scheduled_tasks:
                task_id = task["taskId"]
                task_name = task["taskName"]

                # 获取当前任务对应的榜单类型
                rank_types = task_rank_type_map.get(task_id)
                if not rank_types:
                    self.logger.warning(f"无法识别定时任务 {task_name} 对应的榜单类型, 跳过执行")
                    continue
                # 从活动配置中获取榜单类型名称
                rank_type_names = [
                    self._get_activity_type_name_by_rank_type(rank_type, activity_reward_config_doc)
                    for rank_type in rank_types
                ]

                # 6.1、获取活动榜单数据 - 用户排名及对应奖励
                self.logger.info(f"获取 {"、".join(rank_type_names)} 榜单数据")
                ranking_data = self.get_activity_ranking_data(filter_rank_types = rank_types)

                # 6.2、执行任务前清除榜单中用户奖励
                self.logger.info(f"清除 {"、".join(rank_type_names)} 下发奖励前已有的装扮、荣誉称号、勋章、贵族、会员/超级会员、靓号")
                self.clear_user_rewards(ranking_data, activity_reward_config_doc, rank_types)

                # 6.3、执行定时任务
                self.logger.info(f"开始执行定时任务: {task_name}")
                if not self.execute_scheduled_task(task):
                    self.logger.error(f"定时任务 {task_name} 执行失败, 跳过该榜单验证")
                    all_tasks_successful = False
                    continue

                # 6.4、验证榜单奖励下发情况
                self.logger.info(f"开始验证 {"、".join(rank_type_names)} 奖励下发情况")
                validation_result = self.validate_reward_distribution(ranking_data, activity_reward_config_doc, rank_types)
                all_validation_result.append(validation_result)
                self.logger.info(f"{"、".join(rank_type_names)}奖励验证完成")
                self.logger.info("-" * 50)

            # 7、汇总验证结果
            if all_validation_result:
                # 计算汇总统计信息
                total_users = sum(len(result.get("total_users", [])) for result in all_validation_result)
                total_correct_users = sum(
                    len(result.get("users_with_correct_rewards", [])) for result in all_validation_result)
                total_incorrect_users = sum(
                    len(result.get("users_with_incorrect_rewards", [])) for result in all_validation_result)
                total_without_rewards = sum(
                    len(result.get("users_without_rewards", [])) for result in all_validation_result)

                # 输出汇总报告
                self.logger.info("🎯 所有榜单奖励验证结果汇总")
                self.logger.info(f"📊 总用户数: {total_users}")
                self.logger.info(f"✅ 奖励下发正确的用户数: {total_correct_users}")
                if total_incorrect_users > 0:
                    self.logger.error(f"❌ 奖励下发错误的用户数: {total_incorrect_users}")
                if total_without_rewards > 0:
                    self.logger.error(f"⚠️ 无奖励配置的用户数: {total_without_rewards}")
                # 按奖励类型统计错误
                reward_error_stats = {}
                for result in all_validation_result:
                    for user_validation in result.get("reward_validation_details", []):
                        for reward_validation in user_validation["validation_results"]:
                            if not reward_validation["is_valid"]:
                                reward_type = reward_validation["reward_type"]
                                if reward_type not in reward_error_stats:
                                    reward_error_stats[reward_type] = 0
                                reward_error_stats[reward_type] += 1

                if reward_error_stats:
                    self.logger.error("📊 按奖励类型统计错误:")
                    for reward_type, count in sorted(reward_error_stats.items()):
                        self.logger.error(f"  - {self.reward_mapper.get_reward_type_desc(reward_type)}: {count}个错误")

                self.logger.info("=" * 50)

                # 检查是否所有任务都成功
                if total_incorrect_users > 0 or total_without_rewards > 0:
                    all_tasks_successful = False
            return all_tasks_successful

        except Exception as e:
            self.logger.error(f"验证过程中发生错误: {str(e)}")
            return False


def main():
    """主函数"""

    # 创建验证器
    validator = RewardPackVerification(
        activity_number = 1061,
        activity_config_path = "test_activity/2026_april_fools_reward_config.yaml",
    )

    # 执行验证
    success = validator.validate()
    if success:
        validator.logger.info("✅ 所有奖励验证通过")
    else:
        validator.logger.error("❌ 存在奖励验证失败")
    return success


if __name__ == "__main__":
    main()