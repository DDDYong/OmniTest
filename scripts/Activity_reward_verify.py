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
from typing import Dict, List, Any

from config.config_manager import config_manager
from utils import logger
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
        6: {"name": "BRIGHT_NUMBER", "desc": "靓号"},
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

    def __init__(self, activity_number: int, activity_config_path: str):
        """
        初始化活动奖励验证模块

        Args:
            activity_number: 活动ID
            activity_config_path: 活动奖励配置文件路径
        """
        self.activity_number = activity_number
        self.activity_config_path = activity_config_path
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
        获取数据库中的奖励配置，并根据服务端映射处理奖励类型

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
                    # 构造查询键
                    query_key = f"{activityType_doc}_{rank_doc}_{rewardType_doc}"
                    # 存储文档中该奖励的关键信息
                    doc_quick_query[query_key] = {
                        "rewardId_doc": reward["rewardId"],
                        "valid_days_doc": reward["valid_days"],
                        "rewardType_name_doc": reward["rewardType_name"],
                        "activityType_name_doc": doc_rank["activityType_name"]
                    }

        differences = {
            "db_exist_doc_not": [],  # 数据库存在、文档不存在的奖励
            "rewardId_mismatch": [],  # rewardId不一致的奖励
            "valid_days_mismatch": []  # 奖励时长（rewardCount）不一致的奖励
        }

        for db_item in db_config:
            activityType_db = db_item["activityType"]
            rankNumber_db = db_item["rankNumber"]
            rewardType_db = db_item["rewardType"]
            rewardId_db = db_item["rewardId"]
            rewardCount_db = db_item["rewardCount"]  # 对应文档的valid_days
            rewardType_name_db = db_item["rewardType_name"]

            # 构造查询键，匹配文档配置
            query_key = f"{activityType_db}_{rankNumber_db}_{rewardType_db}"

            # 校验：数据库存在的奖励，文档是否存在
            if query_key not in doc_quick_query:
                differences["db_exist_doc_not"].append({
                    "db_info": {
                        "activityType": activityType_db,
                        "rankNumber": rankNumber_db,
                        "rewardType": rewardType_db,
                        "rewardType_name": rewardType_name_db,
                        "rewardId": rewardId_db,
                        "rewardCount（有效期）": rewardCount_db
                    },
                    "reason": "该奖励在数据库中存在，但文档配置中无对应记录（榜单+排名+奖励类型不匹配）"
                })
                continue  # 文档不存在，无需后续细节校验，直接处理下一个数据库元素

            # 文档存在，校验细节：rewardId是否一致
            doc_info = doc_quick_query[query_key]
            if doc_info["rewardId_doc"] != rewardId_db:
                differences["rewardId_mismatch"].append({
                    "common_info": {
                        "activityType": activityType_db,
                        "activityType_name_doc": doc_info["activityType_name_doc"],
                        "rank": rankNumber_db,
                        "rewardType": rewardType_db,
                        "rewardType_name_doc": doc_info["rewardType_name_doc"],
                        "rewardType_name_db": rewardType_name_db
                    },
                    "rewardId_doc": doc_info["rewardId_doc"],
                    "rewardId_db": rewardId_db,
                    "reason": "奖励ID不一致（文档与数据库核心标识不匹配）"
                })

            # 文档存在，校验细节：有效期（valid_days vs rewardCount）是否一致
            if doc_info["valid_days_doc"] != rewardCount_db:
                differences["valid_days_mismatch"].append({
                    "common_info": {
                        "activityType": activityType_db,
                        "activityType_name_doc": doc_info["activityType_name_doc"],
                        "rank": rankNumber_db,
                        "rewardType": rewardType_db,
                        "rewardType_name_doc": doc_info["rewardType_name_doc"]
                    },
                    "valid_days_doc（文档有效期）": doc_info["valid_days_doc"],
                    "rewardCount_db（数据库有效期）": rewardCount_db,
                    "reason": "奖励有效期天数不一致"
                })

        self.logger.info(f"数据库配置遍历校验报告（共校验数据库奖励：{len(db_config)}条）")

        # 1. 数据库有、文档无的差异
        if differences["db_exist_doc_not"]:
            self.logger.info(f"[差异: 数据库存在、文档无] 共{len(differences['db_exist_doc_not'])}条")
            for idx, item in enumerate(differences["db_exist_doc_not"], 1):
                db = item["db_info"]
                self.logger.info(f"  {idx}. 榜单：activityType={db['activityType']} | 排名：{db['rankNumber']} | 奖励类型：{db['rewardType_name']}（Type={db['rewardType']}） | 数据库rewardId：{db['rewardId']} | 原因：{item['reason']}")

        # 2. rewardId不匹配的差异
        if differences["rewardId_mismatch"]:
            self.logger.info(f"[差异: rewardId不匹配] 共{len(differences['rewardId_mismatch'])}条")
            for idx, item in enumerate(differences["rewardId_mismatch"], 1):
                common = item["common_info"]
                self.logger.info(f"  {idx}. 榜单：{common['activityType_name_doc']}（Type={common['activityType']}） | 排名：{common['rank']} | 奖励类型：{common['rewardType_name_doc']} | 文档rewardId：{item['rewardId_doc']} | 数据库rewardId：{item['rewardId_db']}")

        # 3. 有效期不匹配的差异
        if differences["valid_days_mismatch"]:
            self.logger.info(f"[差异: 有效期不匹配] 共{len(differences['valid_days_mismatch'])}条")
            for idx, item in enumerate(differences["valid_days_mismatch"], 1):
                common = item["common_info"]
                self.logger.info(f"  {idx}. 榜单：{common['activityType_name_doc']}（Type={common['activityType']}） | 排名：{common['rank']} | 奖励类型：{common['rewardType_name_doc']} | 文档有效期：{item['valid_days_doc（文档有效期）']}天 | 数据库有效期：{item['rewardCount_db（数据库有效期）']}天")

        # 无差异提示
        if not any(differences.values()):
            self.logger.info("✅ 数据库所有奖励均在文档中存在，且rewardId、有效期完全一致！")

        return differences

    def get_activity_ranking_data(self, ranking_category: str = '1', ranking_mode: int = 1, ranking_type: int = -1, stage: str = "20260105", top_n: int = 10) -> \
    List[Dict]:
        """
        获取活动榜单数据 - 用户排名及对应奖励
        Args:
            ranking_category: 榜单分类
            ranking_type: 榜单类型(日榜/总榜)
            ranking_mode: 榜单模式(单人/双人/多人)
            stage: 活动阶段(赛段/日期)
            top_n: 要获取的榜单Top N用户

        Returns:
            List[Dict]: 榜单数据
        """
        self.logger.info("获取活动榜单数据")

        # 查询活动榜单数据 - 日榜
        # 查询活动榜单数据 - 总榜
        query = """
            SELECT * FROM `kong_test`.`activity_rank` 
            WHERE activity_number = %s and category = %s and ranking_type = %s and stage = %s
            ORDER BY value desc limit %s
        """
        ranking_data = self.db.execute_query(query, (self.activity_number, ranking_category, ranking_mode, ranking_type,
                                                     stage, top_n))

        self.logger.info(f"获取到 {len(ranking_data)} 条榜单数据")
        return ranking_data

    def validate_reward_distribution(self, ranking_data: List[Dict, Any], activity_reward_config: List[Dict, Any]) -> \
    Dict[str, Any]:
        """
        验证奖励下发情况

        Args:
            ranking_data: 榜单数据

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

            # # # 4、获取活动榜单数据 - 用户排名及对应奖励
            # # ranking_data = self.get_activity_ranking_data()
            # #
            # # # 5、判断用户所有奖励是否下发, 下发时长是否正确
            # # distribution_validation = self.validate_reward_distribution(ranking_data)
            # #
            # # # 综合验证结果
            # # is_config_consistent = config_comparison["is_consistent"]
            # # all_rewards_distributed = distribution_validation["users_without_rewards"] == 0
            # #
            # # validation_passed = is_config_consistent and all_rewards_distributed
            # #
            # # self.logger.info(f"验证结果: {'通过' if validation_passed else '失败'}")
            # # self.logger.info(f"配置一致性: {'一致' if is_config_consistent else '不一致'}")
            # # self.logger.info(f"奖励下发情况: {distribution_validation['users_with_rewards']}/{distribution_validation['total_users']} 用户已下发奖励")

            return None

        except Exception as e:
            self.logger.error(f"验证过程中发生错误: {str(e)}")
            return False


def main():
    """主函数"""

    # 创建验证器
    validator = ActivityRewardVerification(
        activity_number = 1054,
        activity_config_path = 'test_data/activity_reward_config.yaml',
    )

    # 执行验证
    success = validator.validate()
    return success


if __name__ == "__main__":
    main()

# Todo:
# 1、验证配置对比方法是否正常
# 2、获取榜单数据方法
# 3、补充完成奖励下发校验方法 - 根据排名获取应下发的奖励，分别到不同数据库中去查询记录/有效期是否一致
