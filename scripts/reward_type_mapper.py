"""
-------------------------------------------------
File:           reward_type_mapper.py
Author:         duanyang
Date:           2026/1/20
-------------------------------------------------
Description:
This file contains the reward_type_mapper module, which...
-------------------------------------------------
"""
from typing import Dict


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
            1359: "两位自选靓号",
            1358: "三位自选靓号",
            833: "四位自选靓号",
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
        14: {"name": "ENTER_EFFECTS", "desc": "进场特效"},
        15: {"name": "TITLE", "desc": "荣誉称号"},
        16: {"name": "DUKE_NOBLE", "desc": "公爵贵族"},
        17: {"name": "VISCOUNT_NOBLE", "desc": "子爵贵族"},
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
    def get_reward_type_extend(cls, reward_type: int) -> Dict[int, str]:
        """根据奖励类型ID获取扩展信息"""
        return cls.REWARD_TYPE_MAPPING.get(reward_type, {}).get("extend", {})

    @classmethod
    def validate_reward_type(cls, reward_type: int) -> bool:
        """验证奖励类型是否有效"""
        return reward_type in cls.REWARD_TYPE_MAPPING
