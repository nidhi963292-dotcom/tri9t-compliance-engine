# app/models.py
from sqlalchemy.orm import DeclarativeBase

# 1. Define the Base class that main.py is looking for
class Base(DeclarativeBase):
    pass

# Your other models below should inherit from this Base
# Example:
# class ComplianceRule(Base):
#     __tablename__ = "compliance_rules"
#     ...