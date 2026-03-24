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
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from config.config_manager import config_manager
from utils import util
from utils.api.api_client import ApiClient
from utils.db.mysql_client import MySQLClient
from utils.file import FileHandler
from utils.logger import logger


class MultiUserLotteryProbabilityValidator:
    """
    多用户抽奖概率验证器
    支持两种抽奖类型: 消耗抽奖材料和直接消耗抽奖次数
    支持全服概率和个人概率计算
    """

    def __init__(
            self,
            accounts: List[Dict[str, str]],
            lottery_type: str = "COUPON",  # "COUPON" 或 "MATERIAL"
            prize_probabilities: Optional[Dict[str, float]] = None,
            allowed_deviation: float = 0.05,
            lottery_api: str = "/api/activity/lottery/start",
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
            accounts: 账号信息列表, 每个账号包含用户名和密码
            lottery_type: 抽奖类型, "COUPON"表示消耗抽奖次数, "MATERIAL"表示消耗抽奖材料
            prize_probabilities: 奖品与预期概率映射, 默认为None(从数据库获取)
            allowed_deviation: 允许的实际概率偏差绝对值, 默认为0.5
            lottery_api: 抽奖接口URL
            threshold: 抽奖次数阈值, 低于此值跳过概率校验, 默认为50
            times_options: 抽奖次数选项列表, 默认为[1, 10, 50]
            total_times: 抽奖总次数, 默认为100
            activity_number: 活动编号, 默认为1054
            activity_type: 活动类型, 默认为10
            user_times_range: 每个用户抽奖次数范围, 默认为[10, 100]
            validation_mode: 验证模式, "BOTH"表示全服+个人, "SERVER"表示仅全服, "PERSONAL"表示仅个人, 默认为"BOTH"
        """
        self.accounts = accounts
        self.lottery_type = lottery_type.upper()
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

        self.db = MySQLClient(config_manager.get_mysql_config())

        # 添加线程安全锁
        self._probability_lock = threading.Lock()
        self._db_lock = threading.Lock()

    def login_all_users(self) -> bool:
        """
        登录所有用户

        Returns:
            bool: 是否所有用户都登录成功
        """
        self.logger.info(f"开始登录 {len(self.accounts)} 个用户")

        # 线程安全锁, 保护self.users字典
        users_lock = threading.Lock()
        success_count = 0

        def login_task(account):
            """登录任务函数"""
            nonlocal success_count
            try:
                # 创建临时ApiClient实例用于登录
                login_api_client = ApiClient()
                try:
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
                        return False, account

                    # 发送登录请求
                    login_data = {
                        "mobile": account["mobile"],
                        "password": account["password"]
                    }

                    response = login_api_client.post(
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

                            # 线程安全地更新用户字典
                            with users_lock:
                                self.users[user_info["user_id"]] = user_info
                                nonlocal success_count
                                success_count += 1

                            self.logger.info(f"[成功] 账号: {user_info['user_id']} - {user_info['nick']} 登录成功")
                            return True, account
                        else:
                            self.logger.error(f"[失败] 登录失败: {resp_json.get('code', '未知错误')}")
                            return False, account
                    else:
                        self.logger.error(f"[失败] 登录异常: {response.status_code}")
                        return False, account
                finally:
                    # 关闭临时ApiClient实例
                    login_api_client.close()
                    return True, account
            except Exception as exp:
                self.logger.error(f"[失败] 登录异常: {str(exp)}")
                return False, account

        # 使用线程池执行并发登录
        # 线程池大小设置为用户数量, 最多不超过20
        max_workers = min(len(self.accounts), 20)

        with ThreadPoolExecutor(max_workers = max_workers, thread_name_prefix = "LoginThread") as executor:
            # 提交任务到线程池
            future_to_account = {executor.submit(login_task, account): account for account in self.accounts}

            # 收集任务结果
            for future in as_completed(future_to_account):
                account = future_to_account[future]
                try:
                    success, _ = future.result()
                    if not success:
                        self.logger.error(f"用户 {account['mobile']} 登录失败")
                except Exception as e:
                    self.logger.error(f"用户 {account['mobile']} 登录任务执行失败: {str(e)}")
        
        self.logger.info(f"用户登录完成: {success_count}/{len(self.accounts)} 个用户登录成功")
        return success_count > 0

    def distribute_lottery_times(self) -> Dict[str, int]:
        """
        随机分配抽奖次数给登录成功的用户

        Returns:
            Dict[str, int]: 用户ID到抽奖次数的映射
        """
        user_ids = list(self.users.keys())
        user_count = len(user_ids)

        # 无用户直接返回空字典
        if user_count == 0:
            self.logger.info("无登录用户, 抽奖次数分配结果为空")
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

        # 基础分配, 每人先给最小次数
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
                # 用户已达上限, 则不再分配
                if max_add <= 0:
                    available_users.remove(selected_user)
                    continue

                # 本次分配次数: 随机1~(剩余次数和最大可加次数的最小值), 批量分配
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
        检查并更新用户的抽奖次数/材料是否足够

        Args:
            user_times: 用户ID到需要的抽奖次数的映射

        Returns:
            bool: 抽奖次数/材料是否足够
        """
        try:
            if self.lottery_type == "COUPON":
                return self._check_coupon_times(user_times)
            else:  # MATERIAL
                return self._check_material_times(user_times)
        except Exception as e:
            self.logger.error(f"[失败] 检查抽奖次数/材料异常: {str(e)}")
            return False

    def _check_coupon_times(self, user_times: dict[str, int]) -> bool:
        """
        检查并更新抽奖次数(COUPON类型)
        Args:
            user_times: 用户ID到需要的抽奖次数的映射

        Returns:
            bool: 抽奖次数是否足够
        """
        for user_id, required_times in user_times.items():
            self.logger.info(f"正在查询用户 {user_id} 的抽奖次数")

            count = self.db.get_one(
                "SELECT totalCount, usedCount FROM `kong_test`.`activity_coupon_count` WHERE activityNumber = %s AND userId = %s",
                (self.activity_number, user_id)
            )

            if count:
                total_count = count.get("totalCount", 0)
                used_count = count.get("usedCount", 0)
                remaining_count = total_count - used_count

                self.logger.info(f"账号: {user_id} 当前剩余抽奖次数: {remaining_count}, 需要: {required_times}")

                if remaining_count >= required_times:
                    self.logger.info(f"[通过] 账号: {user_id} 抽奖次数足够, 可以直接抽奖")
                else:
                    # 更新抽奖次数
                    need_add = required_times - remaining_count
                    self.logger.info(f"[调整] 账号: {user_id} 抽奖次数不足, 需要增加 {need_add} 次")

                    self.db.execute_update(
                        "UPDATE `kong_test`.`activity_coupon_count` SET totalCount = totalCount + %s WHERE activityNumber = %s AND userId = %s",
                        (need_add, self.activity_number, user_id),
                    )

                    # 重新查询确认
                    updated_count = self.db.get_one(
                        "SELECT totalCount, usedCount FROM `kong_test`.`activity_coupon_count` WHERE activityNumber = %s AND userId = %s",
                        (self.activity_number, user_id)
                    )

                    if updated_count:
                        updated_remaining = updated_count.get("totalCount", 0) - updated_count.get("usedCount", 0)
                        if updated_remaining >= required_times:
                            self.logger.info(f"[通过] 账号: {user_id} 抽奖次数已增加, 当前剩余: {updated_remaining}")
                        else:
                            self.logger.error(f"[失败] 账号: {user_id} 抽奖次数增加后仍不足")
                            return False
                    else:
                        self.logger.error(f"[失败] 账号: {user_id} 抽奖次数更新后查询失败")
                        return False
            else:
                # 如果没有记录, 则插入记录
                self.logger.info(f"账号: {user_id} 没有抽奖次数记录, 正在创建")

                self.db.execute_update(
                    "INSERT INTO `kong_test`.`activity_coupon_count` (activityNumber, activityType, userId, totalCount, usedCount, created, updated) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (self.activity_number, str(self.activity_type), user_id, required_times, 0, util.current_time(),
                     util.current_time()),
                )

                self.logger.info(f"[通过] 账号: {user_id} 抽奖次数记录已创建")

        return True

    def _check_material_times(self, user_times: dict[str, int]) -> bool:
        """
        检查并更新抽奖材料(MATERIAL类型)
        Args:
            user_times: 用户ID到需要的抽奖材料次数的映射

        Returns:
            bool: 抽奖材料是否足够
        """
        # 获取所有抽奖材料ID
        material = self.db.execute_query(
            "SELECT id, name FROM kong_test.activity_material WHERE activityNumber = %s AND activityType = %s",
            (self.activity_number, self.activity_type)
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

        # 构建查询语句
        placeholders = ','.join(['%s'] * len(material_id_list))
        count_query = f"SELECT materialId, totalCount, usedCount FROM `kong_test`.`activity_material_count` WHERE materialId IN ({placeholders}) and userId = %s"

        # 构建插入语句
        insert_query = "INSERT INTO `kong_test`.`activity_material_count` (materialId, userId, totalCount, usedCount, type, created, updated) VALUES (%s, %s, %s, %s, %s, %s, %s)"

        # 构建更新语句
        update_query = "UPDATE `kong_test`.`activity_material_count` SET totalCount = totalCount + %s WHERE materialId = %s AND userId = %s"

        for user_id, required_times in user_times.items():
            self.logger.info(f"正在查询用户 {user_id} 的抽奖材料数量")

            # 查询用户所有抽奖材料数量
            params = tuple(material_id_list) + (user_id,)
            count = self.db.execute_query(count_query, params)

            # 确保每种材料当前数量和需要的数量匹配
            existing_material_ids = {item.get("materialId") for item in count} if count else set()
            all_material_ids = set(material_id_list)
            missing_material_ids = all_material_ids - existing_material_ids

            # 有缺失的抽奖材料则在数据库中创建材料记录
            if missing_material_ids:
                self.logger.info(f"用户 {user_id} 缺少 {len(missing_material_ids)} 种抽奖材料, 正在创建...")
                for material_id in missing_material_ids:
                    material_name = material_dict.get(material_id, f"未知抽奖材料({material_id})")
                    self.db.execute_update(
                        insert_query,
                        (material_id, user_id, required_times, 0, '8', util.current_time(), util.current_time()),
                    )
                    self.logger.info(f"[新增] 已为用户 {user_id} 的 {material_name} 创建记录, 初始数量: {required_times}")

            # 计算需要更新的材料
            count_dict = {item.get("materialId"): item for item in count} if count else {}
            need_update_materials = []

            for material_id in all_material_ids:
                material_name = material_dict.get(material_id, f"未知材料({material_id})")

                if material_id in count_dict:
                    # 已有记录, 检查数量
                    item = count_dict[material_id]
                    total_count = item.get("totalCount", 0)
                    used_count = item.get("usedCount", 0)
                    usable_count = total_count - used_count
                else:
                    # 新创建的记录, 数量足够
                    usable_count = required_times

                self.logger.info(f"用户 {user_id} 当前{material_name}剩余数量: {usable_count}, 需要: {required_times}")

                if usable_count < required_times:
                    need_add = required_times - usable_count
                    need_update_materials.append({
                        'material_id': material_id,
                        'material_name': material_name,
                        'need_add': need_add
                    })
                    self.logger.info(f"[调整] {material_name} 数量不足, 需要增加 {need_add} 个")

            if not need_update_materials:
                self.logger.info(f"[通过] 用户 {user_id} 所有抽奖材料都足够, 可以直接抽奖")
            else:
                # 更新不足的抽奖材料数量
                for material_info in need_update_materials:
                    material_id = material_info['material_id']
                    material_name = material_info['material_name']
                    need_add = material_info['need_add']

                    self.logger.info(f"[调整] 正在为用户 {user_id} 的 {material_name} 增加 {need_add} 个")
                    self.db.execute_update(
                        update_query,
                        (need_add, material_id, user_id),
                    )

                self.logger.info(f"[通过] 用户 {user_id} 所有抽奖材料已增加, 可以进行抽奖")

        return True

    def get_prize_probabilities(self) -> Dict[str, float]:
        """
        获取奖品概率配置

        Returns:
            Dict[str, float]: 奖品概率映射
        """
        # 双重检查锁定模式, 避免重复查询
        if self.prize_probabilities:
            return self.prize_probabilities

        with self._probability_lock:
            # 再次检查, 确保其他线程没有已经初始化
            if self.prize_probabilities:
                return self.prize_probabilities

            self.logger.info(f"正在获取活动 {self.activity_number} 的奖品概率配置")
            try:
                # 从数据库中获取奖品概率配置
                with self._db_lock:
                    query = "SELECT name, prob FROM kong_test.activity_material WHERE activityNumber = %s AND activityType = %s"
                    prize = self.db.execute_query(query, (self.activity_number, self.activity_type))

                if prize:
                    self.prize_probabilities = {item.get("name"): float(item.get("prob")) for item in prize}
                    self.logger.info(f"成功从数据库获取奖品概率配置: {self.prize_probabilities}")
                else:
                    self.logger.warning(f"未从数据库获取到活动 {self.activity_number} 的奖品概率配置")
                    self.prize_probabilities = {}
            except Exception as e:
                # 查询数据库失败
                self.logger.error(f"从数据库获取奖品概率配置失败: {str(e)}")
                self.prize_probabilities = {}

            return self.prize_probabilities

    def _user_lottery_task(self, user_id: str, required_times: int, result_lock: threading.Lock) -> Dict[str, int]:
        """
        单个用户的抽奖任务
        
        Args:
            user_id: 用户ID
            required_times: 该用户需要完成的抽奖次数
            result_lock: 结果合并锁
        
        Returns:
            Dict[str, int]: 该用户的抽奖结果
        """
        # 为每个线程创建独立的ApiClient实例
        thread_api_client = ApiClient()

        user_results = {prize: 0 for prize in self.get_prize_probabilities()}
        user_results["未知奖品"] = 0

        remaining_times = required_times
        completed_times = 0
        consecutive_failures = 0
        max_consecutive_failures = 3

        def get_optimal_times(remaining: int) -> int:
            """
            选择最优抽奖次数
            """
            if remaining <= 1:
                return remaining
            
            # 从times_options中选择不超过用户剩余次数的最大值
            available_times_options = [t for t in self.times_options if t <= remaining]
            if not available_times_options:
                return remaining

            # 优先选择较大的抽奖次数, 减少API调用
            max_option = max(available_times_options)

            return max_option

        while remaining_times > 0 and consecutive_failures < max_consecutive_failures:
            # 选择抽奖次数
            current_times = get_optimal_times(remaining_times)
            current_times = min(current_times, remaining_times)

            self.logger.info(f"用户 {user_id}: 执行 {current_times} 次抽奖, 剩余 {remaining_times} 次")

            # 调用抽奖API (使用当前线程的ApiClient实例)
            try:
                auth_sign = self.users[user_id]["sign"]

                # 抽奖请求参数
                if self.lottery_type == "COUPON":
                    params = {
                        "times": current_times,
                        "number": self.activity_number,
                    }
                else:  # MATERIAL
                    params = {
                        "num": current_times,
                    }

                response = thread_api_client.get(
                    url = self.lottery_api,
                    params = params,
                    headers = {"Content-Type": "application/json", "sign": auth_sign}
                )

                lottery_result = {}
                if response.status_code == 200:
                    response_json = response.json()

                    # 抽奖成功
                    if response_json.get("code") == 200:
                        data = response_json.get("data", [])
                        if data and len(data) > 0:
                            for item in data:
                                prize_name = item.get("name", "未知奖品")
                                count = item.get("rewardCount", 0)
                                if prize_name in lottery_result:
                                    lottery_result[prize_name] += count
                                else:
                                    lottery_result[prize_name] = count
                        self.logger.info(f"用户 {user_id} 抽奖成功, 奖品: {lottery_result}")
                    else:
                        # 抽奖失败, 根据错误码进行分类处理
                        error_msg = response_json.get("err", "未知错误")
                        error_code = response_json.get("code", "未知错误")

                        # 不可重试错误码列表
                        retryable_codes = [10059]

                        if error_code not in retryable_codes:
                            self.logger.warning(f"[可重试] 用户 {user_id} 抽奖失败, 错误信息: {error_code}, {error_msg} - 将重试")
                        else:
                            self.logger.error(f"[不可重试] 用户 {user_id} 抽奖失败, 错误信息: {error_code}, {error_msg} - 停止重试")
                            consecutive_failures = max_consecutive_failures
                else:
                    # HTTP状态码错误
                    self.logger.error(f"[HTTP错误] 用户 {user_id} 抽奖接口请求失败, 状态码: {response.status_code}, 响应: {response.text}")
            except Exception as e:
                # 通用异常处理
                error_str = str(e)
                if "timeout" in error_str.lower() or "time out" in error_str.lower():
                    self.logger.warning(f"[超时错误] 用户 {user_id} 抽奖请求超时: {error_str} - 将重试")
                    lottery_result = {}
                elif any(keyword in error_str.lower() for keyword in ["connection", "network", "connect", "socket"]):
                    self.logger.warning(f"[网络异常] 用户 {user_id} 抽奖网络请求异常: {error_str} - 将重试")
                    lottery_result = {}
                else:
                    # 其他未知异常
                    self.logger.error(f"[未知异常] 用户 {user_id} 抽奖接口调用异常: {error_str} - 停止重试")
                    lottery_result = {}
                    consecutive_failures = max_consecutive_failures  # 标记为不可重试, 加速退出
            
            if lottery_result:
                # 更新用户抽奖结果
                with result_lock:
                    for prize, count in lottery_result.items():
                        if prize in user_results:
                            user_results[prize] += count
                        else:
                            user_results["未知奖品"] += count
                
                # 更新剩余次数
                remaining_times -= current_times
                completed_times += current_times
                consecutive_failures = 0

                self.logger.info(f"[成功] 用户 {user_id} 完成 {completed_times} 次抽奖, 剩余 {remaining_times} 次")
            else:
                # 抽奖失败
                consecutive_failures += 1
                self.logger.error(f"[失败] 用户 {user_id} 抽奖失败, 连续失败 {consecutive_failures} 次")

            # 增加延迟时间到2-2.5秒随机, 避免操作太快
            delay_time = random.uniform(2.0, 2.5)
            time.sleep(delay_time)

        if consecutive_failures >= max_consecutive_failures:
            self.logger.warning(f"用户 {user_id} 连续失败次数过多({max_consecutive_failures}), 停止抽奖")

        if remaining_times > 0:
            self.logger.warning(f"用户 {user_id} 未完成全部抽奖次数, 剩余 {remaining_times} 次")

        # 关闭当前线程的ApiClient实例
        thread_api_client.close()

        return user_results

    def execute_lottery_rounds(self, user_times: Dict[str, int]) -> Tuple[Dict[str, Dict[str, int]], Dict[str, int]]:
        """
        执行抽奖轮次
        支持多线程并发抽奖

        Args:
            user_times: 用户抽奖次数分配

        Returns:
            Tuple: (个人抽奖结果, 全服抽奖结果)
        """
        # 初始化结果存储
        personal_results = {}
        server_results = {prize: 0 for prize in self.get_prize_probabilities()}
        server_results["未知奖品"] = 0

        result_lock = threading.Lock()
        total_completed_times = 0

        self.logger.info(f"开始执行并发抽奖, 最大并发数: {len(user_times)}")
        self.logger.info(f"抽奖次数选项: {self.times_options}")

        # 使用线程池执行并发抽奖
        # 线程池大小设置为用户数量, 最多不超过20
        max_workers = min(len(user_times), 20)

        with ThreadPoolExecutor(max_workers = max_workers, thread_name_prefix = "LotteryThread") as executor:
            # 提交任务到线程池
            future_to_user = {}
            for user_id, required_times in user_times.items():
                future = executor.submit(
                    self._user_lottery_task,
                    user_id,
                    required_times,
                    result_lock
                )
                future_to_user[future] = user_id

            # 收集结果
            for future in as_completed(future_to_user):
                user_id = future_to_user[future]
                try:
                    user_result = future.result()
                    personal_results[user_id] = user_result

                    # 合并到全服结果
                    with result_lock:
                        for prize, count in user_result.items():
                            if prize in server_results:
                                server_results[prize] += count
                            else:
                                server_results["未知奖品"] += count
                        total_completed_times += sum(user_result.values())
                except Exception as e:
                    self.logger.error(f"用户 {user_id} 抽奖任务执行失败: {str(e)}")
                    personal_results[user_id] = {prize: 0 for prize in self.get_prize_probabilities()}
                    personal_results[user_id]["未知奖品"] = 0

        self.logger.info(f"并发抽奖完成: 共完成 {total_completed_times} 次抽奖")
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
            self.logger.error("所有用户登录失败, 无法继续验证")
            return False

        # 分配抽奖次数
        user_times = self.distribute_lottery_times()
        if not user_times:
            self.logger.error("抽奖次数分配失败, 无法继续验证")
            return False

        # 检查抽奖次数
        check = self.check_and_update_user_lottery_times(user_times)
        if not check:
            self.logger.error("抽奖次数不满足要求, 无法继续验证")
            return False

        # 执行抽奖
        personal_results, server_results = self.execute_lottery_rounds(user_times)

        total_server_times = sum(server_results.values())
        if total_server_times == 0:
            self.logger.error("抽奖执行失败, 没有有效的抽奖结果")
            return False
        else:
            self.logger.info(f"=== 最终抽奖结果 ===")
            if self.validation_mode in ["BOTH", "SERVER"]:
                self.logger.info(f"全服: {server_results}")
            if self.validation_mode in ["BOTH", "PERSONAL"] and personal_results:
                for user_id, user_results in personal_results.items():
                    self.logger.info(f"用户{user_id}: {user_results}")

        # 计算概率
        expected_probabilities = self.get_prize_probabilities()
        actual_server_probabilities = self.calculate_probabilities(server_results, total_server_times)

        # 初始验证结果
        server_valid = True
        personal_valid = True

        # 验证全服概率
        if self.validation_mode in ["BOTH", "SERVER"]:
            self.logger.info("=== 全服概率验证 ===")
            result = self.validate_probabilities(actual_server_probabilities, expected_probabilities, total_server_times)
            if result == "FAILED":
                server_valid = False
                self.logger.error("❌ 全服概率验证失败")
            elif result == "PASSED":
                self.logger.info("✅ 全服概率验证通过")
            else:
                server_valid = False
                self.logger.warning("⚠️ 总抽奖次数低于阈值, 跳过全服概率验证")

        # 验证个人概率
        if self.validation_mode in ["BOTH", "PERSONAL"]:
            self.logger.info("=== 个人概率验证 ===")
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
                    self.logger.warning(f"⚠️ 用户 {user_id} 没有有效的抽奖结果, 跳过个人概率验证")

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
    test_user_account = FileHandler().read_yaml("test_data/test_user_account.yaml")
    accounts = test_user_account[1:4]

    validator = MultiUserLotteryProbabilityValidator(
        lottery_type = "COUPON",
        activity_number = 1055,
        lottery_api = "/api/activity/lottery/start",
        accounts = accounts,
        total_times = 20,
        user_times_range = [5, 10],
        times_options = [1, 10, 50],
        allowed_deviation = 0.02,
        threshold = 500
    )

    # 执行验证
    success = validator.validate()
    return success


if __name__ == "__main__":
    main()
