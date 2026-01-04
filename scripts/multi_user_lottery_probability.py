"""
-------------------------------------------------
File:           multi_user_lottery_probability.py
Author:         duanyang
Date:           2025/12/29
-------------------------------------------------
Description:
多用户抽奖概率验证脚本
-------------------------------------------------
"""
import datetime
import os
import random
import sys
import time
from typing import Dict, List, Optional, Tuple

from config.config_manager import config_manager
from utils.api.api_client import ApiClient
from utils.db.mysql_client import MySQLClient
from utils.file_util import FileHandler
from utils.logger_util import logger

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MultiUserLotteryProbabilityValidator:
    """
    多用户抽奖概率验证器
    支持全服概率和个人概率计算，多用户随机抽取
    """

    def __init__(
            self,
            accounts: List[Dict[str, str]],
            prize_probabilities: Optional[Dict[str, float]] = None,
            allowed_deviation: float = 0.05,
            lottery_api: str = "/api/activity/20251223/buildTree",
            threshold: int = 40,
            times_options: List[int] = None,
            total_times: int = 100,
            activity_number: int = 1054,
            activity_type: int = 10,
            user_times_range: List[int] = None,
            validation_mode: str = "BOTH",

    ):
        """
        初始化验证器

        Args:
            accounts: 账号信息列表，每个账号包含用户名和密码
            prize_probabilities: 奖品与预期概率映射，默认为None(从数据库获取)
            allowed_deviation: 允许的实际概率偏差绝对值，默认为0.5
            lottery_api: 抽奖接口URL，默认为"/api/activity/lottery/start"
            threshold: 抽奖次数阈值，低于此值跳过概率校验，默认为50
            times_options: 抽奖次数选项列表，默认为[1, 10, 50]
            total_times: 抽奖总次数，默认为100
            activity_number: 活动编号，默认为1053
            activity_type: 活动类型，默认为10, 101
            user_times_range: 每个用户抽奖次数范围，默认为[10, 100]
            validation_mode: 验证模式，"BOTH"表示全服+个人，"SERVER"表示仅全服，"PERSONAL"表示仅个人，默认为"BOTH"
        """
        self.accounts = accounts
        self.prize_probabilities = prize_probabilities
        self.allowed_deviation = allowed_deviation
        self.lottery_api = lottery_api
        self.threshold = threshold
        self.times_options = times_options if times_options is not None else [1, 10, 50]
        self.total_times = total_times
        self.activity_number = activity_number
        self.activity_type = activity_type
        self.user_times_range = user_times_range
        self.validation_mode = validation_mode
        self.logger = logger

        # 用户信息存储
        self.users = {}  # key: user_id, value: user_info dict
        # self.user_apis = {}  # key: user_id, value: ApiClient instance

        self.db = MySQLClient(config_manager.get_mysql_config())
        self.api_client = ApiClient()

    def login_user(self, account: Dict[str, str]) -> Optional[Dict]:
        """
        用户登录

        Args:
            account: 账号信息

        Returns:
            Dict: 用户信息字典，包含user_id, auth_sign等
        """
        try:
            self.logger.info(f"正在登录账号: {account['mobile']}")
            # 获取用户信息 ID, 性别
            user_info = self.db.get_one(
                "SELECT userid, nick, sex FROM `kong_test`.`user` WHERE mobile = %s",
                (account["mobile"],)
            )

            if user_info:
                user_info = {
                    "user_id": user_info.get("userid"),
                    "mobile": account["mobile"],
                    "sex": user_info.get("sex", 2),
                    "nick": user_info.get("nick"),
                }
            else:
                self.logger.error(f"[失败] 未找到用户信息: {account['mobile']}")
                return None

            # 发送登录请求
            login_data = {
                "mobile": account["mobile"],
                "password": account["password"]
            }

            response = self.api_client.post(
                url = "/api/hx/usr/login/v2",
                json = login_data,
                headers = {"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                resp_json = response.json().get("data")
                if "signature" in resp_json:
                    auth_sign = resp_json["signature"]
                    # 设置签名
                    user_info["sign"] = auth_sign

                    self.logger.info(f"[成功] 账号: {user_info['user_id']} - {user_info['nick']} 登录成功")
                    return user_info
                else:
                    self.logger.error(f"[失败] 登录失败: {resp_json.get('code', '未知错误')}")
                    return None
            else:
                self.logger.error(f"[失败] 登录异常: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"[失败] 登录异常: {str(e)}")
            return None

    def login_all_users(self) -> bool:
        """
        登录所有用户

        Returns:
            bool: 是否所有用户都登录成功
        """
        self.logger.info(f"开始登录 {len(self.accounts)} 个用户")

        success_count = 0
        for account in self.accounts:
            user_info = self.login_user(account)
            if user_info:
                user_id = user_info["user_id"]
                self.users[user_id] = user_info
                success_count += 1
            else:
                self.logger.error(f"用户 {account['mobile']} 登录失败")

        self.logger.info(f"用户登录完成: {success_count}/{len(self.accounts)} 个用户登录成功")
        return success_count > 0

    def distribute_lottery_times(self) -> Dict[str, int]:
        """
        随机分配抽奖次数给登录成功的用户

        Returns:
            Dict[str, int]: 用户ID到抽奖次数的映射

        Raises:
            ValueError: 参数不合法或无法完成分配时抛出异常
        """
        user_ids = list(self.users.keys())
        user_count = len(user_ids)

        # 无用户直接返回空字典
        if user_count == 0:
            self.logger.info("无登录用户，抽奖次数分配结果为空")
            return {}

        min_user_times = min(self.user_times_range)
        max_user_times = max(self.user_times_range)

        # 校验总次数是否满足用户抽奖次数范围要求
        min_required_total = user_count * min_user_times
        max_possible_total = user_count * max_user_times
        if self.total_times < min_required_total:
            self.logger.error(
                f"总抽奖次数不足: {user_count}个用户至少需要{min_required_total}次(每人{min_user_times}次), 不满足用户抽奖次数范围要求"
            )
            return {}

        if self.total_times > max_possible_total:
            self.logger.error(
                f"总抽奖次数超限: {user_count}个用户最多可分配{max_possible_total}次(每人{max_user_times}次), 不满足用户抽奖次数范围要求"
            )
            return {}

        # 基础分配，每人先给最小次数
        user_times = {user_id: min_user_times for user_id in user_ids}
        remaining_times = self.total_times - min_required_total

        # 继续分配剩余次数
        if remaining_times > 0:
            available_users = user_ids.copy()
            while remaining_times > 0 and available_users:
                # 随机选一个可分配的用户
                selected_user = random.choice(available_users)
                # 用户还可分配的最大次数
                max_add = max_user_times - user_times[selected_user]
                # 用户已达上限，则不再分配
                if max_add <= 0:
                    available_users.remove(selected_user)
                    continue

                # 本次分配次数: 随机1~(剩余次数和最大可加次数的最小值)，批量分配
                add_num = random.randint(1, min(remaining_times, max_add))
                user_times[selected_user] += add_num
                remaining_times -= add_num

        self.logger.info(f"抽奖次数分配结果(总次数: {self.total_times}):")
        for user_id, times in sorted(user_times.items()):
            self.logger.info(f"用户 {user_id}: {times} 次")
        self.logger.info("=" * 60)

        return user_times

    def check_and_update_user_lottery_times(self, user_times: dict[str, int]) -> bool:
        """
        检查并更新用户的抽奖次数是否足够

        Args:
            user_times: 用户ID到需要的抽奖次数的映射

        Returns:
            bool: 抽奖次数是否足够
        """
        try:
            # 获取所有抽奖材料ID
            material = self.db.execute_query(
                "SELECT id, name FROM kong_test.activity_material WHERE activityNumber = %s AND activityType = 10",
                (self.activity_number,)
            )

            if not material:
                self.logger.error(f"[失败] 未找到活动 {self.activity_number} 的抽奖材料配置")
                return False

            # 创建抽奖材料名称映射字典和ID列表
            material_dict = {}
            material_id_list = []
            for m in material:
                material_dict[m['id']] = m['name']
                material_id_list.append(m['id'])

            for user_id, required_times in user_times.items():

                self.logger.info(f"正在查询用户 {user_id} 的数量")

                # 查询用户所有抽奖材料数量
                placeholders = ','.join(['%s'] * len(material_id_list))
                query = f"SELECT materialId, totalCount, usedCount FROM `kong_test`.`activity_material_count` WHERE materialId IN ({placeholders}) and  userId = %s"
                params = tuple(material_id_list) + (user_id,)

                count = self.db.execute_query(query, params)

                # 确保每种材料当前数量和需要的数量匹配
                existing_material_ids = {item.get("materialId") for item in count} if count else set()
                all_material_ids = set(material_id_list)
                missing_material_ids = all_material_ids - existing_material_ids

                # 有缺失的抽奖材料则在数据库中创建材料记录
                if missing_material_ids:
                    self.logger.info(f"用户 {user_id} 缺少 {len(missing_material_ids)} 种抽奖材料，正在创建...")
                    for material_id in missing_material_ids:
                        material_name = material_dict.get(material_id, f"未知抽奖材料({material_id})")
                        self.db.execute_update(
                            "INSERT INTO `kong_test`.`activity_material_count` (materialId, userId, totalCount, usedCount, type, created, updated) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (material_id, user_id, required_times, 0, '8', datetime.datetime.now(),
                             datetime.datetime.now()),
                        )
                        self.logger.info(f"[新增] 已为用户 {user_id} 的 {material_name} 创建记录, 初始数量: {required_times}")

                    # 重新查询所有抽奖材料数量
                    count = self.db.execute_query(query, params)

                # 判断每一种抽奖材料数量是否满足抽奖次数要求
                if count:
                    all_sufficient = True
                    need_update_materials = []

                    for item in count:
                        material_id = item.get("materialId")
                        material_name = material_dict.get(material_id, f"未知材料({material_id})")
                        total_count = item.get("totalCount", 0)
                        used_count = item.get("usedCount", 0)
                        usable_count = total_count - used_count

                        self.logger.info(f"用户 {user_id} 当前{material_name}剩余数量: {usable_count}, 需要: {required_times}")

                        if usable_count < required_times:
                            all_sufficient = False
                            need_add = required_times - usable_count
                            need_update_materials.append({
                                'material_id': material_id,
                                'material_name': material_name,
                                'need_add': need_add,
                                'usable_count': usable_count
                            })
                            self.logger.info(f"[调整] {material_name} 数量不足, 需要增加 {need_add} 个")

                    if all_sufficient:
                        self.logger.info(f"[通过] 用户 {user_id} 所有抽奖材料都足够, 可以直接抽奖")
                    else:
                        # 更新不足的抽奖材料数量
                        for material_info in need_update_materials:
                            material_id = material_info['material_id']
                            material_name = material_info['material_name']
                            need_add = material_info['need_add']

                            self.logger.info(f"[调整] 正在为用户 {user_id} 的 {material_name} 增加 {need_add} 个")

                            self.db.execute_update(
                                "UPDATE `kong_test`.`activity_material_count` SET totalCount = totalCount + %s WHERE materialId = %s AND userId = %s",
                                (need_add, material_id, user_id),
                            )

                        # 再次检查是否所有抽奖材料数量都满足要求
                        updated_count = self.db.execute_query(query, params)

                        if updated_count:
                            all_updated_sufficient = True
                            for item in updated_count:
                                material_id = item.get("materialId")
                                material_name = material_dict.get(material_id, f"未知材料({material_id})")
                                total_count = item.get("totalCount", 0)
                                used_count = item.get("usedCount", 0)
                                remaining_count = total_count - used_count

                                if remaining_count < required_times:
                                    all_updated_sufficient = False
                                    self.logger.error(f"[失败] {material_name} 增加后仍不足, 当前剩余: {remaining_count}, 需要: {required_times}")

                            if all_updated_sufficient:
                                self.logger.info(f"[通过] 用户 {user_id} 所有抽奖材料已增加, 可以进行抽奖")
                            else:
                                self.logger.error(f"[失败] 用户 {user_id} 部分抽奖材料增加后仍不足")
                                return False
                        else:
                            self.logger.error(f"[失败] 用户 {user_id} 抽奖材料更新后查询失败")
                            return False

            return True

        except Exception as e:
            self.logger.error(f"[失败] 检查抽奖材料异常: {str(e)}")
            return False

    def get_prize_probabilities(self) -> Dict[str, float]:
        """
        获取奖品概率配置

        Returns:
            Dict[str, float]: 奖品概率映射
        """
        if self.prize_probabilities:
            return self.prize_probabilities

        self.logger.info(f"正在获取的奖品概率配置")
        # self.prize_probabilities = {
        #     "新年大礼包": 0.005,
        #     "锦鲤聚宝盆礼物": 0.02,
        #     "招财金蟾礼物": 0.04,
        #     "闪闪金币礼物": 0.22,
        #     "锦鲤送福进场特效": 0.155,
        #     "新年云间星梦头像框": 0.26,
        #     "新年幻彩星翼头像框": 0.30
        # }
        prize = self.db.execute_query(
            "SELECT name, prob FROM kong_test.activity_material WHERE activityNumber = %s AND activityType = 101",
            (self.activity_number,)
        )
        self.prize_probabilities = {item.get("name"): float(item.get("prob")) for item in prize}
        return self.prize_probabilities

    def call_lottery_api(self, user_id: str, times: int) -> Dict[str, int]:
        """
        调用抽奖API

        Args:
            user_id: 用户ID
            times: 本次抽奖次数

        Returns:
            Dict[str, int]: 抽奖结果，键为奖品名称，值为获得数量
        """
        try:
            auth_sign = self.users[user_id]["sign"]

            params = {
                "num": times,
            }

            response = self.api_client.get(
                url = self.lottery_api,
                params = params,
                headers = {"Content-Type": "application/json", "sign": auth_sign}
            )

            if response.status_code == 200:
                response_json = response.json()

                # 抽奖成功
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

                    self.logger.info(f"用户 {user_id} 抽奖结果: {lottery_result}")
                    return lottery_result
                else:
                    # 抽奖失败
                    error_msg = response_json.get("err", "未知错误")
                    error_code = response_json.get("code", "未知错误")
                    self.logger.error(f"[失败] 用户 {user_id} 抽奖失败, 错误信息: {error_code}, {error_msg}")
                    return {}
            else:
                self.logger.error(f"[失败] 用户 {user_id} 抽奖接口请求失败, 状态码: {response.status_code}, 响应: {response.text}")
                return {}

        except Exception as e:
            self.logger.error(f"[失败] 用户 {user_id} 抽奖接口调用异常: {str(e)}")
            return {}

    def execute_lottery_rounds(self, user_times: Dict[str, int]) -> Tuple[Dict[str, Dict[str, int]], Dict[str, int]]:
        """
        执行抽奖轮次
        支持随机抽奖次数选择，智能处理用户剩余次数不足的情况

        Args:
            user_times: 用户抽奖次数分配

        Returns:
            Tuple: (个人抽奖结果, 全服抽奖结果)
        """
        # 初始化结果存储
        personal_results = {}
        for user_id in user_times.keys():
            personal_results[user_id] = {prize: 0 for prize in self.get_prize_probabilities()}
            personal_results[user_id]["未知奖品"] = 0

        server_results = {prize: 0 for prize in self.get_prize_probabilities()}
        server_results["未知奖品"] = 0

        # 记录每个用户的剩余抽奖次数
        user_remaining_times = user_times.copy()

        # 记录每个用户的连续失败次数
        user_fail_count = {user_id: 0 for user_id in user_times.keys()}
        # 记录失败用户，避免重复选择
        failed_users = set()
        # 最大连续失败次数限制
        max_consecutive_failures = 3
        # 最大循环次数限制，防止无限循环
        max_rounds = self.total_times
        current_round = 0

        self.logger.info(f"开始执行抽奖, 抽奖次数选项: {self.times_options}")

        completed_rounds = 0
        total_completed_times = 0

        def get_optimal_times(userid: str) -> int:
            """
            选择最优抽奖次数

            Args:
                userid: 用户ID

            Returns:
                int: 最优抽奖次数
            """
            user_remaining = user_remaining_times[userid]  # 重命名变量

            # 只剩1次
            if user_remaining <= 1:
                return user_remaining

            # 从times_options中选择不超过用户剩余次数的最大值
            available_times_options = [t for t in self.times_options if t <= user_remaining]
            if not available_times_options:
                return user_remaining

            # 优先选择较大的抽奖次数，减少API调用
            max_option = max(available_times_options)

            # 如果选择最大选项后，剩余次数还能被其他选项整除，则选择最大选项
            remaining_after_max = user_remaining - max_option
            if remaining_after_max == 0:
                return max_option

            # 检查剩余次数是否能被其他选项整除
            for option in sorted(available_times_options, reverse = True):
                if remaining_after_max >= option and remaining_after_max % option == 0:
                    return max_option

            # 如果选择最大选项会导致剩余次数难以分配，尝试次大选项
            if len(available_times_options) > 1:
                second_max = sorted(available_times_options, reverse = True)[1]
                remaining_after_second = user_remaining - second_max
                if remaining_after_second == 0:
                    return second_max
                for option in sorted(available_times_options, reverse = True):
                    if remaining_after_second >= option and remaining_after_second % option == 0:
                        return second_max

            # 默认返回最大可用选项
            return max_option

        while sum(user_remaining_times.values()) > 0 and current_round < max_rounds:
            current_round += 1

            # 选择用户: 优先选择未失败的用户
            available_users = [uid for uid in user_remaining_times.keys()
                               if uid not in failed_users and user_remaining_times[uid] > 0]

            if not available_users:
                # 如果所有用户都失败了，检查是否所有用户都真的无法抽奖
                all_users_failed = True
                for user_id, remaining in user_remaining_times.items():
                    if remaining > 0:
                        # 不再重复检查好运卡，因为已经在抽奖前统一检查过了
                        # 这里只检查是否因为API调用失败而导致的失败
                        if user_fail_count[user_id] < max_consecutive_failures:
                            all_users_failed = False
                            failed_users.discard(user_id)
                            break

                if all_users_failed:
                    self.logger.warning("所有用户都无法抽奖，退出循环")
                    break

                # 重置失败用户集合，重新尝试
                self.logger.warning("所有用户都失败了，重置失败用户集合")
                failed_users.clear()
                available_users = [uid for uid in user_remaining_times.keys()
                                   if user_remaining_times[uid] > 0]

            if not available_users:
                break

            # 随机选择一个用户
            user_id = random.choice(available_users)
            remaining_times = user_remaining_times[user_id]

            if remaining_times <= 0:
                continue

            # 智能选择抽奖次数
            current_times = get_optimal_times(user_id)
            current_times = min(current_times, remaining_times)

            self.logger.info(f"第{completed_rounds + 1}轮: 用户 {user_id}, 抽奖次数: {current_times}")

            # 直接调用抽奖API
            lottery_result = self.call_lottery_api(user_id, current_times)

            if lottery_result:
                # 更新个人抽奖结果
                for prize, count in lottery_result.items():
                    if prize in personal_results[user_id]:
                        personal_results[user_id][prize] += count
                    else:
                        personal_results[user_id]["未知奖品"] += count

                # 更新全服抽奖结果
                for prize, count in lottery_result.items():
                    if prize in server_results:
                        server_results[prize] += count
                    else:
                        server_results["未知奖品"] += count

                # 更新剩余次数
                user_remaining_times[user_id] -= current_times
                total_completed_times += current_times
                completed_rounds += 1

                # 重置失败计数
                user_fail_count[user_id] = 0
                if user_id in failed_users:
                    failed_users.remove(user_id)

                self.logger.info(f"[成功] 第{completed_rounds}轮抽奖完成, 用户 {user_id} 剩余次数: {user_remaining_times[user_id]}")
            else:
                # 抽奖失败
                user_fail_count[user_id] += 1
                self.logger.error(f"[失败] 第{completed_rounds + 1}轮抽奖失败, 用户 {user_id}")

                if user_fail_count[user_id] >= max_consecutive_failures:
                    failed_users.add(user_id)
                    self.logger.warning(f"用户 {user_id} 连续失败次数过多，暂时跳过")

            # 修复: 增加延迟时间到2-2.5秒随机，避免操作太快
            delay_time = random.uniform(2.0, 2.5)
            time.sleep(delay_time)

        # 检查是否因为循环次数过多而退出
        if current_round >= max_rounds:
            self.logger.warning(f"达到最大循环次数限制({max_rounds})，强制退出循环")
            self.logger.info(f"当前剩余抽奖次数: {sum(user_remaining_times.values())}")

        self.logger.info(f"抽奖完成: 共执行 {completed_rounds} 轮, {total_completed_times} 次抽奖")
        return personal_results, server_results

    def calculate_probabilities(self, results: Dict[str, int], total_times: int) -> Dict[str, float]:
        """
        计算实际概率

        Args:
            results: 抽奖结果字典
            total_times: 总抽奖次数

        Returns:
            Dict[str, float]: 实际概率字典
        """
        if total_times == 0:
            return {prize: 0.0 for prize in self.get_prize_probabilities()}

        probabilities = {}
        for prize in self.get_prize_probabilities():
            count = results.get(prize, 0)
            probabilities[prize] = count / total_times

        # 计算未知奖品的概率
        unknown_count = results.get("未知奖品", 0)
        probabilities["未知奖品"] = unknown_count / total_times

        return probabilities

    def validate_probabilities(self, actual_probabilities: Dict[str, float],
                               expected_probabilities: Dict[str, float], total_times: int) -> str:
        """
        验证概率偏差是否在允许范围内

        Args:
            actual_probabilities: 实际概率
            expected_probabilities: 预期概率
            total_times: 总抽奖次数

        Returns:
            str: 是否验证通过
        """
        result = "PASSED"
        if total_times < self.threshold:
            result = "SKIPPED"
            return result

        for prize, expected_prob in expected_probabilities.items():
            actual_prob = actual_probabilities.get(prize, 0.0)
            deviation = abs(actual_prob - float(expected_prob))

            if deviation > self.allowed_deviation:
                self.logger.error(f"[失败] {prize}: 实际 {actual_prob:.2%} → 预期 {expected_prob:.2%} (偏差: {deviation:.2%} > 允许偏差: {self.allowed_deviation:.2%})")
                result = "FAILED"
            else:
                self.logger.info(f"[通过] {prize}: 实际 {actual_prob:.2%} → 预期 {expected_prob:.2%} (偏差: {deviation:.2%}<= 允许偏差: {self.allowed_deviation:.2%})")
        # 验证未知奖品概率
        unknown_prob = actual_probabilities.get("未知奖品", 0.0)
        if unknown_prob > 0.01:
            self.logger.warning(f"未知奖品概率较高: {unknown_prob:.2%}")

        return result

    def validate(self) -> bool:
        """
        执行完整的概率验证流程

        Returns:
            bool: 验证是否通过
        """
        self.logger.info("开始多用户抽奖概率验证")

        # 登录所有用户
        if not self.login_all_users():
            self.logger.error("所有用户登录失败，无法继续验证")
            return False

        # 分配抽奖次数
        user_times = self.distribute_lottery_times()
        if not user_times:
            self.logger.error("抽奖次数分配失败，无法继续验证")
            return False

        # 检查抽奖次数
        check = self.check_and_update_user_lottery_times(user_times)
        if not check:
            self.logger.error("抽奖次数不满足要求，无法继续验证")
            return False

        # 执行抽奖
        personal_results, server_results = self.execute_lottery_rounds(user_times)

        total_server_times = sum(server_results.values())
        if total_server_times == 0:
            self.logger.error("抽奖执行失败，没有有效的抽奖结果")
            return False
        else:
            self.logger.info(f"=== 最终抽奖结果 ===")
            if self.validation_mode in ["BOTH", "SERVER"]:
                self.logger.info(f"全服:{server_results}")
            if self.validation_mode in ["BOTH", "PERSONAL"] and personal_results:
                for user_id, user_results in personal_results.items():
                    self.logger.info(f"用户{user_id}:{user_results}")

        # 计算概率
        expected_probabilities = self.get_prize_probabilities()
        actual_server_probabilities = self.calculate_probabilities(server_results, total_server_times)

        # 验证全服概率
        if self.validation_mode in ["BOTH", "SERVER"]:
            self.logger.info("=== 全服概率验证 ===")
            server_valid = True
            result = self.validate_probabilities(actual_server_probabilities, expected_probabilities, total_server_times)
            if result == "FAILED":
                server_valid = False
                self.logger.error("❌ 全服概率验证失败")
            elif result == "PASSED":
                self.logger.info("✅ 全服概率验证通过")
            else:
                server_valid = False
                self.logger.warning("⚠️ 总抽奖次数低于阈值，跳过全服概率验证")

        # 验证个人概率
        if self.validation_mode in ["BOTH", "PERSONAL"]:
            self.logger.info("=== 个人概率验证 ===")
            personal_valid = True
            for user_id, user_results in personal_results.items():
                user_total_times = sum(user_results.values())
                if user_total_times > 0:
                    self.logger.info(f"开始验证用户 {user_id} 个人概率...")
                    user_probabilities = self.calculate_probabilities(user_results, user_total_times)
                    user_valid = self.validate_probabilities(user_probabilities, expected_probabilities, user_total_times)
                    if user_valid == "FAILED":
                        personal_valid = False
                        self.logger.error(f"❌ 用户 {user_id} 个人概率验证失败")
                    elif user_valid == "PASSED":
                        self.logger.info(f"✅ 用户 {user_id} 个人概率验证通过")
                    else:
                        self.logger.warning(f"⚠️ 用户 {user_id} 个人概率验证跳过")
                else:
                    self.logger.warning(f"⚠️ 用户 {user_id} 没有有效的抽奖结果，跳过个人概率验证")

        # 验证结果
        self.logger.info("=== 最终验证结果 ===")
        if self.validation_mode == "SERVER":
            final_valid = server_valid
        elif self.validation_mode == "PERSONAL":
            final_valid = personal_valid
        else:
            final_valid = server_valid and personal_valid

        if final_valid:
            self.logger.info("✅ 概率验证通过!")
            return True
        else:
            self.logger.error("❌ 概率验证失败!")
            return False


def main():
    """主函数"""
    # 测试账号
    # accounts = [
    #     {"mobile": "17370000002", "password": "123456"},
    #     {"mobile": "17370000003", "password": "123456"},
    #     {"mobile": "17370000004", "password": "123456"},
    # ]
    test_user_account = FileHandler().read_yaml("test_data/test_user_account.yaml")
    accounts = test_user_account[1:4]

    # 创建验证器实例
    validator = MultiUserLotteryProbabilityValidator(
        activity_number = 1054,
        lottery_api = "/api/activity/20251223/buildTree",
        accounts = accounts,
        total_times = 50,
        user_times_range = [10, 30],
        times_options = [1, 10, 50],
        allowed_deviation = 0.05,
        threshold = 20
    )

    # 执行验证
    success = validator.validate()
    return success


if __name__ == "__main__":
    main()
