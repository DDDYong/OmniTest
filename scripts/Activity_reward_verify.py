"""
-------------------------------------------------
File:           Activity_reward_verify.py
Author:         duanyang
Date:           2026/1/4
-------------------------------------------------
Description:
活动榜单奖励下发验证模块
-------------------------------------------------
"""
import os
import sys
from typing import Dict, List, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config_manager import config_manager
from utils import logger, util
from utils.db.mysql_client import MySQLClient
from utils.file_util import FileHandler


class RewardTypeMapper:
    """
    活动奖励类型枚举
    """

    # 奖励类型枚举映射
    REWARD_TYPE_MAPPING = {
        0: {"name": "UNKNOWN", "desc": "未知"},
        1: {"name": "MEDAL", "desc": "勋章"},
        2: {"name": "AVATAR_COVER", "desc": "头像框"},
        3: {"name": "RIDE", "desc": "座驾"},
        4: {"name": "VIP", "desc": "会员"},
        5: {"name": "SUPER_VIP", "desc": "超级会员"},
        6: {"name": "BRIGHT_NUMBER", "desc": "靓号", "extend": {
            746: "五位自选靓号",
            1357: "六位自选靓号",
            1001620: "七位靓号"
        }},
        7: {"name": "GIFT", "desc": "礼物"},
        8: {"name": "CUSTOM", "desc": "自定义"},
        9: {"name": "CHATROOM_BUBBLE", "desc": "房间聊天气泡"},
        10: {"name": "MAIN_PAGE_EFFECTS", "desc": "主页特效"},
        11: {"name": "ACTIVITY_VOTE", "desc": "活动票"},
        12: {"name": "IM_BUBBLE", "desc": "私聊气泡"},
        13: {"name": "SF_2024_DRAGON_COUPON", "desc": "龙珠"},
        14: {"name": "ENTER_EFFECTS", "desc": "进场特效"},
        15: {"name": "TITLE", "desc": "荣誉称号"},
        16: {"name": "DUKE_NOBLE", "desc": "公爵贵族"},
        17: {"name": "VISCOUNT_NOBLE", "desc": "子爵贵族体验卡"},
        99: {"name": "GAME", "desc": "游戏"}
    }

    @classmethod
    def get_reward_type_name(cls, reward_type: int) -> str:
        """根据奖励类型ID获取类型名称"""
        return cls.REWARD_TYPE_MAPPING.get(reward_type, {}).get("name", "UNKNOWN")

    @classmethod
    def get_reward_type_desc(cls, reward_type: int) -> str:
        """根据奖励类型ID获取类型描述"""
        return cls.REWARD_TYPE_MAPPING.get(reward_type, {}).get("desc", "未知奖励类型")

    @classmethod
    def validate_reward_type(cls, reward_type: int) -> bool:
        """验证奖励类型是否有效"""
        return reward_type in cls.REWARD_TYPE_MAPPING


