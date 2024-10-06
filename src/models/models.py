from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func, BigInteger
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import UniqueConstraint

Base = declarative_base()

class UserModel(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, nullable=False, unique=True)
    username = Column(String, nullable=True)

    categories = relationship("CategoryModel", back_populates="user")
    tasks = relationship("TaskModel", back_populates="user")
    reminders = relationship("ReminderModel", back_populates="user", cascade="all, delete-orphan")


class CategoryModel(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)

    user = relationship("UserModel", back_populates="categories")
    tasks = relationship("TaskModel", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_user_category_name'),)


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)

    category = relationship("CategoryModel", back_populates="tasks")
    user = relationship("UserModel", back_populates="tasks")


class ReminderModel(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(TIMESTAMP, nullable=False)
    description = Column(String, nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)

    user = relationship("UserModel", back_populates="reminders")
