import pytest
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from server.core.controller import Controller
from server.core.models import AlarmPayload, TimerPayload, ScheduleType, ScheduleRecord
from server.core.database import async_session
from server.core.schema import Schedule

from unittest.mock import MagicMock

@pytest.fixture
def mock_assistant():
    assistant = MagicMock()
    return assistant

@pytest.fixture
def mock_logger():
    return MagicMock()

@pytest.mark.asyncio
async def test_get_due_schedules(mock_assistant, mock_logger):
    controller = Controller(assistant=mock_assistant, logger=mock_logger)
    
    now = datetime.now(timezone.utc)
    
    # Create future schedule 1
    future_payload_1 = AlarmPayload(
        label="Future Alarm 1",
        time=now + timedelta(hours=1),
        timezone="UTC",
        is_recurring=False,
        tags=["user:test_due"]
    )
    record1 = await controller.create_schedule(future_payload_1)
    
    # Create future schedule 2
    future_payload_2 = AlarmPayload(
        label="Future Alarm 2",
        time=now + timedelta(hours=3),
        timezone="UTC",
        is_recurring=False,
        tags=["user:test_due"]
    )
    record2 = await controller.create_schedule(future_payload_2)
    
    # Query with future 'now' to simulate due schedules
    simulated_now = now + timedelta(hours=2)
    due_schedules = await controller.get_due_schedules(simulated_now)
    
    # Assert
    # We should at least get record1, but not record2
    due_ids = [s.id for s in due_schedules]
    assert record1.id in due_ids
    assert record2.id not in due_ids
    
    # Cleanup
    await controller.delete_schedule(record1.id)
    await controller.delete_schedule(record2.id)

@pytest.mark.asyncio
async def test_get_schedule_records(mock_assistant, mock_logger):
    controller = Controller(assistant=mock_assistant, logger=mock_logger)
    
    now = datetime.now(timezone.utc)
    test_tag = f"user:record_test_{uuid.uuid4()}"
    
    payload = AlarmPayload(
        label="Tag Alarm",
        time=now + timedelta(hours=2),
        timezone="UTC",
        is_recurring=False,
        tags=[test_tag]
    )
    record = await controller.create_schedule(payload)
    
    records = await controller.get_schedule_records(tags=[test_tag], type_filter=None)
    assert len(records) == 1
    assert records[0].label == "Tag Alarm"
    
    # test type filter
    records_filtered = await controller.get_schedule_records(tags=[test_tag], type_filter=ScheduleType.ALARM)
    assert len(records_filtered) == 1
    
    records_empty = await controller.get_schedule_records(tags=[test_tag], type_filter=ScheduleType.REMINDER)
    assert len(records_empty) == 0
    
    await controller.delete_schedule(record.id)
