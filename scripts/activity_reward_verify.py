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
from typing import Dict, List, Any

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

    def __init__(self, activity_number: int, activity_config_path: str, rank_mapping: Dict[str, int]):
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

    def get_activity_reward_config_doc(self, activity_config_path: str) -> List[Dict[str, Any]]:
        """
        获取活动文档中的奖励配置

        Args:
            activity_config_path: 活动奖励配置文件路径

        Returns:
            dict: 奖励配置
        """
        self.logger.info("获取活动文档中的奖励配置")
        activity_reward_config = self.filehandler.read_yaml(activity_config_path)
        self.logger.info(f"文档配置: {activity_reward_config}")
        return activity_reward_config

    def get_activity_reward_config_db(self) -> List[Dict[str, Any]]:
        """
        获取数据库中的奖励配置, 并根据服务端映射处理奖励类型

        Returns:
            List[Dict]: 处理后的奖励配置列表
        """
        self.logger.info("获取数据库中的奖励配置")

        # 查询数据库中的奖励配置
        query = """
            SELECT activityType, rankNumber, rewardType, rewardId, rewardCount FROM `kong_test`.`reward_option_config` 
            WHERE activityNumber = %s
        """
        rewards = self.db.execute_query(query, (self.activity_number,))

        if not rewards:
            self.logger.warning(f"未找到活动 {self.activity_number} 的奖励配置")
            return []

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
                    query_key = f"{activityType_doc}_{rank_doc}_{rewardType_doc}"
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

            # 构造查询key, 通过两个查询key进行匹配
            query_key = f"{activityType_db}_{rankNumber_db}_{rewardType_db}"

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
            if rewardType_db in [1, 6]:
                if rewardCount_db == 1:
                    # self.logger.info(f"跳过有效期验证 - 奖励: {doc_info["rewardType_desc_doc"]} (Type={rewardType_db}) | 榜单: {doc_info['activityType_name_doc']} | 排名: {rankNumber_db} | 文档有效期: {doc_info['valid_days_doc']} | 数据库数量: {rewardCount_db}个")
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

    def get_activity_ranking_data(self) -> List[Dict]:
        """
        获取活动榜单数据 - 用户排名及对应奖励
        Returns:
            List[Dict]: 格式化后的榜单数据
        """
        # 从奖励配置文档读取榜单信息
        activity_reward_config = self.get_activity_reward_config_doc(self.activity_config_path)

        all_ranked_data = []  # 收集所有榜单数据

        # 遍历所有榜单配置
        for config in activity_reward_config:
            rank_category = config.get('rank_category', '0')
            activity_type_name = config.get('activityType_name', '')
            rank_type = config.get('activityType', 0)
            rank_coverage = config.get('rank_coverage', 10)

            # 根据activityType_name判断榜单类型
            if '日榜' in activity_type_name:
                # 日榜的stage设为当前日期的前一天
                stage = util.format_time(util.get_time_delta(days = -1), format_str = '%Y%m%d')
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
                    self.logger.info(f"成功获取到 {len(ranked_data)} 条榜单数据, 排名范围: 1-{rank_coverage}")
                    # 将当前配置的数据添加到总结果中
                    all_ranked_data.extend(ranked_data)
                else:
                    self.logger.warning(f"没有获取到榜单数据, 跳过处理")

            except Exception as e:
                self.logger.error(f"获取活动榜单数据失败: {str(e)}")
                # 继续处理下一个配置，而不是抛出异常
                continue

        self.logger.info(f"总共获取到 {len(all_ranked_data)} 条榜单数据")
        return all_ranked_data

    def _query_ranking_data(self, rank_category: str, stage: str, rank_coverage: int) -> List[Dict]:
        """查询榜单数据
        Args:
            rank_category: 榜单分类
            stage: 活动阶段(赛段/日期), 默认前一天
            rank_coverage: 要获取的榜单Top N用户, 默认10

        Returns:
            List[Dict]: 格式化后的榜单数据
        """
        # 查询数据并按value降序排列
        query = f"""
                SELECT number, userId, intimateId, category, stage, year, month, day, value
                FROM `kong_test`.`activity_rank` 
                WHERE number = %s and category = %s and stage = %s
                ORDER BY value DESC LIMIT {rank_coverage}
            """

        raw_data = self.db.execute_query(query, (self.activity_number, rank_category, stage))
        return raw_data

    def _insert_test_ranking_data(self, ranking_category: str, stage: str, count: int) -> int:
        """插入测试榜单数据
        Args:
            ranking_category: 榜单分类
            stage: 活动阶段(赛段/日期), 默认前一天, 20260119表示日榜
            count: 要插入的测试数据数量
        Returns:
            int: 成功插入的测试数据数量
        """
        # 从满足条件的榜单数据中取一条数据作为模板
        inserted_count = 0

        existing_users_query = f"""
                    SELECT * FROM `kong_test`.`activity_rank` 
                    WHERE number = {self.activity_number} 
                    and category = '{ranking_category}' 
                    order by id desc
                """
        existing_users = self.db.execute_query(existing_users_query)
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
        if existing_user_pairs:
            pairs_str = ', '.join([f'({user_id}, {intimate_id})' for user_id, intimate_id in existing_user_pairs])
            not_in_condition = f'and (userId, intimateId) not in ({pairs_str})'
        else:
            not_in_condition = ''
        other_stage_query = f"""
                        SELECT * FROM `kong_test`.`activity_rank` 
                        WHERE number = {self.activity_number} 
                        and category = '{ranking_category}' 
                        {'and day = -1' if len(stage) == 8 else 'and day != -1'}
                        {not_in_condition}
                        ORDER BY id DESC
                        LIMIT {count}
                   """
        other_stage_data = self.db.execute_query(other_stage_query)

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
                            template_data['value'], template_data['value1'], template_data['value2'],
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
            random_users_query = f"""
                   SELECT userid FROM `kong_test`.`user` 
                   WHERE status = 0 and role = 5 
                   and userid NOT IN ({','.join(map(str, existing_user_ids)) if existing_user_ids else '0'})
                   ORDER BY lastLoginDate desc
                   LIMIT {remaining_count * 2}
               """
            random_users = self.db.execute_query(random_users_query)

            for i in range(remaining_count):
                if template_data['userId'] == template_data['intimateId']:  # 单人榜
                    user_id = random_users[i]['userid']
                    intimate_id = user_id
                else:  # 双人榜
                    # 生成唯一的用户对
                    max_attempts = 3  # 最多尝试3次
                    for attempt in range(max_attempts):
                        user_id = random_users[i]['userid']
                        intimate_id = random_users[remaining_count + i]['userid']

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
        """处理榜单数据（单人和双人分别处理）"""
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

    def get_expected_rewards_by_ranking(self, ranking: int, activity_type: int, activity_reward_config: List[
        Dict[str, Any]]) -> \
            List[Dict]:
        """
        根据排名获取应得的奖励配置

        Args:
            ranking: 排名
            activity_type: 榜单类型
            activity_reward_config: 活动奖励配置

        Returns:
            List[Dict]: 应得的奖励列表
        """
        expected_rewards = []
        self.logger.info(f"查找排名 {ranking} 在榜单类型 {activity_type} 的奖励配置")
        # 查找对应榜单类型的配置
        config_found = False
        for config in activity_reward_config:
            config_activity_type = config.get('activityType')
            self.logger.debug(f"检查配置: activityType={config_activity_type}, 目标activityType={activity_type}")

            # 确保类型一致，都转换为int进行比较
            if int(config_activity_type) == int(activity_type):
                config_found = True
                self.logger.debug(f"找到匹配的榜单类型配置: {config.get('activityType_name', '未知榜单')}")

                # 查找对应排名的奖励配置
                reward_details = config.get('reward_details', [])
                self.logger.debug(f"该榜单有 {len(reward_details)} 个排名配置")

                # 使用字典映射代替线性查找，减少日志输出
                reward_detail_dict = {int(rd.get('rank')): rd for rd in reward_details}

                if int(ranking) in reward_detail_dict:
                    reward_detail = reward_detail_dict[int(ranking)]
                    rewards = reward_detail.get('rewards', [])
                    expected_rewards.extend(rewards)
                    self.logger.info(f"找到排名 {ranking} 的奖励配置，共 {len(rewards)} 个奖励")
                else:
                    self.logger.warning(f"在榜单类型 {activity_type} 中未找到排名 {ranking} 的奖励配置")
                    # 列出该榜单所有可用的排名
                    available_ranks = sorted(reward_detail_dict.keys())
                    self.logger.warning(f"该榜单可用的排名: {available_ranks}")
                break

        if not config_found:
            self.logger.warning(f"未找到榜单类型 {activity_type} 的配置")
            # 列出所有可用的榜单类型
            available_activity_types = [cfg.get('activityType') for cfg in activity_reward_config]
            self.logger.warning(f"可用的榜单类型: {available_activity_types}")

        self.logger.info(f"获取排名 {ranking} 应下发的奖励: {expected_rewards}")
        return expected_rewards

    def clear_user_rewards(self, ranking_data: List[Dict], activity_reward_config: List[Dict[str, Any]]) -> None:
        """
        清除榜单用户奖励 - 初步方案: 直接全部清除

        Args:
            ranking_data: 榜单数据
            activity_reward_config: 活动奖励配置
        """
        # 缓存已查找过的奖励配置(ranking, activity_type)
        reward_cache = {}

        # 清除用户奖励
        for user_data in ranking_data:
            user_id = user_data.get('user_id')
            ranking = user_data.get('ranking')
            activity_type = user_data.get('rank_type')

            # 检查缓存中是否已有该排名和榜单类型的奖励配置
            cache_key = (ranking, activity_type)
            if cache_key in reward_cache:
                expected_rewards = reward_cache[cache_key]
                self.logger.debug(f"使用缓存的奖励配置: 排名{ranking}, 榜单类型{activity_type}")
            else:
                # 获取用户应得奖励
                expected_rewards = self.get_expected_rewards_by_ranking(ranking, activity_type, activity_reward_config)
                # 将结果存入缓存
                reward_cache[cache_key] = expected_rewards
    
            if not expected_rewards:
                self.logger.warning(f"用户 {user_id} 排名 {ranking} 未找到对应的奖励配置")
                continue

            self.logger.info(f"清除用户 {user_id} (排名 {ranking}) 的已有奖励")
            # 根据应得奖励类型进行精确清理
            for reward in expected_rewards:
                reward_type = reward.get('rewardType')
                reward_id = reward.get('rewardId')
                reward_desc = reward.get('reward_desc')
    
                if reward_type == 1:  # 勋章
                    self._clear_user_medal(user_id, reward_id)
                elif reward_type == 2:  # 头像框
                    self._clear_user_dress(user_id, reward_id, reward_desc)
                elif reward_type == 3:  # 座驾
                    self._clear_user_dress(user_id, reward_id, reward_desc)
                elif reward_type == 4:  # 会员
                    self._clear_user_vip(user_id, 'Vip')
                elif reward_type == 5:  # 超级会员
                    self._clear_user_vip(user_id, 'SuperVip')
                elif reward_type == 6:  # 靓号
                    self._clear_user_bright_number(user_id, reward_id, reward_desc)
                elif reward_type == 9:  # 房间气泡
                    self._clear_user_dress(user_id, reward_id, reward_desc)
                elif reward_type == 10:  # 主页特效
                    self._clear_user_dress(user_id, reward_id, reward_desc)
                elif reward_type == 12:  # 私聊气泡
                    self._clear_user_dress(user_id, reward_id, reward_desc)
                elif reward_type == 14:  # 进场特效
                    self._clear_user_dress(user_id, reward_id, reward_desc)
                elif reward_type == 15:  # 荣誉称号
                    self._clear_user_title(user_id, reward_id)
                elif reward_type == 16:  # 公爵贵族
                    self._clear_user_noble(user_id, 7)
                elif reward_type == 17:  # 子爵贵族
                    self._clear_user_noble(user_id, 4)

    def _clear_user_dress(self, user_id: int, dress_id: int, dress_type_name: str):
        """清除用户装扮"""
        query = "DELETE FROM `kong_test`.`user_dress` WHERE userId = %s and dressId = %s"
        self.db.execute_update(query, (user_id, dress_id,))
        self.logger.debug(f"清除用户 {user_id} 的{dress_type_name}装扮 {dress_id}")

    def _clear_user_medal(self, user_id: int, medal_id: int):
        """清除用户勋章"""
        query = "DELETE FROM `kong_test`.`user_medal` WHERE userId = %s and medalId = %s"
        self.db.execute_update(query, (user_id, medal_id))
        self.logger.debug(f"清除用户 {user_id} 的勋章 {medal_id}")

    def _clear_user_title(self, user_id: int, title_id: int):
        """清除用户荣誉称号"""
        query = "DELETE FROM `kong_test`.`user_title` WHERE userId = %s and titleId = %s"
        self.db.execute_update(query, (user_id, title_id))
        self.logger.debug(f"清除用户 {user_id} 的荣誉称号 {title_id}")

    def _clear_user_noble(self, user_id: int, nobleman_id: int):
        """清除用户贵族身份 - 设置为过期状态"""
        noble_type = '公爵' if nobleman_id == 7 else '子爵'
        query = "UPDATE `kong_test`.`user_nobleman_level` SET isNobleman = 0, noblemanExpire = DATE_SUB(NOW(), INTERVAL 1 DAY) WHERE userId = %s and noblemanId = %s"

        self.db.execute_update(query, (user_id, nobleman_id,))
        self.logger.debug(f"设置用户 {user_id} 的{noble_type}贵族为过期状态")

    def _clear_user_vip(self, user_id: int, vip_type: str):
        """清除用户会员身份 - 设置为过期状态"""
        if vip_type == 'Vip':
            query = "UPDATE `kong_test`.`user` SET isVip = 0, vipExpire = DATE_SUB(NOW(), INTERVAL 1 DAY) WHERE userId = %s"
        elif vip_type == 'SuperVip':
            query = "UPDATE `kong_test`.`user` SET isSuperVip = 0, superVipExpire = DATE_SUB(NOW(), INTERVAL 1 DAY) WHERE userId = %s"
        else:
            return

        self.db.execute_update(query, (user_id,))
        self.logger.debug(f"设置用户 {user_id} 的{vip_type}为过期状态")

    def _clear_user_bright_number(self, user_id: int, reward_id: int, reward_desc: str):
        """清除用户靓号"""
        query = "DELETE FROM `kong_test`.`user_gift` WHERE userId = %s and giftId = %s"
        self.db.execute_update(query, (user_id, reward_id,))
        self.logger.debug(f"清除用户 {user_id} 的{reward_desc}")

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
    def validate_reward_distribution(self, ranking_data: List[Dict], activity_reward_config: List[Dict[str, Any]]) -> \
            Dict[str, Any]:
        """
        验证奖励下发情况

        Args:
            ranking_data: 榜单数据
            activity_reward_config: 活动奖励配置

        Returns:
            Dict: 验证结果
        """
        self.logger.info("开始验证奖励下发情况")

        # 按用户ID分组, 处理同一用户在多个榜单的情况
        user_rewards_map = {}

        for user_data in ranking_data:
            user_id = user_data.get('user_id')
            ranking = user_data.get('ranking')
            rank_type_name = user_data.get('rank_type_name')
            activity_type = self.rank_mapping.get(rank_type_name)

            # 获取用户应得奖励
            expected_rewards = self.get_expected_rewards_by_ranking(ranking, activity_type, activity_reward_config)
            if not expected_rewards:
                continue

            # 按用户ID聚合奖励
            if user_id not in user_rewards_map:
                user_rewards_map[user_id] = {
                    'user_id': user_id,
                    'rewards': [],
                    'rankings': [],
                    'activity_types': set()
                }

            user_rewards_map[user_id]['rewards'].extend(expected_rewards)
            user_rewards_map[user_id]['rankings'].append(ranking)
            user_rewards_map[user_id]['activity_types'].add(activity_type)

        validation_result = {
            "total_users": len(user_rewards_map),
            "users_with_correct_rewards": 0,
            "users_with_incorrect_rewards": 0,
            "users_without_rewards": 0,
            "distribution_details": [],
            "reward_validation_details": []
        }

        # 验证每个用户的奖励下发情况
        for user_info in user_rewards_map.values():
            user_id = user_info['user_id']
            rewards = user_info['rewards']
            rankings = user_info['rankings']
            activity_types = user_info['activity_types']

            self.logger.info(f"验证用户 {user_id} 的奖励下发情况（在 {len(rankings)} 个榜单中, 排名: {rankings}）")

            # 去重处理：同一用户可能在不同榜单获得相同奖励
            unique_rewards = {}
            for reward in rewards:
                reward_key = f"{reward['rewardType']}_{reward['rewardId']}"
                if reward_key not in unique_rewards:
                    unique_rewards[reward_key] = reward
                else:
                    # 如果同一奖励在多个榜单出现, 取最长的有效期
                    existing_reward = unique_rewards[reward_key]
                    if reward.get('valid_days', 0) > existing_reward.get('valid_days', 0):
                        unique_rewards[reward_key] = reward

            user_validation = {
                "user_id": user_id,
                "rankings": rankings,
                "activity_types": list(activity_types),
                "expected_rewards": list(unique_rewards.values()),
                "actual_rewards": [],
                "validation_results": [],
                "all_correct": True
            }

            # 验证每个应得奖励是否已正确下发
            for expected_reward in unique_rewards.values():
                reward_type = expected_reward.get('rewardType')
                reward_id = expected_reward.get('rewardId')
                valid_days = expected_reward.get('valid_days')
                reward_desc = expected_reward.get('reward_desc')

                # 验证奖励是否已下发
                is_valid, validation_msg = self._validate_single_reward(user_id, reward_type, reward_id, valid_days, reward_desc)

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
            if user_validation["all_correct"]:
                validation_result["users_with_correct_rewards"] += 1
                user_validation["status"] = "correct"
            else:
                validation_result["users_with_incorrect_rewards"] += 1
                user_validation["status"] = "incorrect"
            validation_result["reward_validation_details"].append(user_validation)

        # 输出验证摘要
        self.logger.info("=== 奖励下发验证结果 ===")
        self.logger.info(f"总用户数: {validation_result['total_users']}")
        self.logger.info(f"奖励下发正确的用户: {validation_result['users_with_correct_rewards']}")
        self.logger.info(f"奖励下发错误的用户: {validation_result['users_with_incorrect_rewards']}")
        self.logger.info(f"无奖励配置的用户: {validation_result['users_without_rewards']}")

        return validation_result

    def _validate_single_reward(self, user_id: int, reward_type: int, reward_id: int, valid_days: int, reward_desc: str) -> \
            tuple[bool, str]:
        """
        验证单个奖励的下发情况

        Returns:
            tuple[bool, str]: (是否验证通过, 验证消息)
        """
        try:
            if reward_type == 1:  # 勋章
                return self._validate_medal_reward(user_id, reward_id)
            elif reward_type == 2:  # 头像框
                return self._validate_dress_reward(user_id, reward_id, 2, reward_desc, valid_days)
            elif reward_type == 3:  # 座驾
                return self._validate_dress_reward(user_id, reward_id, 1, reward_desc, valid_days)
            elif reward_type == 4:  # 会员
                return self._validate_vip_reward(user_id, 'Vip', valid_days)
            elif reward_type == 5:  # 超级会员
                return self._validate_vip_reward(user_id, 'SuperVip', valid_days)
            elif reward_type == 6:  # 靓号
                return self._validate_nice_number_reward(user_id, reward_id, reward_desc)
            elif reward_type == 9:  # 房间聊天气泡
                return self._validate_dress_reward(user_id, reward_id, 4, reward_desc, valid_days)
            elif reward_type == 10:  # 主页特效
                return self._validate_dress_reward(user_id, reward_id, 5, reward_desc, valid_days)
            elif reward_type == 12:  # 私聊气泡
                return self._validate_dress_reward(user_id, reward_id, 3, reward_desc, valid_days)
            elif reward_type == 14:  # 进场特效
                return self._validate_dress_reward(user_id, reward_id, 6, reward_desc, valid_days)
            elif reward_type == 15:  # 荣誉称号
                return self._validate_title_reward(user_id, reward_id, valid_days)
            elif reward_type == 16:  # 公爵贵族
                return self._validate_noble_reward(user_id, 7, valid_days)
            elif reward_type == 17:  # 子爵贵族
                return self._validate_noble_reward(user_id, 4, valid_days)
            else:
                return False, f"未知奖励类型: {reward_type}"
        except Exception as e:
            return False, f"验证过程中发生错误: {str(e)}"

    def _validate_dress_reward(self, user_id: int, dress_id: int, dress_type: int, dress_type_name: str, valid_days: int) -> \
            tuple[bool, str]:
        """验证装扮奖励"""
        query = """
            SELECT userid, dressId, timestampdiff(day, FROM_UNIXTIME(valid/1000), FROM_UNIXTIME(expire/1000)) as validDay FROM `kong_test`.`user_dress` 
            WHERE userId = %s and dressId = %s and category = %s
        """
        result = self.db.get_one(query, (user_id, dress_id, dress_type))

        if not result:
            return False, f"{dress_type_name}装扮 {dress_id} 未下发或已过期"

        # 验证有效期
        if valid_days > 0:
            actual_expire = result.get('validDay')
            if abs(actual_expire - valid_days) > 0:
                return False, f"{dress_type_name}装扮有效期不匹配"

        return True, f"{dress_type_name}装扮验证通过"

    def _validate_medal_reward(self, user_id: int, medal_id: int) -> tuple[bool, str]:
        """验证勋章奖励"""
        query = "SELECT * FROM `kong_test`.`user_medal` WHERE userId = %s and medalId = %s"
        result = self.db.get_one(query, (user_id, medal_id))

        if not result:
            return False, f"勋章 {medal_id} 未下发"

        return True, "勋章验证通过"

    def _validate_title_reward(self, user_id: int, title_id: int, valid_days: int) -> tuple[bool, str]:
        """验证荣誉称号奖励"""
        query = """
            SELECT userid, honorTitleId, timestampdiff(day, valid, expire) as validDay FROM `kong_test`.`user_title` 
            WHERE userId = %s and honorTitleId = %s 
        """
        result = self.db.get_one(query, (user_id, title_id))

        if not result:
            return False, f"荣誉称号 {title_id} 未下发或已过期"

        # 验证有效期
        if valid_days > 0:
            actual_expire = result.get('validDay')
            if abs(actual_expire - valid_days) > 0:
                return False, f"荣誉称号有效期不匹配"

        return True, "荣誉称号验证通过"

    def _validate_noble_reward(self, user_id: int, nobleman_id: int, valid_days: int) -> tuple[bool, str]:
        """验证贵族奖励"""
        noble_type = '公爵' if nobleman_id == 7 else '子爵'

        query = f"SELECT userId, noblemanId, timestampdiff(day, FROM_UNIXTIME(noblemanValid), FROM_UNIXTIME(noblemanExpire)) as validDay FROM `kong_test`.`user_nobleman_level` WHERE userId = %s and noblemanId = %s"
        result = self.db.get_one(query, (user_id, nobleman_id,))

        if not result:
            return False, f"{noble_type}贵族未下发或已过期"

        # 验证有效期
        if valid_days > 0:
            actual_expire = result.get('validDay')
            if abs(actual_expire - valid_days) > 0:
                return False, f"{noble_type}贵族有效期不匹配"

        return True, f"{noble_type}贵族验证通过"

    def _validate_vip_reward(self, user_id: int, vip_type: str, valid_days: int) -> tuple[bool, str]:
        """验证会员奖励"""
        if vip_type == 'Vip':
            query = "SELECT userId, isVip as valid, timestampdiff(day, FROM_UNIXTIME(vipValid/1000), FROM_UNIXTIME(vipExpire/1000)) as validDay FROM `kong_test`.`user` WHERE userId = %s"
        elif vip_type == 'SuperVip':
            query = "SELECT userId, isSuperVip as valid, timestampdiff(day, FROM_UNIXTIME(superVipValid/1000), FROM_UNIXTIME(superVipExpire/1000)) as validDay FROM `kong_test`.`user` WHERE userId = %s"
        else:
            return False, f"未知会员类型: {vip_type}"

        result = self.db.get_one(query, (user_id,))

        if not result:
            return False, f"{vip_type}未下发或已过期"

        # 验证有效期
        if valid_days > 0:
            valid = result.get('valid')
            actual_expire = result.get('validDay')
            if valid == 0:
                return False, f"{vip_type}未下发"
            elif valid == 1 and abs(actual_expire - valid_days) > 0:
                return False, f"{vip_type}有效期不匹配"

        return True, f"{vip_type}验证通过"

    def _validate_nice_number_reward(self, user_id: int, reward_id: int, reward_desc: str) -> tuple[bool, str]:
        """验证靓号奖励"""
        query = "SELECT * FROM `kong_test`.`user_gift` WHERE userId = %s and giftId = %s"
        result = self.db.get_one(query, (user_id, reward_id,))

        if not result:
            return False, f"{reward_desc} - {reward_id} 未下发"

        return True, f"{reward_desc}验证通过"

    def validate(self):
        """
        执行完整的奖励验证流程

        Returns:
            bool: 验证是否通过
        """
        self.logger.info("=== 开始活动榜单奖励验证 ===")

        try:
            # 1、获取活动文档中的奖励配置
            activity_reward_config_doc = self.get_activity_reward_config_doc(self.activity_config_path)

            # 2、获取数据库表中的奖励配置
            activity_reward_config_db = self.get_activity_reward_config_db()

            # 3、比较奖励配置是否一致
            self.verify_db_vs_doc(activity_reward_config_doc, activity_reward_config_db)

            # 4、获取活动榜单数据 - 用户排名及对应奖励
            ranking_data = self.get_activity_ranking_data()

            # 5、清除下发奖励前已有的装扮、荣誉称号、勋章、贵族、会员/超级会员、靓号
            self.clear_user_rewards(ranking_data, activity_reward_config_doc)

            # 6、获取活动定时任务
            scheduled_tasks = self.get_scheduled_tasks()
            # 7、开始执行定时任务, 下发奖励
            for task in scheduled_tasks:
                if not self.execute_scheduled_task(task):
                    continue
                # 8、定时任务执行成功判断用户所有奖励是否下发, 下发时长是否正确
                if ranking_data:
                    validation_result = self.validate_reward_distribution(ranking_data, activity_reward_config_doc)
                    if validation_result.get('users_with_incorrect_rewards') != 0:
                        self.logger.error(f"存在用户奖励下发错误: {validation_result.get('users_with_incorrect_rewards')}")
                        return False
                    if validation_result.get('users_without_rewards') != 0:
                        self.logger.error(f"存在用户奖励未下发: {validation_result.get('users_without_rewards')}")
                        return False
            return True

        except Exception as e:
            self.logger.error(f"验证过程中发生错误: {str(e)}")
            return False


def main():
    """主函数"""

    # 创建验证器
    validator = ActivityRewardVerification(
        activity_number = 1053,
        activity_config_path = 'test_activity/christmas_reward_config.yaml',
        rank_mapping = {
            "圣诞日榜": 81,
            "圣诞总榜": 82,
        }
    )

    # 执行验证
    success = validator.validate()
    return success


if __name__ == "__main__":
    main()

# Todo:
# 3、执行定时任务方法
# 4、补充完成奖励下发校验方法 - 根据排名获取应下发的奖励, 分别到不同数据库中去查询记录/有效期是否一致
