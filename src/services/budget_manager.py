"""
预算管理模块
支持设置月度预算、预算分类和预算提醒
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, List
from dataclasses import dataclass

from ..exceptions.custom_exceptions import ValidationError


@dataclass
class Budget:
    """预算对象"""
    category: str
    amount: Decimal
    month: int
    year: int
    spent: Decimal = Decimal('0')
    
    @property
    def remaining(self) -> Decimal:
        """剩余预算"""
        return self.amount - self.spent
    
    @property
    def usage_percentage(self) -> float:
        """使用百分比"""
        if self.amount == 0:
            return 0.0
        return float(self.spent / self.amount * 100)
    
    @property
    def is_exceeded(self) -> bool:
        """是否超支"""
        return self.spent > self.amount


class BudgetManager:
    """
    预算管理器
    管理月度预算和分类预算
    
    时间复杂度分析：
    - 设置预算: O(1)
    - 更新支出: O(1)
    - 获取预算状态: O(1)
    - 获取月度总预算: O(n)，n为分类数量
    """
    
    def __init__(self):
        # 分类预算: {(category, year, month): Budget}
        self._category_budgets: Dict[tuple, Budget] = {}
        # 月度总预算: {(year, month): Decimal}
        self._monthly_budgets: Dict[tuple, Decimal] = {}
        # 预算警告阈值
        self._alert_threshold: float = 80.0  # 80%
    
    def set_monthly_budget(self, year: int, month: int, amount: Decimal) -> None:
        """设置月度总预算"""
        if amount < 0:
            raise ValidationError("amount", "预算金额不能为负数")
        
        self._monthly_budgets[(year, month)] = amount
    
    def set_category_budget(
        self,
        category: str,
        year: int,
        month: int,
        amount: Decimal
    ) -> Budget:
        """设置分类预算"""
        if amount < 0:
            raise ValidationError("amount", "预算金额不能为负数")
        
        budget = Budget(
            category=category,
            amount=amount,
            month=month,
            year=year,
            spent=Decimal('0')
        )
        
        self._category_budgets[(category, year, month)] = budget
        return budget
    
    def update_category_spending(
        self,
        category: str,
        year: int,
        month: int,
        spent: Decimal
    ) -> None:
        """更新分类支出"""
        key = (category, year, month)
        if key in self._category_budgets:
            self._category_budgets[key].spent = spent
    
    def add_category_spending(
        self,
        category: str,
        year: int,
        month: int,
        amount: Decimal
    ) -> None:
        """增加分类支出"""
        key = (category, year, month)
        if key in self._category_budgets:
            self._category_budgets[key].spent += amount
    
    def get_category_budget(
        self,
        category: str,
        year: int,
        month: int
    ) -> Optional[Budget]:
        """获取分类预算"""
        return self._category_budgets.get((category, year, month))
    
    def get_monthly_budget(self, year: int, month: int) -> Optional[Decimal]:
        """获取月度总预算"""
        return self._monthly_budgets.get((year, month))
    
    def get_all_category_budgets(self, year: int, month: int) -> List[Budget]:
        """获取指定月份所有分类预算"""
        return [
            budget for (cat, y, m), budget in self._category_budgets.items()
            if y == year and m == month
        ]
    
    def check_budget_alerts(
        self,
        year: int,
        month: int,
        current_spending: Decimal
    ) -> List[str]:
        """
        检查预算警告
        
        :return: 警告消息列表
        """
        alerts = []
        
        # 检查月度总预算
        monthly_budget = self.get_monthly_budget(year, month)
        if monthly_budget and monthly_budget > 0:
            pct = float(current_spending / monthly_budget * 100)
            if pct >= 100:
                alerts.append(f"[严重] 月度总预算已超支! 已用 {pct:.1f}%")
            elif pct >= self._alert_threshold:
                alerts.append(f"[警告] 月度总预算使用已达 {pct:.1f}%，注意控制支出")
        
        # 检查分类预算
        for budget in self.get_all_category_budgets(year, month):
            if budget.usage_percentage >= 100:
                alerts.append(f"[严重] 分类 '{budget.category}' 预算已超支!")
            elif budget.usage_percentage >= self._alert_threshold:
                alerts.append(
                    f"[警告] 分类 '{budget.category}' 预算使用已达 {budget.usage_percentage:.1f}%"
                )
        
        return alerts
    
    def get_budget_summary(self, year: int, month: int) -> Dict:
        """获取预算摘要"""
        category_budgets = self.get_all_category_budgets(year, month)
        monthly_budget = self.get_monthly_budget(year, month)
        
        return {
            "year": year,
            "month": month,
            "monthly_budget": monthly_budget or Decimal('0'),
            "category_count": len(category_budgets),
            "category_budgets": category_budgets,
            "exceeded_count": sum(1 for b in category_budgets if b.is_exceeded),
            "warning_count": sum(
                1 for b in category_budgets 
                if b.usage_percentage >= self._alert_threshold and not b.is_exceeded
            )
        }
    
    def set_alert_threshold(self, threshold: float) -> None:
        """设置警告阈值"""
        if 0 <= threshold <= 100:
            self._alert_threshold = threshold
        else:
            raise ValidationError("threshold", "阈值必须在0-100之间")

    def clear(self) -> None:
        """Reset every budget while preserving the manager instance."""
        self._category_budgets.clear()
        self._monthly_budgets.clear()
        self._alert_threshold = 80.0
    
    # ==================== 序列化 ====================
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "category_budgets": [
                {
                    "category": b.category,
                    "amount": str(b.amount),
                    "spent": str(b.spent),
                    "year": b.year,
                    "month": b.month
                }
                for b in self._category_budgets.values()
            ],
            "monthly_budgets": {
                f"{y}-{m}": str(amount)
                for (y, m), amount in self._monthly_budgets.items()
            },
            "alert_threshold": self._alert_threshold
        }
    
    def from_dict(self, data: Dict) -> None:
        """从字典加载"""
        self._category_budgets.clear()
        self._monthly_budgets.clear()
        
        for b_data in data.get("category_budgets", []):
            budget = Budget(
                category=b_data["category"],
                amount=Decimal(b_data["amount"]),
                spent=Decimal(b_data["spent"]),
                year=b_data["year"],
                month=b_data["month"]
            )
            self._category_budgets[(budget.category, budget.year, budget.month)] = budget
        
        for key, value in data.get("monthly_budgets", {}).items():
            year, month = map(int, key.split('-'))
            self._monthly_budgets[(year, month)] = Decimal(value)
        
        self._alert_threshold = data.get("alert_threshold", 80.0)
