"""
-------------------------------------------------
File:           lottery_probability_christmas.py
Author:         duanyang
Date:           2025/12/18
-------------------------------------------------
Description:
圣诞节抽奖概率验证脚本
用于验证抽奖接口的实际概率是否符合预期概率
-------------------------------------------------
"""
import datetime
import os
import random
import sys
import time
from typing import Dict, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import logger
from utils.api.api_client import ApiClient
from utils.db.mysql_client import MySQLClient
from config.config_manager import config_manager


class ChristmasLotteryProbabilityValidator:
    """
    圣诞节抽奖概率验证器
    用于验证抽奖接口的实际概率是否符合预期概率
    """

    def __init__(
            self,
            account: Dict[str, str],
            prize_probabilities: Optional[Dict[str, float]] = None,
            allowed_deviation: float = 0.05,
            lottery_api: str = "/api/activity/lottery/start",
            threshold: int = 40,
            times: int = 1,
            total: int = 100,
            activity_number: int = 1053,
            activity_type: int = 10
    ):
        """
        初始化验证器
        
        Args:
            account: 账号信息, 包含用户名和密码
            prize_probabilities: 奖品与预期概率映射, 默认为None(从数据库获取)
            allowed_deviation: 允许的实际概率偏差绝对值, 默认为0.05
            lottery_api: 抽奖接口URL, 默认为"/api/activity/lottery/start"
            threshold: 抽奖次数阈值, 低于此值跳过概率校验, 默认为50
            times: 每次抽奖的次数, [1, 10, 50]
            total: 抽奖总次数, 默认为100
            activity_number: 活动编号, 默认为1053
            activity_type: 活动类型, 默认为10, 101
        """
        self.account = account
        self.prize_probabilities = prize_probabilities
        self.allowed_deviation = allowed_deviation
        self.lottery_api = lottery_api
        self.threshold = threshold
        self.times = times
        self.total = total
        self.activity_number = activity_number
        self.activity_type = activity_type
        self.logger = logger
        self.api_client = ApiClient()
        self.auth_signature = None
        self.user_id = None
        self.user_sex = None
        # 使用ConfigManager获取配置并创建MySQLClient实例
        self.db = MySQLClient(config_manager.get_mysql_config())

    def login(self) -> bool:
        """
        用户登录
        
        Returns:
            bool: 登录是否成功
        """
        try:
            self.logger.info(f"正在登录账号: {self.account['mobile']}")

            # 发送登录请求
            login_data = {
                "mobile": self.account["mobile"],
                "password": self.account["password"]
            }

            response = self.api_client.post(
                url = "/api/hx/usr/login/v2",
                json = login_data,
                headers = {"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                resp_json = response.json().get("data")
                if "signature" in resp_json:
                    self.auth_signature = resp_json["signature"]
                    # 设置认证头
                    self.api_client.set_headers({"Authorization": f"Bearer {self.auth_signature}"})

                    # 获取用户ID
                    user_info = self.db.get_one(
                        "SELECT userid, sex FROM `kong_test`.`user` WHERE mobile = %s",
                        (self.account["mobile"],)
                    )

                    if user_info:
                        self.user_id = user_info.get("userid")
                        self.user_sex = user_info.get("sex", 2)  # 默认2为女用户
                        self.logger.info(f"[成功] 账号: {self.user_id} 登录成功, 性别: {'男' if self.user_sex == 1 else '女'}, 获取到的签名: {self.auth_signature}")
                        return True
                    else:
                        self.logger.error(f"[失败] 未找到用户信息: {self.account['mobile']}")
                        return False
                else:
                    self.logger.error(f"[失败] 登录响应中缺少signature字段: {response.text}")
                    return False
            else:
                self.logger.error(f"[失败] 登录失败, 状态码: {response.status_code}, 响应: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"[失败] 登录异常: {str(e)}")
            return False

    def check_and_update_lottery_times(self) -> bool:
        """
        检查并更新抽奖次数
        
        Returns:
            bool: 抽奖次数是否足够
        """
        try:
            # 查询用户ID
            if not self.user_id:
                self.logger.error("用户ID为空, 无法查询抽奖次数")
                return False

            # 查询抽奖次数
            self.logger.info(f"正在查询账号: {self.user_id} 的抽奖次数")

            count = self.db.get_one(
                "SELECT totalCount, usedCount FROM `kong_test`.`activity_coupon_count` WHERE activityNumber = %s AND userId = %s",
                (
                    self.activity_number,
                    self.user_id,
                )
            )

            if count:
                total_count = count.get("totalCount", 0)
                used_count = count.get("usedCount", 0)
                remaining_count = total_count - used_count
                required_count = self.total if self.activity_type == 10 else self.total * 2

                self.logger.info(f"账号: {self.user_id} 当前剩余抽奖次数: {remaining_count}, 需要: {required_count}")

                if remaining_count >= required_count:
                    self.logger.info(f"[通过] 账号: {self.user_id} 抽奖次数足够, 可以直接抽奖")
                    return True
                else:
                    # 更新抽奖次数
                    need_add = required_count - remaining_count
                    self.logger.info(f"[调整] 账号: {self.user_id} 抽奖次数不足, 需要增加 {need_add} 次")

                    self.db.execute_update(
                        "UPDATE `kong_test`.`activity_coupon_count` SET totalCount = totalCount + %s WHERE activityNumber = %s AND userId = %s",
                        (need_add, self.activity_number, self.user_id),
                    )

                    # 重新查询确认
                    updated_count = self.db.get_one(
                        "SELECT totalCount, usedCount FROM `kong_test`.`activity_coupon_count` WHERE activityNumber = %s AND userId = %s",
                        (
                            self.activity_number,
                            self.user_id,
                        )
                    )

                    if updated_count:
                        updated_remaining = updated_count.get("totalCount", 0) - updated_count.get("usedCount", 0)
                        if updated_remaining >= required_count:
                            self.logger.info(f"[通过] 账号: {self.user_id} 抽奖次数已增加, 当前剩余: {updated_remaining}")
                            return True
                        else:
                            self.logger.error(f"[失败] 账号: {self.user_id} 抽奖次数增加后仍不足")
                            return False
                    else:
                        self.logger.error(f"[失败] 账号: {self.user_id} 抽奖次数更新后查询失败")
                        return False
            else:
                # 如果没有记录, 则插入记录
                self.logger.info(f"账号: {self.user_id} 没有抽奖次数记录, 正在创建")

                self.db.execute_update(
                    "INSERT INTO `kong_test`.`activity_coupon_count` (activityNumber, activityType, userId, totalCount, usedCount, created, updated) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (self.activity_number, '10', self.user_id, self.total, 0, datetime.datetime.now(),
                     datetime.datetime.now()),
                )

                self.logger.info(f"[通过] 账号: {self.user_id} 抽奖次数记录已创建")
                return True

        except Exception as e:
            self.logger.error(f"[失败] 检查抽奖次数异常: {str(e)}")
            return False

    def get_prize_probabilities(self) -> Dict[str, float]:
        """
        获取奖品概率配置(代码中写死的概率映射)
        
        Returns:
            Dict[str, float]: 奖品概率映射
        """
        if self.prize_probabilities:
            return self.prize_probabilities

        try:

            self.logger.info(f"正在获取 {'奇幻圣诞树' if self.activity_type == 10 else '水晶圣诞树'} 的奖品概率配置, 用户性别: {'男' if self.user_sex == 1 else '女'}")

            # 根据活动类型和用户性别设置不同的概率配置
            if self.activity_type == 10:
                # 奇幻圣诞树的奖品概率配置
                if self.user_sex == 1:  # 男用户
                    self.prize_probabilities = {
                        "拐棍糖果": 0.25,
                        "圣诞彩球": 0.15,
                        "雪花饼干": 0.30,
                        "小姜饼人": 0.25,
                        "圣诞礼袜": 0.05
                    }
                else:  # 女用户
                    self.prize_probabilities = {
                        "拐棍糖果": 0.35,
                        "圣诞彩球": 0.25,
                        "雪花饼干": 0.20,
                        "小姜饼人": 0.15,
                        "圣诞礼袜": 0.05
                    }
            elif self.activity_type == 101:
                # 水晶圣诞树的奖品概率配置
                if self.user_sex == 1:  # 男用户
                    self.prize_probabilities = {
                        "金丝葫芦": 0.25,
                        "珐琅彩马": 0.15,
                        "水晶耳饰": 0.30,
                        "皓月挂坠": 0.25,
                        "钻石王冠": 0.05
                    }
                else:  # 女用户
                    self.prize_probabilities = {
                        "金丝葫芦": 0.35,
                        "珐琅彩马": 0.25,
                        "水晶耳饰": 0.20,
                        "皓月挂坠": 0.15,
                        "钻石王冠": 0.05
                    }
            else:
                self.logger.error(f"[失败] 不支持的活动类型: {self.activity_type}")
                return {}

            self.logger.info(f"获取奖品概率成功: {self.prize_probabilities}")
            return self.prize_probabilities

        except Exception as e:
            self.logger.error(f"[失败] 获取奖品概率异常: {str(e)}")
            return {}

    def call_lottery_api(self) -> Dict[str, int]:
        """
        调用抽奖API
        
        Returns:
            Dict[str, int]: 抽奖结果, 键为奖品名称, 值为获得数量
        """
        try:
            params = {
                "number": self.activity_number,
                "times": self.times,
                "activityType": self.activity_type,
            }
            # self.logger.info(f"正在调用抽奖API, 请求参数: {params}")
            response = self.api_client.get(
                url = self.lottery_api,
                params = params,
                headers = {"Content-Type": "application/json", "sign": self.auth_signature}
            )

            if response.status_code == 200:
                response_json = response.json()

                # 判断业务响应码是否为200(成功)
                if response_json.get("code") == 200:
                    data = response_json.get("data", [])

                    lottery_result = {}
                    if data and len(data) > 0:
                        for item in data:
                            prize_name = item.get("name", "未知奖品")
                            count = item.get("rewardCount", 0)
                            if prize_name in lottery_result:
                                lottery_result[prize_name] += count
                            else:
                                lottery_result[prize_name] = count

                    self.logger.info(f"抽奖结果: {lottery_result}")
                    return lottery_result
                else:
                    # 业务响应码不是200, 说明抽奖失败
                    error_msg = response_json.get("msg", "未知错误")
                    self.logger.error(f"[失败] 抽奖失败, 错误信息: {response_json.get("code"), error_msg}")
                    return {}
            else:
                self.logger.error(f"[失败] 抽奖接口调用失败, 状态码: {response.status_code}, 响应: {response.text}")
                return {}

        except Exception as e:
            self.logger.error(f"[失败] 抽奖接口调用异常: {str(e)}")
            return {}

    def validate(self) -> bool:
        """
        执行概率验证
        
        Returns:
            bool: 概率验证是否通过
        """
        try:
            # 1. 用户登录
            if not self.login():
                return False

            # 2. 检查并更新抽奖次数
            if not self.check_and_update_lottery_times():
                return False

            # 3. 获取奖品概率配置
            prize_probabilities = self.get_prize_probabilities()
            if not prize_probabilities:
                return False

            # 4. 执行抽奖并统计结果
            self.logger.info(f"开始执行抽奖, 总次数: {self.total}, 每次抽奖: {self.times} 次")

            prize_counts = {prize: 0 for prize in prize_probabilities}
            prize_counts["未知奖品"] = 0

            for i in range(self.total // self.times):
                lottery_result = self.call_lottery_api()
                if lottery_result:
                    for prize, count in lottery_result.items():
                        if prize in prize_counts:
                            prize_counts[prize] += count
                        else:
                            prize_counts["未知奖品"] += count

                wait_time = random.uniform(2, 2.5)  # 随机间隔
                self.logger.info(f"等待 {wait_time} 秒后继续下一次抽奖...")
                time.sleep(wait_time)

                # 抽奖记录进度
                self.logger.info(f"抽奖进度: {(i + 1) * self.times}/{self.total}")

            self.logger.info(f"抽奖完成, 总抽奖次数: {self.total}")
            self.logger.info(f"抽奖结果统计: {prize_counts}")

            # 5. 验证概率
            if self.total < self.threshold:
                self.logger.info(f"[跳过] 抽奖次数不足阈值 {self.threshold} 次, 跳过概率偏差校验")
                return True

            all_valid = True
            total_actual = sum(prize_counts.values())

            for prize, expected_prob in prize_probabilities.items():
                actual_count = prize_counts.get(prize, 0)
                actual_prob = actual_count / total_actual if total_actual > 0 else 0
                deviation = abs(float(actual_prob) - float(expected_prob))

                if deviation > self.allowed_deviation:
                    self.logger.error(
                        f"[失败] {prize}: 预期 {expected_prob:.2%} → 实际 {actual_prob:.2%} (偏差: {deviation:.2%}, 允许偏差: ±{self.allowed_deviation:.2%})")
                    all_valid = False
                else:
                    self.logger.info(
                        f"[通过] {prize}: 预期 {expected_prob:.2%} → 实际 {actual_prob:.2%} (偏差: {deviation:.2%}, 允许偏差: ±{self.allowed_deviation:.2%})")

            # 检查未知奖品
            if prize_counts["未知奖品"] > 0:
                self.logger.warning(f"[警告] 出现未知奖品 {prize_counts['未知奖品']} 次")

            return all_valid

        except Exception as e:
            self.logger.error(f"[失败] 概率验证异常: {str(e)}")
            return False
        finally:
            # 移除不必要的显式关闭, MySQLClient的析构函数会自动处理资源释放
            # 这样可以避免连接池被关闭两次的问题
            pass


def main(args = None):
    """
    主函数
    
    Args:
        args: 可选参数, 用于直接传递参数, 而不通过命令行解析
    """
    import argparse

    if args is None:
        # 从命令行解析参数
        parser = argparse.ArgumentParser(description = "圣诞节抽奖概率验证脚本")
        parser.add_argument("-m", "--mobile", type = str, required = True, help = "登录手机号")
        parser.add_argument("-p", "--password", type = str, required = True, help = "登录密码")
        parser.add_argument("--activity-number", type = int, default = 1053, help = "活动编号, 默认: 1053")
        parser.add_argument("--activity-type", type = int, default = 10, help = "抽奖类型, 默认: 10")
        parser.add_argument("--total", type = int, default = 100, help = "抽奖总次数, 默认: 100")
        parser.add_argument("--times", type = int, default = 1, help = "每次抽奖次数, 默认: 1")
        parser.add_argument("--threshold", type = int, default = 40, help = "概率校验阈值, 默认: 50")
        parser.add_argument("--deviation", type = float, default = 0.05, help = "允许偏差, 默认: 0.05")

        args = parser.parse_args()

    # 创建验证器
    validator = ChristmasLotteryProbabilityValidator(
        account = {
            "mobile": args.mobile,
            "password": args.password
        },
        activity_number = args.activity_number,
        activity_type = args.activity_type,
        total = args.total,
        times = args.times,
        threshold = args.threshold,
        allowed_deviation = args.deviation
    )

    # 执行验证
    result = validator.validate()

    if result:
        logger.info("=" * 60)
        logger.info("🎉 抽奖概率验证通过!")
        logger.info("=" * 60)
        return True
    else:
        logger.error("=" * 60)
        logger.error("❌ 抽奖概率验证失败!")
        logger.error("=" * 60)
        return False


if __name__ == "__main__":
    class Args:
        def __init__(self):
            self.mobile = "17370000004"
            self.password = "123456"
            self.activity_number = 1053
            self.activity_type = 10
            self.total = 1000
            self.times = 50
            self.threshold = 100
            self.deviation = 0.01


    main(Args())
