from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TestRun(Base):
    __tablename__ = "test_run"

    # unique run ID
    id = Column(Integer, primary_key=True)

    # pytest data
    session_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    originalname = Column(String, nullable=False)
    path = Column(String, nullable=True)
    setup_outcome = Column(String, nullable=True)
    call_outcome = Column(String, nullable=True)
    teardown_outcome = Column(String, nullable=True)

    # Runtime data
    cubed_version = Column(String, nullable=True)
    xarray_version = Column(String, nullable=True)
    cubed_xarray_version = Column(String, nullable=True)
    lithops_version = Column(String, nullable=True)
    python_version = Column(String, nullable=True)
    platform = Column(String, nullable=True)

    # CI runner data
    ci_run_url = Column(String, nullable=True)

    # Wall clock data
    start = Column(DateTime, nullable=True)
    end = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)

    # Memory data
    projected_memory = Column(Float, nullable=True)
    average_memory = Column(Float, nullable=True)
    peak_memory = Column(Float, nullable=True)

    # Task data
    number_of_tasks_run = Column(Integer, nullable=True)
    container_seconds = Column(Float, nullable=True)
    
    # Storage data
    intermediate_data_stored = Column(Float, nullable=True)
