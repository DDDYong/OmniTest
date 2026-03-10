"""
-------------------------------------------------
File:           activity_reward_verify.py
Author:         duanyang
Date:           2026/1/4
-------------------------------------------------
Description:
活动榜单奖励下发验证模块
-------------------------------------------------
"""
import random
from typing import Dict, List, Any, Optional

from config.config_manager import config_manager
from scripts.reward_type_mapper import RewardTypeMapper
from utils import logger, util
from utils.api import ApiClient
from utils.db.mysql_client import MySQLClient
from utils.decorator_util import wait_with_jitter
from utils.file_util import FileHandler


class ActivityRewardVerification:
    """
    活动奖励验证模块
    """

    def __init__(self, activity_number: int, activity_config_path: str, rank_mapping: Dict[int, str]):
        """
        初始化活动奖励验证模块

        Args:
            activity_number: 活动ID
            activity_config_path: 活动奖励配置文件路径
        """
        self.activity_number = activity_number
        self.activity_config_path = activity_config_path
        self.rank_mapping = rank_mapping
        self.logger = logger
        self.filehandler = FileHandler()
        self.api_client = ApiClient()
        self.db = MySQLClient(config_manager.get_mysql_config())
        self.reward_mapper = RewardTypeMapper()

        # 缓存字典，减少重复的文件读取和数据库查询
        self._cache = {
            'activity_reward_config_doc': [],
            'activity_reward_config_db': [],
            'expected_rewards': {},  # {(ranking, activity_type): expected_rewards}
            'activity_ranking_data': {},  # 榜单用户排名数据
            'user_expected_rewards': {},  # {user_id: {rank_type: {ranking: expected_rewards}}}
        }

    def get_activity_reward_config_doc(self, activity_config_path: str) -> List[Dict[str, Any]]:
        """
        获取活动文档中的奖励配置

        Args:
            activity_config_path: 活动奖励配置文件路径

        Returns:
            dict: 奖励配置
        """
        # 检查缓存中是否已有文档配置，避免重复读取YAML文件
        if not self._cache['activity_reward_config_doc']:
            self.logger.info("获取活动文档中的奖励配置")
            activity_reward_config = self.filehandler.read_yaml(activity_config_path)
            self.logger.info(f"文档配置: {activity_reward_config}")
            self._cache['activity_reward_config_doc'] = activity_reward_config
        else:
            self.logger.debug("使用缓存的活动文档奖励配置")
            activity_reward_config = self._cache['activity_reward_config_doc']
        return activity_reward_config

    def get_activity_reward_config_db(self) -> List[Dict[str, Any]]:
        """
        获取数据库中的奖励配置, 并根据服务端映射处理奖励类型

        Returns:
            List[Dict]: 处理后的奖励配置列表
        """
        # 检查缓存中是否已有数据库配置，避免重复查询数据库
        if not self._cache['activity_reward_config_db']:
            self.logger.info("获取数据库中的奖励配置")

            # 查询数据库中的奖励配置
            query = """
                SELECT activityType, rankNumber, rewardType, rewardId, rewardCount, sex FROM `kong_test`.`reward_option_config` 
                WHERE activityNumber = %s
            """
            rewards = self.db.execute_query(query, (self.activity_number,))

            if not rewards:
                self.logger.warning(f"未找到活动 {self.activity_number} 的奖励配置")
                activity_reward_config = []
            else:
                # 处理奖励配置
                activity_reward_config = []
                for reward in rewards:
                    reward['rankNumber'] = reward['rankNumber'] + 1
                    reward_type = reward.get('rewardType', 0)

                    # 根据服务端映射处理奖励类型
                    reward['rewardType_name'] = self.reward_mapper.get_reward_type_name(reward_type)
                    reward['rewardType_desc'] = self.reward_mapper.get_reward_type_desc(reward_type)
                    activity_reward_config.append(reward)

            self.logger.info(f"数据库配置: {activity_reward_config}")
            self._cache['activity_reward_config_db'] = activity_reward_config
        else:
            self.logger.debug("使用缓存的数据库奖励配置")
            activity_reward_config = self._cache['activity_reward_config_db']
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
        for doc_rank in doc_config:
            activityType_doc = doc_rank["activityType"]
            # 遍历该榜单的所有rank
            for reward_detail in doc_rank["reward_details"]:
                rank_doc = reward_detail["rank"]
                # 遍历该rank的所有奖励类型
                for reward in reward_detail["rewards"]:
                    rewardType_doc = reward["rewardType"]
                    # 构造查询key, 榜单分类_排名_奖励类型
                    query_key = f"{activityType_doc}_{rank_doc}_{rewardType_doc}_{reward['rewardId']}"

                    # 头像框奖励(rewardType=2)可能需要根据男女区分
                    if rewardType_doc == 2:
                        reward_desc = reward["reward_desc"]
                        if "（男）" in reward_desc:
                            query_key += "_男"
                        elif "（女）" in reward_desc:
                            query_key += "_女"

                    # 存储文档中该奖励的详细信息
                    doc_quick_query[query_key] = {
                        "rewardId_doc": reward["rewardId"],  # 奖励ID
                        "valid_days_doc": reward["valid_days"] if reward["valid_days"] != -1 else "永久",  # 奖励时长
                        "rewardType_name_doc": reward["rewardType_name"],  # 奖励类型名称
                        "activityType_name_doc": doc_rank["activityType_name"],  # 榜单名称
                        "rewardType_desc_doc": reward["reward_desc"],  # 奖励描述
                    }

        differences = {
            "db_exist_doc_not": [],  # 数据库未配置的奖励
            "rewardId_mismatch": [],  # rewardId不一致的奖励
            "reward_count_error": [],  # 奖励数量(rewardCount)不一致的奖励
            "valid_days_mismatch": []  # 奖励时长 (valid_days)不一致的奖励
        }

        for db_item in db_config:
            activityType_db = db_item["activityType"]
            rankNumber_db = db_item["rankNumber"]
            rewardType_db = db_item["rewardType"]
            rewardId_db = db_item["rewardId"]
            rewardCount_db = db_item["rewardCount"]
            rewardType_name_db = db_item["rewardType_name"]
            rewardType_desc_db = db_item["rewardType_desc"]
            rewardType_sex_db = db_item.get("sex", "")

            # 构造查询key, 通过两个查询key进行匹配
            query_key = f"{activityType_db}_{rankNumber_db}_{rewardType_db}_{rewardId_db}"

            # 头像框奖励(rewardType=2)根据性别区分
            if rewardType_db == 2:
                if rewardType_sex_db == 1:
                    query_key += "_男"
                elif rewardType_sex_db == 2:
                    query_key += "_女"

            # 校验数据库存在的奖励, 是否在文档中存在
            if query_key not in doc_quick_query:
                differences["db_exist_doc_not"].append({
                    "db_info": {
                        "activityType": activityType_db,
                        "rankNumber": rankNumber_db,
                        "rewardType": rewardType_db,
                        "rewardType_name": rewardType_name_db,
                        "rewardType_desc": rewardType_desc_db,
                        "rewardId": rewardId_db,
                        "rewardCount": rewardCount_db,
                    },
                    "reason": "该奖励在数据库中存在, 但文档配置中无对应记录"
                })
                # 文档中存在, 跳过当前奖励, 直接处理下一个数据库奖励配置
                continue

            # 文档存在, 进一步校验rewardId是否一致
            doc_info = doc_quick_query[query_key]
            if doc_info["rewardId_doc"] != rewardId_db:
                differences["rewardId_mismatch"].append({
                    "common_info": {
                        "activityType": activityType_db,
                        "activityType_name_doc": doc_info["activityType_name_doc"],
                        "rank": rankNumber_db,
                        "rewardType": rewardType_db,
                        "rewardType_name_doc": doc_info["rewardType_name_doc"],
                        "rewardType_name_db": rewardType_name_db,
                        "rewardType_desc_db": doc_info["rewardType_desc_doc"],
                        "rewardType_desc_doc": doc_info["rewardType_desc_doc"],
                    },
                    "rewardId_doc": doc_info["rewardId_doc"],
                    "rewardId_db": rewardId_db,
                    "reason": "奖励ID不一致(数据库配置的奖励ID与文档不匹配)"
                })

            # rewardID一致, 进一步校验奖励有效期(valid_days vs rewardCount)是否一致
            # 特殊处理：勋章(Type=1)和靓号(Type=6)是永久奖励, 跳过有效期校验
            if rewardType_db in {1, 6}:
                if rewardCount_db == 1:
                    continue
                else:
                    self.logger.error(f"奖励数量错误: {doc_info["rewardType_desc_doc"]} (Type={rewardType_db}) | 榜单: {doc_info['activityType_name_doc']} | 排名: {rankNumber_db} | 奖励rewardId: {rewardId_db} | 数据库数量: {rewardCount_db}个")
                    differences["reward_count_error"].append({
                        "common_info": {
                            "activityType": activityType_db,
                            "activityType_name_doc": doc_info["activityType_name_doc"],
                            "rank": rankNumber_db,
                            "rewardType": rewardType_db,
                            "rewardType_name_doc": doc_info["rewardType_name_doc"],
                            "rewardType_desc_db": rewardType_desc_db,
                            "rewardType_desc_doc": doc_info["rewardType_desc_doc"],
                        },
                        "rewardId_db": rewardId_db,
                        "rewardCount_db": rewardCount_db,
                        "reason": "永久奖励数量错误(应为1个)"
                    })
                    continue
            if doc_info["valid_days_doc"] != rewardCount_db:
                differences["valid_days_mismatch"].append({
                    "common_info": {
                        "activityType": activityType_db,
                        "activityType_name_doc": doc_info["activityType_name_doc"],
                        "rank": rankNumber_db,
                        "rewardType": rewardType_db,
                        "rewardType_name_doc": doc_info["rewardType_name_doc"],
                        "rewardType_desc_db": rewardType_desc_db,
                        "rewardType_desc_doc": doc_info["rewardType_desc_doc"],
                    },
                    "rewardId_db": rewardId_db,
                    "valid_days_doc (文档有效期)": doc_info["valid_days_doc"],
                    "rewardCount_db (数据库有效期)": rewardCount_db,
                    "reason": "奖励有效期不一致"
                })

        self.logger.info(f"共校验数据库奖励配置: {len(db_config)}条")

        # 数据库有、文档无
        if differences["db_exist_doc_not"]:
            self.logger.info(f"[差异: 数据库存在、文档无] 共{len(differences['db_exist_doc_not'])}条")
            for item in differences["db_exist_doc_not"]:
                db = item["db_info"]
                self.logger.info(f"榜单: activityType={db['activityType']} | 排名: {db['rankNumber']} | 奖励类型: {db['rewardType_desc']} (Type={db['rewardType']}) | 数据库rewardId: {db['rewardId']} | 原因: {item['reason']}")

        # rewardId不一致
        if differences["rewardId_mismatch"]:
            self.logger.info(f"[差异: rewardId不匹配] 共{len(differences['rewardId_mismatch'])}条")
            for item in differences["rewardId_mismatch"]:
                common = item["common_info"]
                self.logger.info(f"榜单: {common['activityType_name_doc']} (Type={common['activityType']}) | 排名: {common['rank']} | 奖励类型: {common['rewardType_desc_doc']} (Type={common['rewardType']}) | 文档rewardId: {item['rewardId_doc']} | 数据库rewardId: {item['rewardId_db']}")

        # 永久奖励数量错误
        if differences["reward_count_error"]:
            self.logger.info(f"[差异: 永久奖励数量错误] 共{len(differences['reward_count_error'])}条")
            for item in differences["reward_count_error"]:
                common = item["common_info"]
                self.logger.error(f"榜单: {common['activityType_name_doc']} (Type={common['activityType']}) | 排名: {common['rank']} | 奖励类型: {common['rewardType_desc_doc']} (Type={common['rewardType']}) | 奖励rewardId: {item['rewardId_db']} | 数据库数量: {item['rewardCount_db']}个 | 原因: {item['reason']}")

        # 有效期不匹配
        if differences["valid_days_mismatch"]:
            self.logger.info(f"[差异: 有效期不匹配] 共{len(differences['valid_days_mismatch'])}条")
            for item in differences["valid_days_mismatch"]:
                common = item["common_info"]
                self.logger.info(f"榜单: {common['activityType_name_doc']} (Type={common['activityType']}) | 排名: {common['rank']} | 奖励类型: {common['rewardType_desc_doc']} (Type={common['rewardType']}) | 奖励rewardId: {item['rewardId_db']} | 文档有效期: {item['valid_days_doc (文档有效期)']}天 | 数据库有效期: {item['rewardCount_db (数据库有效期)']}天")

        # 数据库配置与文档一致
        if not any(differences.values()):
            self.logger.info("✅ 数据库配置所有奖励均在文档中存在, 且rewardId、有效期完全一致！")
        else:
            self.logger.warning(f"❌ 发现 {sum(len(v) for v in differences.values())} 条差异, 请检查文档和数据库配置！")

        return differences

    def get_activity_ranking_data(self, filter_rank_types: Optional[List[int]] = None) -> List[Dict]:
        """
        获取活动榜单数据 - 用户排名及对应奖励
        Args:
            filter_rank_types: 可选，要获取的榜单类型列表
        Returns:
            List[Dict]: 格式化后的榜单数据
        """
        # 构建缓存键，包括过滤条件
        cache_key = (tuple(filter_rank_types) if filter_rank_types else None)

        # 检查缓存中是否已有对应过滤条件的榜单数据
        if cache_key in self._cache.get('activity_ranking_data', {}):
            self.logger.debug(f"使用缓存的活动榜单数据 (过滤条件: {filter_rank_types})")
            return self._cache['activity_ranking_data'][cache_key]

        # 从奖励配置文档读取榜单信息
        activity_reward_config = self.get_activity_reward_config_doc(self.activity_config_path)

        all_ranked_data = []  # 收集所有榜单数据

        # 遍历所有榜单配置
        for config in activity_reward_config:
            rank_type = config.get('activityType', 0)

            # 检查是否需要过滤榜单类型
            if filter_rank_types and rank_type not in filter_rank_types:
                continue

            rank_category = config.get('rank_category', '0')
            activity_type_name = config.get('activityType_name', '')
            rank_coverage = config.get('rank_coverage', 10)

            # 根据activityType_name判断榜单类型
            if '日榜' in activity_type_name:
                # 日榜的stage设为当前日期的前一天
                query = """select nowTime from `kong_test`.`activity_gift_medal` where id = %s"""
                result = self.db.get_one(query, (self.activity_number,))
                stage = util.format_time(util.get_time_delta(datetime_obj = result.get('nowTime'), days = -1), format_str = '%Y%m%d')
            elif '总榜' in activity_type_name:
                # 只有一个赛段时, stage设为-1, TODO 多赛段时，stage的值
                stage = "-1"
            else:
                self.logger.warning(f"未知榜单类型: {activity_type_name}, 跳过处理")
                continue

            self.logger.info(f"处理榜单配置：{activity_type_name}, 阶段={stage}, TopN={rank_coverage}")

            try:
                # 按条件查询榜单数据
                raw_data = self._query_ranking_data(rank_category, stage, rank_coverage)

                # 检查数据量是否足够
                if len(raw_data) < rank_coverage:
                    self.logger.warning(f"现有数据不足TopN({rank_coverage}), 当前只有{len(raw_data)}条, 需要补足数据")
                    missing_count = rank_coverage - len(raw_data)

                    # 插入缺少的数据
                    inserted_count = self._insert_test_ranking_data(rank_category, stage, missing_count)

                    if inserted_count > 0:
                        self.logger.info(f"成功插入{inserted_count}条测试数据, 重新查询榜单数据")
                        # 重新查询数据
                        raw_data = self._query_ranking_data(rank_category, stage, rank_coverage)
                    else:
                        self.logger.warning("复制数据失败, 使用现有数据进行处理")

                # 处理榜单数据并计算排名
                if raw_data:
                    ranked_data = self._process_ranking_data(raw_data, rank_type)
                    self.logger.debug(f"成功获取到 {len(ranked_data)} 条榜单数据, 排名范围: 1-{rank_coverage}")
                    # 将当前配置的数据添加到总结果中
                    all_ranked_data.extend(ranked_data)
                else:
                    self.logger.warning(f"没有获取到榜单数据, 跳过处理")

            except Exception as e:
                self.logger.error(f"获取活动榜单数据失败: {str(e)}")
                # 继续处理下一个榜单
                continue

        self.logger.info(f"总共获取到 {len(all_ranked_data)} 条榜单数据")

        # 将结果存入缓存
        if 'activity_ranking_data' not in self._cache:
            self._cache['activity_ranking_data'] = {}
        self._cache['activity_ranking_data'][cache_key] = all_ranked_data

        return all_ranked_data

    def get_user_expected_rewards(self, ranking_data: List[Dict], activity_reward_config: List[Dict[str, Any]],
                                  filter_rank_types: Optional[List[int]] = None,
                                  exclude_accumulate_types: Optional[List[int]] = None) -> Dict:
        """
        获取用户预期奖励，按用户ID分组

        Args:
            ranking_data: 榜单数据
            activity_reward_config: 活动奖励配置
            filter_rank_types: 可选，要获取的榜单类型列表
            exclude_accumulate_types: 可选，不需要累加有效期的奖励类型列表，默认[1, 6]（勋章、靓号）

        Returns:
            Dict: 按用户ID分组的预期奖励，格式: {user_id: {rank_type: {ranking: expected_rewards}}}
        """

        # 构建缓存键
        def make_hashable(obj):
            if isinstance(obj, (list, tuple)):
                return tuple(make_hashable(item) for item in obj)
            elif isinstance(obj, dict):
                return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
            else:
                return obj

        cache_key = (
            make_hashable(ranking_data) if ranking_data else None,
            make_hashable(activity_reward_config) if activity_reward_config else None,
            tuple(filter_rank_types) if filter_rank_types else None,
            tuple(exclude_accumulate_types) if exclude_accumulate_types else None
        )

        # 检查缓存
        if cache_key in self._cache.get('user_expected_rewards', {}):
            self.logger.debug("使用缓存的用户预期奖励")
            return self._cache['user_expected_rewards'][cache_key]

        # 设置默认需要不累加的奖励类型
        if exclude_accumulate_types is None:
            exclude_accumulate_types = [1, 6]

        # 收集所有需要查询的用户ID
        user_ids = []
        for user_data in ranking_data:
            user_id = user_data.get('user_id')
            rank_type = user_data.get('rank_type')

            # 指定过滤条件，只处理指定的榜单类型
            if filter_rank_types and rank_type not in filter_rank_types:
                continue

            if user_id not in user_ids:
                user_ids.append(user_id)

        # 批量查询用户角色和性别信息
        user_role_map = {}
        user_sex_map = {}
        if user_ids:
            placeholders = ', '.join(['%s'] * len(user_ids))
            user_query = f"""
                SELECT userid, role, sex FROM `kong_test`.`user` 
                WHERE userid IN ({placeholders})
            """
            users = self.db.execute_query(user_query, tuple(user_ids))

            # 构建用户ID到角色和性别的映射
            for user_info in users:
                user_role_map[user_info['userid']] = user_info['role']
                user_sex_map[user_info['userid']] = user_info['sex']

        user_expected_rewards = {}
        # 记录同一用户同一奖励类型和ID的累计有效期
        user_reward_aggregate = {}

        for user_data in ranking_data:
            user_id = user_data.get('user_id')
            ranking = user_data.get('ranking')
            rank_type = user_data.get('rank_type')

            # 指定过滤条件，只处理指定的榜单类型
            if filter_rank_types and rank_type not in filter_rank_types:
                continue

            # 获取用户应得奖励
            expected_rewards = self.get_expected_rewards_by_ranking(ranking, rank_type, activity_reward_config)

            # 根据用户角色、性别和榜单类型筛选奖励
            user_role = user_role_map.get(user_id, 0)  # 默认普通用户
            user_sex = user_sex_map.get(user_id, 1)  # 默认性别男
            filtered_rewards = []

            for reward in expected_rewards:
                reward_type = reward.get('rewardType')
                reward_id = reward.get('rewardId')
                valid_days = reward.get('valid_days', 0)
                reward_desc = reward.get('reward_desc', '')

                if reward_type == 2:
                    # 头像框奖励区分男女用户
                    if ('（男）' in reward_desc and user_sex != 1) or ('（女）' in reward_desc and user_sex != 2):
                        continue

                # 检查是否需要累加有效期
                if reward_type not in exclude_accumulate_types:
                    if user_id not in user_reward_aggregate:
                        user_reward_aggregate[user_id] = {}
                    # 确保 reward_id 是可哈希的类型
                    if isinstance(reward_id, dict):
                        # 如果 reward_id 是字典，尝试获取其 id 键值
                        reward_id = reward_id.get('id', str(reward_id))
                    reward_key = (reward_type, reward_id)
                    reward_info = user_reward_aggregate[user_id].setdefault(reward_key, {
                        'reward_id': reward_id,
                        'valid_days': 0,
                        'reward_desc': reward_desc,
                        'accumulated_days': []
                    })
                    reward_info['accumulated_days'].append(valid_days)
                    reward_info['valid_days'] += valid_days

                    # 陪伴师专属奖励
                if user_role == 5 and reward_type == 5:
                    # 超级VIP奖励，需要累加有效期
                    if user_id not in user_reward_aggregate:
                        user_reward_aggregate[user_id] = {}
                    reward_key = (reward_type, reward_id)
                    if reward_key not in user_reward_aggregate[user_id]:
                        user_reward_aggregate[user_id][reward_key] = {
                            'reward_id': reward_id,
                            'valid_days': 0,
                            'reward_desc': reward_desc,
                            'accumulated_days': []
                        }
                    # 累加有效期
                    user_reward_aggregate[user_id][reward_key]['valid_days'] += valid_days
                    user_reward_aggregate[user_id][reward_key]['accumulated_days'].append(valid_days)
                # 普通用户专属奖励
                elif user_role == 0 and reward_type == 16:
                    # 公爵贵族奖励，需要累加有效期
                    if user_id not in user_reward_aggregate:
                        user_reward_aggregate[user_id] = {}
                    reward_key = (reward_type, reward_id)
                    if reward_key not in user_reward_aggregate[user_id]:
                        user_reward_aggregate[user_id][reward_key] = {
                            'reward_id': reward_id,
                            'valid_days': 0,
                            'reward_desc': reward_desc,
                            'accumulated_days': []
                        }
                    # 累加有效期
                    user_reward_aggregate[user_id][reward_key]['valid_days'] += valid_days
                    user_reward_aggregate[user_id][reward_key]['accumulated_days'].append(valid_days)
                # 其他奖励类型直接保留
                else:
                    if isinstance(reward_id, dict):
                        reward_id = reward_id.get('id', str(reward_id))
                        # 更新奖励中的 rewardId
                        reward['rewardId'] = reward_id
                    filtered_rewards.append(reward)

        # 构建累加后的预期奖励结构
        for user_id in user_role_map.keys():
            if user_id not in user_expected_rewards:
                user_expected_rewards[user_id] = {}

            # 添加需要累加的奖励
            if user_id in user_reward_aggregate:
                for key, reward_info in user_reward_aggregate[user_id].items():
                    reward_type, reward_id = key  # 解包键，获取 reward_type 和 reward_id
                    if 'aggregate' not in user_expected_rewards[user_id]:
                        user_expected_rewards[user_id]['aggregate'] = {}
                    # 使用0作为排名标识
                    accumulated_reward = {
                        'rewardType': reward_type,
                        'rewardId': reward_info['reward_id'],
                        'valid_days': reward_info['valid_days'],
                        'reward_desc': reward_info['reward_desc'],
                        'is_accumulated': True  # 标记为累加后的奖励
                    }
                    user_expected_rewards[user_id]['aggregate'][0] = [accumulated_reward]
                    # 构建累加表达式
                    accumulated_days = reward_info.get('accumulated_days', [])
                    if len(accumulated_days) > 1:
                        expr = ' + '.join(map(str, accumulated_days))
                        self.logger.info(f"用户[{user_id}] 奖励类型[{reward_type}] 已累加，累计有效期[{expr} = {reward_info['valid_days']}]天")
                    else:
                        self.logger.info(f"用户[{user_id}] 奖励类型[{reward_type}] 有效期[{reward_info['valid_days']}]天")

        # 将原始奖励添加到预期奖励中（但不包括已经累加的奖励类型）
        for user_data in ranking_data:
            user_id = user_data.get('user_id')
            ranking = user_data.get('ranking')
            rank_type = user_data.get('rank_type')

            # 指定过滤条件，只处理指定的榜单类型
            if filter_rank_types and rank_type not in filter_rank_types:
                continue

            # 获取用户应得奖励
            expected_rewards = self.get_expected_rewards_by_ranking(ranking, rank_type, activity_reward_config)

            # 根据用户角色和性别筛选奖励：只保留不需要累加的奖励类型和装扮类奖励
            # user_role = user_role_map.get(user_id, 0)  # 默认普通用户
            user_sex = user_sex_map.get(user_id, 1)  # 默认性别男
            filtered_rewards = []

            for reward in expected_rewards:
                reward_type = reward.get('rewardType')
                reward_id = reward.get('rewardId')
                reward_desc = reward.get('reward_desc', '')

                # 跳过需要累加的奖励类型
                if reward_type not in exclude_accumulate_types:
                    continue

                # 头像框奖励区分男女用户
                if reward_type == 2:  # AVATAR_COVER
                    if ('（男）' in reward_desc and user_sex != 1) or ('（女）' in reward_desc and user_sex != 2):
                        self.logger.debug(f"用户{user_id}性别{user_sex}不匹配头像框奖励{reward_desc}，跳过")
                        continue

                if isinstance(reward_id, dict):
                    reward_id = reward_id.get('id', str(reward_id))
                    # 更新奖励中的 rewardId
                    reward['rewardId'] = reward_id

                filtered_rewards.append(reward)

            # 按用户ID、榜单类型、排名分组存储
            if user_id not in user_expected_rewards:
                user_expected_rewards[user_id] = {}
            if rank_type not in user_expected_rewards[user_id]:
                user_expected_rewards[user_id][rank_type] = {}
            user_expected_rewards[user_id][rank_type][ranking] = filtered_rewards

        # 存入缓存
        if 'user_expected_rewards' not in self._cache:
            self._cache['user_expected_rewards'] = {}
        self._cache['user_expected_rewards'][cache_key] = user_expected_rewards

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
        # 查询数据并按value降序排列
        query = """
                SELECT number, userId, intimateId, category, stage, year, month, day, value
                FROM `kong_test`.`activity_rank`
                WHERE number = %s and category = %s and stage = %s
                ORDER BY value DESC LIMIT %s
            """

        raw_data = self.db.execute_query(query, (self.activity_number, rank_category, stage, rank_coverage))
        # 女神节榜单数据不是在activity_rank表中, 而是activity_group_member表中
        # query = """
        #     select 1059 as number, userId, userId as intimateId, 0 as category, stage, -1 as year, -1 as month, -1 as day, score as value
        #     from kong_test.activity_group_member
        #     where groupId in (select groupId
        #                       from kong_test.activity_group
        #                       where activityId = 1059
        #                         and activityType = 11
        #                         and stage = '105905'
        #                       order by scoreSum desc) order by score desc limit 7;
        # """
        # raw_data = self.db.execute_query(query, ())
        return raw_data

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
            existing_user_pairs.add((user['userId'], user['intimateId']))
            existing_user_ids.add(user['userId'])
            existing_user_ids.add(user['intimateId'])

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
            self.logger.info(f"发现同一类型的其他榜单有{len(other_stage_data)}条数据，复制其中{copy_count}条")

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
                            other_stage_data[i]['userId'], other_stage_data[i]['intimateId'],
                            self.activity_number, ranking_category, stage, year, month, day,
                            template_data['value'] * random.uniform(0.8, 1.2), template_data['value1'],
                            template_data['value2'],
                            template_data['value3'], template_data['value4'], template_data['value5'],
                            template_data['value6'], template_data['value7'], template_data['valueTime'],
                            template_data['source'], template_data['display'], template_data['completed'],
                            template_data['created'], template_data['updated']

                        )
                    )
                    inserted_count += 1
                    existing_user_pairs.add((other_stage_data[i]['userId'], other_stage_data[i]['intimateId']))
                    existing_user_ids.add(other_stage_data[i]['userId'])
                    existing_user_ids.add(other_stage_data[i]['intimateId'])
                    self.logger.info(f"复制榜单数据 {other_stage_data[i]['userId']} - {other_stage_data[i]['intimateId']}")
                except Exception as e:
                    self.logger.error(f"复制榜单数据 {other_stage_data[i]['userId']} - {other_stage_data[i]['intimateId']} 失败: {str(e)}")

            self.logger.info(f"已复制插入 {inserted_count} 条测试数据")

            # 满足榜单数量要求，直接返回
            if inserted_count >= count:
                return inserted_count
            else:
                # 还需要生成的随机数据数量
                remaining_count = count - inserted_count
        else:
            # 没有其他榜单数据，全部使用随机数据生成
            remaining_count = count

        # 生成剩余的随机数据
        if remaining_count > 0:
            self.logger.info(f"使用随机数据生成剩余的 {remaining_count} 条测试数据")

            # 随机获取不在排行榜中的用户ID
            existing_ids_str = ','.join(map(str, existing_user_ids))
            random_users_query = """
                                SELECT userid FROM `kong_test`.`user` 
                                WHERE status = 0 and role = 5 and userid NOT IN (%s)
                                ORDER BY lastLoginDate desc LIMIT %s
                            """
            random_users = self.db.execute_query(random_users_query, (existing_ids_str, remaining_count * 2,))
            for i in range(remaining_count):
                if template_data['userId'] == template_data['intimateId']:  # 单人榜
                    # 生成唯一的单人记录
                    max_attempts = 3  # 最多尝试3次
                    for attempt in range(max_attempts):
                        user_id = random_users[i + attempt]['userid']
                        intimate_id = user_id
                        user_pair = (user_id, intimate_id)

                        # 检查用户对是否已存在
                        if user_pair not in existing_user_pairs:
                            existing_user_pairs.add(user_pair)
                            break
                    else:
                        self.logger.warning(f"无法为第 {i + 1} 条记录生成唯一的单人记录，已跳过")
                        continue
                else:  # 双人榜
                    # 生成唯一的用户对
                    max_attempts = 3  # 最多尝试3次
                    for attempt in range(max_attempts):
                        # 尝试不同的随机用户组合
                        user_id = random_users[i + attempt]['userid']
                        intimate_id = random_users[remaining_count + i + attempt]['userid']

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
                        self.logger.warning(f"无法为第 {i + 1} 条记录生成唯一的用户对，已跳过")
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
                            template_data['value'], template_data['value1'], template_data['value2'],
                            template_data['value3'], template_data['value4'], template_data['value5'],
                            template_data['value6'], template_data['value7'], template_data['valueTime'],
                            template_data['source'], template_data['display'], template_data['completed'],
                            template_data['created'], template_data['updated']
                        )
                    )
                    inserted_count += 1
                    self.logger.info(f"生成随机榜单数据 {user_id} - {intimate_id}")
                except Exception as e:
                    self.logger.error(f"生成随机榜单数据 {user_id} - {intimate_id} 失败: {str(e)}")

            self.logger.info(f"共插入 {inserted_count} 条测试数据")
        return inserted_count

    def _process_ranking_data(self, raw_data: List[Dict], rank_type: int) -> List[Dict]:
        """
        处理榜单数据（单人和双人分别处理)

        Args:
            raw_data: 原始榜单数据列表
            rank_type: 榜单类型

        Returns:
            List[Dict]: 处理后的榜单数据列表
        """
        ranked_data = []

        for index, item in enumerate(raw_data, 1):
            if item.get("userId") == item.get("intimateId"):
                # 单人榜处理
                ranked_item = {
                    "number": item.get("number"),  # 活动编号
                    "category": item.get("category"),
                    "rank_type": rank_type,
                    "rank_day": item.get("day"),
                    "stage": item.get("stage"),
                    "user_id": item.get("userId"),
                    "value": item.get("value"),
                    "ranking": index,
                }
                ranked_data.append(ranked_item)
            else:
                # 双人榜处理 - 两个人的排名要分别记录
                ranked_item_user1 = {
                    "number": item.get("number"),
                    "category": item.get("category"),
                    "rank_type": rank_type,
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
                    "rank_day": item.get("day"),
                    "stage": item.get("stage"),
                    "user_id": item.get("intimateId"),
                    "value": item.get("value"),
                    "ranking": index,
                }
                ranked_data.extend([ranked_item_user1, ranked_item_user2])
        self.logger.info(f"榜单数据处理完成: {ranked_data}")
        return ranked_data

    def get_expected_rewards_by_ranking(self, ranking: int, activity_type: int,
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
        # 添加类型检查
        try:
            ranking = int(ranking)
            activity_type = int(activity_type)
        except (TypeError, ValueError) as e:
            self.logger.error(f"无效的排名或榜单类型参数: ranking={ranking}, activity_type={activity_type}, 错误: {str(e)}")
            return []

        # 检查缓存中是否已有结果，避免重复计算
        cache_key = (ranking, activity_type)
        if cache_key in self._cache['expected_rewards']:
            return self._cache['expected_rewards'][cache_key]

        expected_rewards = []
        self.logger.debug(f"查找排名 {ranking} 在榜单类型 {activity_type} 的奖励配置")

        # 构建榜单类型到配置的映射，提高查找效率
        activity_config_map = {int(cfg.get('activityType')): cfg for cfg in activity_reward_config}

        # 查找对应榜单类型的配置
        target_activity_type = int(activity_type)
        if target_activity_type in activity_config_map:
            config = activity_config_map[target_activity_type]
            self.logger.debug(f"找到匹配的榜单类型配置: {config.get('activityType_name', '未知榜单')}")

            # 查找对应排名的奖励配置
            reward_details = config.get('reward_details', [])
            reward_detail_dict = {int(rd.get('rank')): rd for rd in reward_details}

            target_ranking = int(ranking)
            if target_ranking in reward_detail_dict:
                reward_detail = reward_detail_dict[target_ranking]
                rewards = reward_detail.get('rewards', [])
                expected_rewards.extend(rewards)
                self.logger.debug(f"找到排名 {ranking} 的奖励配置，共 {len(rewards)} 个奖励")
            else:
                self.logger.warning(f"在榜单类型 {activity_type} 中未找到排名 {ranking} 的奖励配置")
                # 列出该榜单所有可用的排名
                available_ranks = sorted(reward_detail_dict.keys())
                self.logger.warning(f"该榜单可用的排名: {available_ranks}")
        else:
            self.logger.warning(f"未找到榜单类型 {activity_type} 的配置")
            # 列出所有可用的榜单类型
            available_activity_types = list(activity_config_map.keys())
            self.logger.warning(f"可用的榜单类型: {available_activity_types}")

        # 将结果存入缓存
        self._cache['expected_rewards'][cache_key] = expected_rewards
        self.logger.info(f"获取{self.rank_mapping.get(activity_type)}排名 {ranking} 应下发的奖励: {expected_rewards}")
        return expected_rewards

    def clear_user_rewards(self, ranking_data: List[Dict], activity_reward_config: List[Dict[str, Any]],
                           filter_rank_types: Optional[List[int]] = None) -> None:
        """
        清除榜单用户奖励

        Args:
            ranking_data: 榜单数据
            activity_reward_config: 活动奖励配置
            filter_rank_types: 可选，要清除的榜单类型列表
        """
        # 获取用户预期奖励（使用缓存）
        user_expected_rewards = self.get_user_expected_rewards(ranking_data, activity_reward_config, filter_rank_types)

        # 收集需要清除的各种奖励
        dress_to_clear = []
        medal_to_clear = []
        title_to_clear = []
        noble_to_clear = []
        vip_to_clear = []
        super_vip_to_clear = []
        nice_number_to_clear = []

        # 遍历用户数据，收集需要清除的奖励
        for user_data in ranking_data:
            user_id = user_data.get('user_id')
            ranking = user_data.get('ranking')
            activity_type = user_data.get('rank_type')

            # 指定过滤条件，只处理指定的榜单类型
            if filter_rank_types and activity_type not in filter_rank_types:
                continue

            # 从缓存中获取用户应得奖励
            expected_rewards = user_expected_rewards.get(user_id, {}).get(activity_type, {}).get(ranking, [])
            # 获取累加奖励
            aggregate_rewards = user_expected_rewards.get(user_id, {}).get('aggregate', {}).get(0, [])
            all_rewards = expected_rewards + aggregate_rewards

            if not all_rewards:
                self.logger.warning(f"用户 {user_id} 排名 {ranking} 未找到对应的奖励配置")
                continue

            self.logger.info(f"准备清除用户 {user_id} (榜单{activity_type} 排名{ranking}) 的已有奖励")
            # 根据应得奖励类型统计需要清除的记录
            for reward in all_rewards:
                reward_type = reward.get('rewardType')
                reward_id = reward.get('rewardId')

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
                    # 贵族 - 16为公爵，17为子爵
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
                    self.logger.warning(f"未知的奖励类型: {reward_type}，无法清除")

        # 批量执行清除操作
        if dress_to_clear:
            query = "DELETE FROM `kong_test`.`user_dress` WHERE userId = %s and dressId = %s"
            affected_rows = self.db.execute_many(query, dress_to_clear)
            self.logger.info(f"批量清除装扮奖励，共影响 {affected_rows} 条记录")

        if medal_to_clear:
            query = "DELETE FROM `kong_test`.`user_medal` WHERE userId = %s and medalId = %s"
            affected_rows = self.db.execute_many(query, medal_to_clear)
            self.logger.info(f"批量清除勋章奖励，共影响 {affected_rows} 条记录")

        if title_to_clear:
            query = "DELETE FROM `kong_test`.`user_honor_title` WHERE userId = %s and titleId = %s"
            affected_rows = self.db.execute_many(query, title_to_clear)
            self.logger.info(f"批量清除荣誉称号奖励，共影响 {affected_rows} 条记录")

        if noble_to_clear:
            query = "UPDATE `kong_test`.`user_nobleman_level` SET isNobleman = 0, noblemanExpire = DATE_SUB(NOW(), INTERVAL 1 DAY) WHERE userId = %s and noblemanId = %s"
            affected_rows = self.db.execute_many(query, noble_to_clear)
            self.logger.info(f"批量清除贵族奖励，共影响 {affected_rows} 条记录")

        if vip_to_clear:
            query = "UPDATE `kong_test`.`user` SET isVip = 0, vipExpire = UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL 1 DAY)) * 1000 WHERE userId = %s"
            affected_rows = self.db.execute_many(query, vip_to_clear)
            self.logger.info(f"批量清除VIP奖励，共影响 {affected_rows} 条记录")

        if super_vip_to_clear:
            query = "UPDATE `kong_test`.`user` SET isSuperVip = 0, superVipExpire = UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL 1 DAY)) * 1000 WHERE userId = %s"
            affected_rows = self.db.execute_many(query, super_vip_to_clear)
            self.logger.info(f"批量清除超级VIP奖励，共影响 {affected_rows} 条记录")

        if nice_number_to_clear:
            query = "DELETE FROM `kong_test`.`user_gift` WHERE userId = %s and giftId = %s"
            affected_rows = self.db.execute_many(query, nice_number_to_clear)
            self.logger.info(f"批量清除靓号奖励，共影响 {affected_rows} 条记录")

    def get_scheduled_tasks(self) -> List[Dict]:
        """
        获取活动定时任务配置

        Returns:
            List[Dict]: 定时任务配置列表
        """
        activity_name = self.db.get_one("select activityName from `kong_test`.`activity_gift_medal` where id = %s", (
            self.activity_number,)
        )

        # 根据活动名称获取定时任务ID, 并对ID进行处理
        scheduled_tasks = self.db.execute_query("select job_desc as taskName, REPLACE(executor_handler, '#', '@') AS taskId from `xxl_job`.`xxl_job_info` where SUBSTRING_INDEX(SUBSTRING_INDEX(job_desc, '【', -1), '】', 1) = %s", (
            activity_name['activityName'],)
        )
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
            "expression": task['taskId']
        }
        response = self.api_client.get(url = "/api/xxl-job/execute", params = params)
        try:
            resp = response.json()
            if resp.get('code') == 200:
                self.logger.info(f"定时任务 {task['taskName']} 执行成功")
            else:
                self.logger.error(f"定时任务 {task['taskName']} 执行失败: {resp.get('err')}")
                return False
        except Exception as e:
            self.logger.error(f"定时任务 {task['taskName']} 执行异常: {str(e)}")
            return False

        return True

    @wait_with_jitter(base_delay = 2, jitter_factor = 0.3)
    def validate_reward_distribution(self, ranking_data: List[Dict], activity_reward_config: List[Dict[str, Any]],
                                     filter_rank_types: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        验证奖励下发情况

        Args:
            ranking_data: 榜单数据
            activity_reward_config: 活动奖励配置
            filter_rank_types: 可选，要验证的榜单类型列表

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

        # 按用户ID分组处理，过滤符合filter_rank_types的榜单数据
        user_ranking_dict = {}
        for data in ranking_data:
            rank_type = data.get('rank_type')
            # 检查是否需要过滤榜单类型
            if filter_rank_types and rank_type not in filter_rank_types:
                continue

            user_id = data.get('user_id')
            if user_id not in user_ranking_dict:
                user_ranking_dict[user_id] = []
            user_ranking_dict[user_id].append(data)

        validation_result["total_users"] = list(user_ranking_dict.keys())

        # 如果没有用户数据，直接返回
        if not user_ranking_dict:
            return validation_result

        # 获取所有用户预期奖励
        user_expected_rewards = self.get_user_expected_rewards(ranking_data, activity_reward_config, filter_rank_types)

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
            # 收集用户的所有排名信息
            user_rankings = []
            for user_data in user_data_list:
                ranking = user_data.get('ranking')
                rank_type = user_data.get('rank_type')
                user_rankings.append({
                    'rank': ranking,
                    'rank_type': rank_type,
                    'rank_type_name': self.rank_mapping.get(rank_type, f"未知({rank_type})")
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
            aggregate_rewards = user_expected_rewards.get(user_id, {}).get('aggregate', {}).get(0, [])
            if aggregate_rewards:
                has_any_reward = True
                for reward in aggregate_rewards:
                    reward_type = reward.get('rewardType')
                    reward_id = reward.get('rewardId')
                    # 使用 (reward_type, reward_id) 作为唯一键
                    key = (reward_type, reward_id)
                    if key not in rewards_to_validate:
                        rewards_to_validate[key] = reward

            # 遍历用户的所有符合条件的榜单数据
            for user_data in user_data_list:
                ranking = user_data.get('ranking')
                activity_type = user_data.get('rank_type')

                # 获取用户应得奖励
                expected_rewards = user_expected_rewards.get(user_id, {}).get(activity_type, {}).get(ranking, [])

                if expected_rewards:
                    has_any_reward = True
                    for reward in expected_rewards:
                        reward_type = reward.get('rewardType')
                        reward_id = reward.get('rewardId')
                        # 使用 (reward_type, reward_id) 作为唯一键
                        key = (reward_type, reward_id)
                        if key not in rewards_to_validate:
                            rewards_to_validate[key] = reward

            # 对去重后的奖励进行验证
            for key, reward in rewards_to_validate.items():
                reward_type = reward.get('rewardType')
                reward_id = reward.get('rewardId')
                valid_days = reward.get('valid_days')
                reward_desc = reward.get('reward_desc')

                # 使用批量查询结果进行验证
                is_valid, validation_msg = self._batch_validate_single_reward(
                    user_id, reward_type, reward_id, valid_days, reward_desc,
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
        self.logger.info(f"总用户数: {len(validation_result['total_users'])}" + (
            f" {validation_result['total_users']}" if len(validation_result['total_users']) > 0 else ""))
        if len(validation_result['users_with_correct_rewards']) > 0:
            self.logger.info(f"✅ 奖励下发正确的用户数: {len(validation_result['users_with_correct_rewards'])}" + (
                f" {validation_result['users_with_correct_rewards']}"))
        if len(validation_result['users_with_incorrect_rewards']) > 0:
            self.logger.error(f"❌ 奖励下发错误的用户数: {len(validation_result['users_with_incorrect_rewards'])}" + (
                f" {validation_result['users_with_incorrect_rewards']}"))
        if len(validation_result['users_without_rewards']) > 0:
            self.logger.error(f"⚠️ 无奖励配置的用户数: {len(validation_result['users_without_rewards'])}" + (
                f" {validation_result['users_without_rewards']}"))

        # 输出详细的错误奖励信息
        if len(validation_result['users_with_incorrect_rewards']) > 0:
            self.logger.error("❌ 详细错误奖励信息:")
            for user_validation in validation_result['reward_validation_details']:
                user_id = user_validation['user_id']
                # 格式化排名信息
                rankings_info = []
                for rank_info in user_validation['rankings']:
                    rankings_info.append(f"{rank_info['rank_type_name']}第{rank_info['rank']}名")
                rankings_str = "，".join(rankings_info)

                self.logger.error(f"  用户ID: {user_id} ({rankings_str})")
                for reward_validation in user_validation['validation_results']:
                    if not reward_validation['is_valid']:
                        reward_type = reward_validation['reward_type']
                        reward_id = reward_validation['reward_id']
                        error_msg = reward_validation['message']
                        self.logger.error(f"    - 奖励类型: {self.reward_mapper.get_reward_type_desc(reward_type)}, 奖励ID: {reward_id}, 错误原因: {error_msg}")

        return validation_result

    def _batch_query_dress_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询装扮奖励
        """
        if not user_ids:
            return {}

        placeholders = ', '.join(['%s'] * len(user_ids))
        query = f"""
            SELECT userId, dressId, category, timestampdiff(day, FROM_UNIXTIME(valid/1000), FROM_UNIXTIME(expire/1000)) as validDay 
            FROM `kong_test`.`user_dress` 
            WHERE userId IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询
        result_dict = {}
        for row in results:
            user_id = row['userId']
            dress_id = row['dressId']
            category = row['category']
            valid_day = row['validDay']

            if user_id not in result_dict:
                result_dict[user_id] = {}
            if dress_id not in result_dict[user_id]:
                result_dict[user_id][dress_id] = {}

            # 如果相同装扮已存在，累计有效期；否则直接设置
            if category in result_dict[user_id][dress_id]:
                result_dict[user_id][dress_id][category] += valid_day
            else:
                result_dict[user_id][dress_id][category] = valid_day

        return result_dict

    def _batch_query_medal_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询勋章奖励
        """
        if not user_ids:
            return {}

        placeholders = ', '.join(['%s'] * len(user_ids))
        query = f"""SELECT userId, medalId FROM `kong_test`.`user_medal` WHERE userId IN ({placeholders})"""
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询: {user_id: {medal_id: True}}
        result_dict = {}
        for row in results:
            user_id = row['userId']
            medal_id = row['medalId']

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

        placeholders = ', '.join(['%s'] * len(user_ids))
        query = f"""
            SELECT userId, honorTitleId, timestampdiff(day, valid, expire) as validDay 
            FROM `kong_test`.`user_honor_title` 
            WHERE userId IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询: {user_id: {title_id: valid_days}}
        result_dict = {}
        for row in results:
            user_id = row['userId']
            title_id = row['honorTitleId']
            valid_day = row['validDay']

            if user_id not in result_dict:
                result_dict[user_id] = {}
            result_dict[user_id][title_id] = valid_day

        return result_dict

    def _batch_query_noble_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询贵族奖励
        """
        if not user_ids:
            return {}

        placeholders = ', '.join(['%s'] * len(user_ids))
        query = f"""
            SELECT userId, noblemanId, 
                   timestampdiff(day, FROM_UNIXTIME(noblemanValid), FROM_UNIXTIME(noblemanExpire)) as validDay 
            FROM `kong_test`.`user_nobleman_level` 
            WHERE userId IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询: {user_id: {nobleman_id: valid_days}}
        result_dict = {}
        for row in results:
            user_id = row['userId']
            nobleman_id = row['noblemanId']
            valid_day = row['validDay']

            if user_id not in result_dict:
                result_dict[user_id] = {}
            result_dict[user_id][nobleman_id] = valid_day

        return result_dict

    def _batch_query_vip_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询会员奖励
        """
        if not user_ids:
            return {}

        placeholders = ', '.join(['%s'] * len(user_ids))
        query = f"""
            SELECT userId, isVip, isSuperVip, 
                   timestampdiff(day, FROM_UNIXTIME(vipValid/1000), FROM_UNIXTIME(vipExpire/1000)) as vipValidDay,
                   timestampdiff(day, FROM_UNIXTIME(superVipValid/1000), FROM_UNIXTIME(superVipExpire/1000)) as superVipValidDay
            FROM `kong_test`.`user` 
            WHERE userId IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询: {user_id: {'Vip': {'valid': bool, 'valid_days': int}, 'SuperVip': {'valid': bool, 'valid_days': int}}}
        result_dict = {}
        for row in results:
            user_id = row['userId']
            result_dict[user_id] = {
                'Vip': {
                    'valid': bool(row['isVip']),
                    'valid_days': row['vipValidDay']
                },
                'SuperVip': {
                    'valid': bool(row['isSuperVip']),
                    'valid_days': row['superVipValidDay']
                }
            }

        return result_dict

    def _batch_query_nice_number_rewards(self, user_ids: List[int]) -> Dict:
        """
        批量查询靓号奖励
        """
        if not user_ids:
            return {}

        placeholders = ', '.join(['%s'] * len(user_ids))
        query = f"""
            SELECT userId, giftId 
            FROM `kong_test`.`user_gift` 
            WHERE userId IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(user_ids))

        # 整理结果为字典便于查询: {user_id: {gift_id: True}}
        result_dict = {}
        for row in results:
            user_id = row['userId']
            gift_id = row['giftId']

            if user_id not in result_dict:
                result_dict[user_id] = {}
            result_dict[user_id][gift_id] = True

        return result_dict

    @staticmethod
    def _batch_validate_single_reward(user_id: int, reward_type: int, reward_id: int,
                                      valid_days: int, reward_desc: str, dress_results: Dict,
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

            # 装扮奖励（头像框、座驾等）
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
                if valid_days > 0:
                    actual_expire = user_dresses[reward_id][dress_type]
                    if abs(actual_expire - valid_days) > 0:
                        return False, f"{reward_desc}装扮有效期不匹配, 实际有效期: {actual_expire} != {valid_days}"

                return True, f"{reward_desc}装扮验证通过"

            # 荣誉称号
            elif reward_type == 15:
                user_titles = title_results.get(user_id, {})
                if reward_id not in user_titles:
                    return False, f"荣誉称号 {reward_id} 未下发或已过期"

                # 验证有效期
                if valid_days > 0:
                    actual_expire = user_titles[reward_id]
                    if abs(actual_expire - valid_days) > 0:
                        return False, f"荣誉称号有效期不匹配, 实际有效期: {actual_expire} != {valid_days}"

                return True, "荣誉称号验证通过"

            # 贵族奖励
            elif reward_type in {16, 17}:
                nobleman_id = 7 if reward_type == 16 else 4
                noble_type = '公爵' if nobleman_id == 7 else '子爵'

                user_nobles = noble_results.get(user_id, {})
                if nobleman_id not in user_nobles:
                    return False, f"{noble_type}贵族未下发或已过期"

                # 验证有效期
                if valid_days > 0:
                    actual_expire = user_nobles[nobleman_id]
                    if abs(actual_expire - valid_days) > 0:
                        return False, f"{noble_type}贵族有效期不匹配, 实际有效期: {actual_expire} != {valid_days}"

                return True, f"{noble_type}贵族验证通过"

            # VIP奖励
            elif reward_type == 4:
                user_vip = vip_results.get(user_id, {})
                if 'Vip' not in user_vip or not user_vip['Vip'].get('valid'):
                    return False, "VIP未下发"

                # 验证有效期
                if valid_days > 0:
                    actual_expire = user_vip['Vip'].get('valid_days', 0)
                    if abs(actual_expire - valid_days) > 0:
                        return False, "VIP有效期不匹配, 实际有效期: {actual_expire} != {valid_days}"

                return True, "VIP验证通过"

            # 超级VIP奖励
            elif reward_type == 5:
                user_vip = vip_results.get(user_id, {})
                if 'SuperVip' not in user_vip or not user_vip['SuperVip'].get('valid'):
                    return False, "超级VIP未下发"

                # 验证有效期
                if valid_days > 0:
                    actual_expire = user_vip['SuperVip'].get('valid_days', 0)
                    if abs(actual_expire - valid_days) > 0:
                        return False, "超级VIP有效期不匹配, 实际有效期: {actual_expire} != {valid_days}"

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

            # 5、定时任务与榜单类型的映射
            task_rank_type_map = {}
            new_scheduled_tasks = []
            for task in scheduled_tasks:
                task_name = task['taskName']
                task_id = task['taskId']
                task_rank_type_map[task_id] = []
                # 根据taskId后缀匹配
                if '@ACTIVITY_DAY_END' in task_id:
                    # 日榜任务
                    for k, v in self.rank_mapping.items():
                        if '日榜' in v:
                            task_rank_type_map[task_id].append(k)
                elif '@ACTIVITY_END' in task_id:
                    # 总榜任务
                    for k, v in self.rank_mapping.items():
                        if '总榜' in v:
                            task_rank_type_map[task_id].append(k)

                # 匹配到榜单类型
                if task_rank_type_map[task_id]:
                    new_scheduled_tasks.append(task)
                else:
                    self.logger.warning(f"无法识别定时任务 {task_name} 对应的榜单")

            # 6、执行定时任务和验证
            all_tasks_successful = True
            all_validation_result = []
            for task in new_scheduled_tasks:
                task_id = task['taskId']
                task_name = task['taskName']

                # 获取当前任务对应的榜单类型
                rank_types = task_rank_type_map.get(task_id)
                if not rank_types:
                    self.logger.warning(f"无法识别定时任务 {task_name} 对应的榜单类型，跳过执行")
                    continue
                rank_type_names = [self.rank_mapping.get(rank_type) for rank_type in rank_types]

                # 6.1、获取活动榜单数据 - 用户排名及对应奖励
                self.logger.info(f"获取 {'、'.join(rank_type_names)} 榜单数据")
                ranking_data = self.get_activity_ranking_data(filter_rank_types = rank_types)

                # 6.2、执行任务前清除榜单中用户奖励
                self.logger.info(f"清除 {'、'.join(rank_type_names)} 下发奖励前已有的装扮、荣誉称号、勋章、贵族、会员/超级会员、靓号")
                self.clear_user_rewards(ranking_data, activity_reward_config_doc, rank_types)

                # 6.3、执行定时任务
                self.logger.info(f"开始执行定时任务: {task_name}")
                if not self.execute_scheduled_task(task):
                    self.logger.error(f"定时任务 {task_name} 执行失败，跳过该榜单验证")
                    all_tasks_successful = False
                    continue

                # 6.4、验证榜单奖励下发情况
                self.logger.info(f"开始验证 {'、'.join(rank_type_names)} 奖励下发情况")
                validation_result = self.validate_reward_distribution(ranking_data, activity_reward_config_doc, rank_types)
                all_validation_result.append(validation_result)
                self.logger.info(f"{'、'.join(rank_type_names)}奖励验证完成")
                self.logger.info("-" * 50)

            # 7、汇总验证结果
            if all_validation_result:
                # 计算汇总统计信息
                total_users = sum(len(result.get('total_users', [])) for result in all_validation_result)
                total_correct_users = sum(
                    len(result.get('users_with_correct_rewards', [])) for result in all_validation_result)
                total_incorrect_users = sum(
                    len(result.get('users_with_incorrect_rewards', [])) for result in all_validation_result)
                total_without_rewards = sum(
                    len(result.get('users_without_rewards', [])) for result in all_validation_result)

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
                    for user_validation in result.get('reward_validation_details', []):
                        for reward_validation in user_validation['validation_results']:
                            if not reward_validation['is_valid']:
                                reward_type = reward_validation['reward_type']
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
    validator = ActivityRewardVerification(
        activity_number = 1059,
        activity_config_path = 'test_activity/2026_goddess_day_reward_config.yaml',
        rank_mapping = {
            308: "乘风破浪（总榜）",
        }
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
