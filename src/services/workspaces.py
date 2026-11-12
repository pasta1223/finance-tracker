"""Presentation and category choices for each account type."""

PROFILES = {
    "personal": {
        "title": "个人财务", "income": "个人收入", "expense": "个人支出", "balance": "个人结余",
        "income_categories": ["工资", "奖金", "投资收益", "兼职", "其他收入"],
        "expense_categories": ["餐饮", "交通", "购物", "住房", "医疗", "教育", "娱乐", "通讯", "其他支出"],
        "hint": "管理个人收支、分类预算和结余趋势。",
    },
    "family": {
        "title": "家庭财务", "income": "家庭收入", "expense": "家庭支出", "balance": "家庭结余",
        "income_categories": ["家庭工资", "奖金", "投资收益", "其他家庭收入"],
        "expense_categories": ["日常餐饮", "房租房贷", "水电物业", "子女教育", "医疗健康", "交通出行", "家庭购物", "休闲旅行", "其他家庭支出"],
        "hint": "家庭成员共享账本和预算；可按记录人查看各成员收支。",
    },
    "shop": {
        "title": "小商铺经营", "income": "营业收入", "expense": "经营支出", "balance": "经营净现金流",
        "income_categories": ["商品销售", "服务收入", "其他营业收入"],
        "expense_categories": ["采购进货", "店铺租金", "员工工资", "水电费用", "物流运输", "营销推广", "税费", "其他经营支出"],
        "hint": "记录营业收入、采购和经营费用，查看经营现金流。",
    },
}