class ActivityRewardVerification:
    """
    活动奖励验证模块
    """

    def __init__(self, activity_number: int, activity_config_path: str, scheduled_tasks: List[Dict[str, Any]]):
        """
        初始化活动奖励验证模块

        Args:
            activity_number: 活动ID
            activity_config_path: 活动奖励配置文件路径
        """
        self.activity_number = activity_number
        self.activity_config_path = activity_config_path
        self.scheduled_tasks = scheduled_tasks
        self.top_n = None

        self.logger = logger
        self.filehandler = FileHandler()
        self.db = MySQLClient(config_manager.get_mysql_config())
        self.reward_mapper = RewardTypeMapper()

    def get_activity_reward_config_doc(self, activity_config_path: str) -> List[Dict[str, Any]]:
        """
        获取活动文档中的奖励配置

        Args:
            activity_config_path: 活动奖励配置文件路径

        Returns:
            list: 奖励配置
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
            # 特殊处理：勋章(Type=1)和靓号(Type=6)是永久奖励，跳过有效期校验
            if rewardType_db in [1, 6]:
                if rewardCount_db == 1:
                    # self.logger.info(f"跳过有效期验证 - 奖励: {doc_info["rewardType_desc_doc"]} (Type={rewardType_db}) | 榜单: {doc_info['activityType_name_doc']} | 排名: {rankNumber_db} | 文档有效期: {doc_info['valid_days_doc']} | 数据库数量: {rewardCount_db}个")
                    continue
                else:
                    self.logger.error(f"奖励数量错误: {doc_info["rewardType_desc_doc"]} (Type={rewardType_db}) | 榜单: {doc_info['activityType_name_doc']} | 排名: {rankNumber_db} | 数据库数量: {rewardCount_db}个")
                    differences["reward_count_error"].append({
                        "shared_info": {
                            "activityType": activityType_db,
                            "activityType_name_doc": doc_info["activityType_name_doc"],
                            "rank": rankNumber_db,
                            "rewardType": rewardType_db,
                            "rewardType_name_doc": doc_info["rewardType_name_doc"],
                            "rewardType_desc_db": rewardType_desc_db,
                            "rewardType_desc_doc": doc_info["rewardType_desc_doc"],
                        },
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
                common = item["shared_info"]
                self.logger.error(f"榜单: {common['activityType_name_doc']} (Type={common['activityType']}) | 排名: {common['rank']} | 奖励类型: {common['rewardType_desc_doc']} (Type={common['rewardType']}) | 数据库数量: {item['rewardCount_db']}个 | 原因: {item['reason']}")

        # 有效期不匹配
        if differences["valid_days_mismatch"]:
            self.logger.info(f"[差异: 有效期不匹配] 共{len(differences['valid_days_mismatch'])}条")
            for item in differences["valid_days_mismatch"]:
                common = item["common_info"]
                self.logger.info(f"榜单: {common['activityType_name_doc']} (Type={common['activityType']}) | 排名: {common['rank']} | 奖励类型: {common['rewardType_desc_doc']} (Type={common['rewardType']}) | 文档有效期: {item['valid_days_doc (文档有效期)']}天 | 数据库有效期: {item['rewardCount_db (数据库有效期)']}天")

        # 数据库配置与文档一致
        if not any(differences.values()):
            self.logger.info("✅ 数据库配置所有奖励均在文档中存在, 且rewardId、有效期完全一致！")
        else:
            self.logger.warning(f"❌ 发现 {sum(len(v) for v in differences.values())} 条差异，请检查文档和数据库配置！")

        return differences

    def get_activity_ranking_data(self, ranking_category: str, ranking_day: int = -1, stage: str = util.format_time(util.get_time_delta(days = -1), format_str = "%Y%m%d"), top_n: int = 10) -> \
            List[Dict]:
        """
        获取活动榜单数据 - 用户排名及对应奖励
        Args:
            ranking_category: 榜单分类
            ranking_day: 榜单类型(日榜/总榜)，-1表示总榜，其他数字表示日榜
            stage: 活动阶段(赛段/日期)，默认前一天
            top_n: 要获取的榜单Top N用户，默认10

        Returns:
            List[Dict]: 格式化后的榜单数据
        """
        self.logger.info(f"获取活动榜单数据：活动ID={self.activity_number}, 分类={ranking_category}, 类型={ranking_day}, 阶段={stage}, TopN={top_n}")

        try:
            # 按条件查询榜单数据
            raw_data = self._query_ranking_data(ranking_category, ranking_day, stage, top_n)

            # 检查数据量是否足够
            if len(raw_data) < top_n:
                self.logger.warning(f"现有数据不足TopN({top_n})，当前只有{len(raw_data)}条，需要补足数据")
                missing_count = top_n - len(raw_data)

                # 插入缺少的数据
                inserted_count = self._insert_test_ranking_data(ranking_category, ranking_day, stage, missing_count)

                if inserted_count > 0:
                    self.logger.info(f"成功插入{inserted_count}条测试数据，重新查询榜单数据")
                    # 重新查询数据
                    raw_data = self._query_ranking_data(ranking_category, ranking_day, stage, top_n)
                else:
                    self.logger.warning("复制数据失败，使用现有数据进行处理")

            # 处理榜单数据并计算排名
            ranked_data = self._process_ranking_data(raw_data)
            self.logger.info(f"成功获取到 {len(ranked_data)} 条榜单数据，排名范围: 1-{len(ranked_data)}")

            return ranked_data

        except Exception as e:
            self.logger.error(f"获取活动榜单数据失败: {str(e)}")
            raise

    def _query_ranking_data(self, ranking_category: str, ranking_day: int, stage: str, top_n: int) -> List[Dict]:
        """查询榜单数据
        Args:
            ranking_category: 榜单分类
            ranking_day: 榜单类型(日榜/总榜)，-1表示总榜，其他数字表示日榜
            stage: 活动阶段(赛段/日期)，默认前一天
            top_n: 要获取的榜单Top N用户，默认10

        Returns:
            List[Dict]: 格式化后的榜单数据
        """
        # 构建查询条件
        query_conditions = [f"number = {self.activity_number}", f"category = '{ranking_category}'",
                            f"day = {ranking_day}"]

        # 添加活动阶段
        if stage:
            query_conditions.append(f"stage = '{stage}'")

        where_clause = " AND ".join(query_conditions)

        # 查询数据并按value降序排列
        query = f"""
                SELECT number, userId, intimateId, category, stage, year, month, day, value
                FROM `kong_test`.`activity_rank` 
                WHERE 1 = 1 {where_clause}
                ORDER BY value DESC LIMIT {top_n}
            """

        raw_data = self.db.execute_query(query)
        return raw_data

    def _check_user_in_ranking(self, user_id: str, imtimate_id: str, ranking_category: str, ranking_day: int, stage: str) -> bool:
        """检查用户是否已在榜单中

        Args:
            user_id: 用户ID
            imtimate_id: Partner用户ID
            ranking_category: 榜单分类
            ranking_day: 榜单类型(日榜/总榜)，-1表示总榜，其他数字表示日榜
            stage: 活动阶段(赛段/日期)，默认前一天

        Returns:
            bool: 用户是否已在榜单中
        """
        query_conditions = [
            f"number = {self.activity_number}",
            f"category = '{ranking_category}'",
            f"day = {ranking_day}",
            f"userId = {user_id}",
            f"intimateId = {imtimate_id}"
        ]

        if stage:
            query_conditions.append(f"stage = '{stage}'")

        where_clause = " AND ".join(query_conditions)

        query = f"""
               SELECT COUNT(*) as count 
               FROM `kong_test`.`activity_rank` 
               WHERE {where_clause}
           """

        result = self.db.get_one(query)
        return result['count'] > 0 if result else False

    def _insert_test_ranking_data(self, ranking_category: str, ranking_day: int, stage: str, count: int):
        """插入测试榜单数据
        Args:
            ranking_category: 榜单分类
            ranking_day: 榜单类型(日榜/总榜)，-1表示总榜，其他数字表示日榜
            stage: 活动阶段(赛段/日期)，默认前一天
            count: 要插入的测试数据数量
        """
        # 从满足条件的榜单数据中取一条数据作为模板
        template_query = f"""
                    SELECT * FROM `kong_test`.`activity_rank` 
                    WHERE number = {self.activity_number} 
                    AND category = '{ranking_category}' 
                    AND day = {ranking_day}
                    {'AND stage = ' + stage if stage else ''}
                    LIMIT 1
                """

        template_data = self.db.get_one(template_query)

        if not template_data:
            self.logger.warning("未找到符合条件的模板数据，无法进行复制")
            return 0

        self.logger.info(f"找到模板数据，开始复制生成 {count} 条测试数据")

        inserted_count = 0
        base_user_id = 1467213
        user_account = FileHandler().read_yaml("test_data/test_user_account.yaml")

        for i in range(count):
            user_id = base_user_id + i

            # 设置intimateId（单人榜：user_id=intimateId；双人榜：intimateId>user_id）
            if template_data['userId'] == template_data['intimateId']:  # 单人榜
                intimate_id = user_id
            else:  # 双人榜
                intimate_id = user_account[12 + i]['user_id']

            # 构建复制插入SQL，只修改关键字段
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
                # 插入数据
                self.db.execute_update(
                    insert_query,
                    (
                        user_id, intimate_id,
                        template_data['number'], template_data['category'], template_data['stage'],
                        template_data['year'], template_data['month'], template_data['day'],
                        template_data['value'] - i * 10,  # 递减的value值
                        template_data['value1'], template_data['value2'], template_data['value3'],
                        template_data['value4'], template_data['value5'], template_data['value6'],
                        template_data['value7'], template_data['valueTime'],
                        template_data['source'], template_data['display'], template_data['completed'],
                        template_data['created'], template_data['updated']
                    )
                )
                inserted_count += 1
                self.logger.info(f"新增榜单数据 {user_id} - {intimate_id}")
            except Exception as e:
                self.logger.error(f"新增榜单数据 {user_id} - {intimate_id} 失败: {str(e)}")

        self.logger.info(f"共插入 {inserted_count} 条测试数据")
        return inserted_count

    def _process_ranking_data(self, raw_data: List[Dict]) -> List[Dict]:
        """处理榜单数据（单人和双人分别处理）"""
        ranked_data = []

        for index, item in enumerate(raw_data, 1):
            if item.get("userId") == item.get("intimateId"):
                # 单人榜处理
                ranked_item = {
                    "number": item.get("number"),  # 活动编号
                    "category": item.get("category"),
                    "ranking_day": item.get("day"),
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
                    "ranking_day": item.get("day"),
                    "stage": item.get("stage"),
                    "user_id": item.get("userId"),
                    "value": item.get("value"),
                    "ranking": index,
                }
                ranked_item_user2 = {
                    "number": item.get("number"),
                    "category": item.get("category"),
                    "ranking_day": item.get("day"),
                    "stage": item.get("stage"),
                    "user_id": item.get("intimateId"),
                    "value": item.get("value"),
                    "ranking": index,
                }
                ranked_data.extend([ranked_item_user1, ranked_item_user2])
        self.logger.info(f"榜单数据处理完成: {ranked_data}")
        return ranked_data

    def clear_user_rewards(self, ranking_data: List[Dict], activity_reward_config: List[Dict]):
        """
        清除榜单用户奖励 - 初步方案: 直接全部清除

        Args:
            ranking_data: 榜单数据
            activity_reward_config: 活动奖励配置
        """

        # 清除用户奖励
        for user_data in ranking_data:
            user_id = user_data.get('user_id')
            # 清除装扮奖励
            dress_query = """
                delete from `kong_test`.`user_dress` where userId = %s;
            """
            self.db.execute_update(dress_query, (user_id,))
            # 清除荣誉称号奖励
            title_query = """
                delete from `kong_test`.`user_title` where userId = %s;
            """
            self.db.execute_update(title_query, (user_id,))
            # 清除勋章奖励
            medal_query = """
                delete from `kong_test`.`user_medal` where userId = %s;
            """
            self.db.execute_update(medal_query, (user_id,))
            # 清除贵族奖励
            noble_query = """
                delete from `kong_test`.`user_nobleman_level` where userId = %s;
            """
            self.db.execute_update(noble_query, (user_id,))
            # 清除会员/超级会员奖励
            vip_query = """
                delete from `kong_test`.`user_vip_level` where userId = %s;
            """
            self.db.execute_update(vip_query, (user_id,))
            # 清除靓号奖励
            nice_query = """
                delete from `kong_test`.`user_nice_number` where userId = %s;
            """
            self.db.execute_update(nice_query, (user_id,))

    def execute_scheduled_tasks(self, scheduled_tasks: List[Dict[str, Any]]):
        """
        执行定时任务

        Args:
            scheduled_tasks: 计划任务列表
        """
        pass

    def validate_reward_distribution(self, ranking_data: List[Dict], activity_reward_config: List[Dict]) -> Dict[
                                                                                                            str:str,
                                                                                                            Any]:
        """
        验证奖励下发情况

        Args:
            ranking_data: 榜单数据
            activity_reward_config: 活动奖励配置
        Returns:
            Dict: 验证结果
        """
        self.logger.info("验证奖励下发情况")

        validation_result = {
            "total_users": len(ranking_data),
            "users_with_rewards": 0,
            "users_without_rewards": 0,
            "distribution_details": []
        }

        # 根据排名获取应下发的奖励

        # 验证每个用户的奖励下发情况
        for user_data in ranking_data:
            user_id = user_data.get('user_id')
            ranking = user_data.get('ranking')

            # 查询装扮奖励下发记录
            dress_query = """
                select * from `kong_test`.`user_honor_title` where userId = %s;
            """
            reward_dress = self.db.execute_query(dress_query, (user_id,))
            # 查询荣誉称号奖励下发记录
            title_query = """
                select * from `kong_test`.`user_title` where userId = %s;
            """
            reward_title = self.db.execute_query(title_query, (user_id,))
            # 查询勋章奖励下发记录
            medal_query = """
                select * from `kong_test`.`user_medal` where userId = %s;
            """
            reward_medal = self.db.execute_query(medal_query, (user_id,))
            # 查询贵族奖励下发记录
            noble_query = """
                select * from `kong_test`.`user_nobleman_level` where userId = %s;
            """
            reward_noble = self.db.execute_query(noble_query, (user_id,))
            # 查询会员/超级会员奖励下发记录
            vip_query = """
                select * from `kong_test`.`user` where userId = %s;
            """
            reward_vip = self.db.execute_query(vip_query, (user_id,))
            # 查询靓号奖励下发记录
            number_query = """
                select * from `kong_test`.`user_backpack` where userId = %s;
            """
            reward_number = self.db.execute_query(number_query, (user_id,))

    def validate(self):
        """
        执行完整的奖励验证流程

        Returns:
            bool: 验证是否通过
        """
        self.logger.info("开始活动榜单奖励验证")

        try:
            # 1、获取活动文档中的奖励配置
            activity_reward_config_doc = self.get_activity_reward_config_doc(self.activity_config_path)

            # 2、获取数据库表中的奖励配置
            activity_reward_config_db = self.get_activity_reward_config_db()

            # 3、比较奖励配置是否一致
            differences = self.verify_db_vs_doc(activity_reward_config_doc, activity_reward_config_db)

            # # 4、获取活动榜单数据 - 用户排名及对应奖励
            # ranking_data = self.get_activity_ranking_data()
            #
            # # 5、清除下发奖励前已有的装扮、荣誉称号、勋章、贵族、会员/超级会员、靓号
            # self.clear_user_rewards(ranking_data, activity_reward_config_doc)
            #
            # # 6、执行定时任务 - 奖励下发
            # self.execute_scheduled_tasks(self.scheduled_tasks)
            #
            # # 7、判断用户所有奖励是否下发, 下发时长是否正确
            # if ranking_data:
            #     self.logger.info("榜单数据示例: %s", ranking_data[0] if len(ranking_data) > 0 else "无数据")

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
        scheduled_tasks = []
    )

    # 执行验证
    success = validator.validate()
    return success


if __name__ == "__main__":
    main()

# Todo:
# 1、完善获取榜单数据方法
# 2、清除下发奖励前已有的装扮、荣誉称号、勋章、贵族、会员/超级会员、靓号
# 3、执行定时任务方法
# 4、补充完成奖励下发校验方法 - 根据排名获取应下发的奖励, 分别到不同数据库中去查询记录/有效期是否一致
