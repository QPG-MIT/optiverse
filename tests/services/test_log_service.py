"""
Tests for LogService.

These tests verify:
- Log messages are created correctly
- Log levels work properly
- Message filtering works
- Listeners are notified correctly
- Message limit is enforced
"""

from __future__ import annotations

from optiverse.services.log_service import LogLevel, LogMessage, LogService, get_log_service


class TestLogMessage:
    """Tests for LogMessage class."""

    def test_create_log_message(self):
        """Test creating a log message."""
        msg = LogMessage(LogLevel.INFO, "Test message", "TestCategory")

        assert msg.level == LogLevel.INFO
        assert msg.message == "Test message"
        assert msg.category == "TestCategory"
        assert msg.timestamp is not None

    def test_log_message_format(self):
        """Test log message formatting."""
        msg = LogMessage(LogLevel.ERROR, "Error occurred", "System")

        formatted = msg.format()
        assert "ERROR" in formatted
        assert "Error occurred" in formatted
        assert "System" in formatted

    def test_log_message_str(self):
        """Test __str__ method."""
        msg = LogMessage(LogLevel.DEBUG, "Debug info")

        assert str(msg) == msg.format()


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_log_level_values(self):
        """Test log level values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"


class TestLogService:
    """Tests for LogService class."""

    def test_create_log_service(self):
        """Test creating a log service."""
        service = LogService()
        assert service is not None
        assert len(service.get_messages()) == 0

    def test_create_with_max_messages(self):
        """Test creating service with custom max messages."""
        service = LogService(max_messages=50)
        assert service._max_messages == 50

    def test_log_debug(self):
        """Test logging debug message."""
        service = LogService()
        service.debug("Debug message", "Test")

        messages = service.get_messages()
        assert len(messages) == 1
        assert messages[0].level == LogLevel.DEBUG
        assert messages[0].message == "Debug message"
        assert messages[0].category == "Test"

    def test_log_info(self):
        """Test logging info message."""
        service = LogService()
        service.info("Info message")

        messages = service.get_messages()
        assert len(messages) == 1
        assert messages[0].level == LogLevel.INFO

    def test_log_warning(self):
        """Test logging warning message."""
        service = LogService()
        service.warning("Warning message")

        messages = service.get_messages()
        assert len(messages) == 1
        assert messages[0].level == LogLevel.WARNING

    def test_log_error(self):
        """Test logging error message."""
        service = LogService()
        service.error("Error message")

        messages = service.get_messages()
        assert len(messages) == 1
        assert messages[0].level == LogLevel.ERROR

    def test_filter_by_level(self):
        """Test filtering messages by level."""
        service = LogService()
        service.debug("Debug")
        service.info("Info")
        service.error("Error")

        errors = service.get_messages(level=LogLevel.ERROR)
        assert len(errors) == 1
        assert errors[0].message == "Error"

    def test_filter_by_category(self):
        """Test filtering messages by category."""
        service = LogService()
        service.info("Message 1", "Cat1")
        service.info("Message 2", "Cat2")
        service.info("Message 3", "Cat1")

        cat1_msgs = service.get_messages(category="Cat1")
        assert len(cat1_msgs) == 2

    def test_filter_by_level_and_category(self):
        """Test filtering by both level and category."""
        service = LogService()
        service.debug("Debug Cat1", "Cat1")
        service.error("Error Cat1", "Cat1")
        service.error("Error Cat2", "Cat2")

        filtered = service.get_messages(level=LogLevel.ERROR, category="Cat1")
        assert len(filtered) == 1
        assert filtered[0].message == "Error Cat1"

    def test_clear(self):
        """Test clearing all messages."""
        service = LogService()
        service.info("Message 1")
        service.info("Message 2")
        assert len(service.get_messages()) == 2

        service.clear()
        assert len(service.get_messages()) == 0

    def test_max_messages_limit(self):
        """Test that max messages limit is enforced."""
        service = LogService(max_messages=5)

        for i in range(10):
            service.info(f"Message {i}")

        messages = service.get_messages()
        assert len(messages) == 5
        # Should keep newest messages
        assert messages[0].message == "Message 5"
        assert messages[-1].message == "Message 9"

    def test_get_categories(self):
        """Test getting list of categories."""
        service = LogService()
        service.info("Msg", "Alpha")
        service.info("Msg", "Beta")
        service.info("Msg", "Alpha")

        categories = service.get_categories()
        assert "Alpha" in categories
        assert "Beta" in categories
        assert len(categories) == 2

    def test_add_listener(self):
        """Test adding a listener."""
        service = LogService()
        received_messages = []

        def listener(msg):
            received_messages.append(msg)

        service.add_listener(listener)
        service.info("Test message")

        assert len(received_messages) == 1
        assert received_messages[0].message == "Test message"

    def test_remove_listener(self):
        """Test removing a listener."""
        service = LogService()
        received_messages = []

        def listener(msg):
            received_messages.append(msg)

        service.add_listener(listener)
        service.info("Message 1")
        assert len(received_messages) == 1

        service.remove_listener(listener)
        service.info("Message 2")
        assert len(received_messages) == 1  # Still 1, listener was removed

    def test_listener_error_doesnt_break_logging(self):
        """Test that listener errors don't break logging."""
        service = LogService()

        def bad_listener(msg):
            raise ValueError("Listener error")

        def good_listener(msg):
            pass

        service.add_listener(bad_listener)
        service.add_listener(good_listener)

        # Should not raise
        service.info("Test message")

        # Message should still be logged
        assert len(service.get_messages()) == 1

    def test_duplicate_listener_not_added(self):
        """Test that duplicate listeners are not added."""
        service = LogService()
        call_count = [0]

        def listener(msg):
            call_count[0] += 1

        service.add_listener(listener)
        service.add_listener(listener)  # Duplicate

        service.info("Test")
        assert call_count[0] == 1  # Only called once


class TestGlobalLogService:
    """Tests for global log service singleton."""

    def test_get_log_service_returns_singleton(self):
        """Test that get_log_service returns same instance."""
        service1 = get_log_service()
        service2 = get_log_service()

        assert service1 is service2

    def test_global_service_is_log_service(self):
        """Test that global service is a LogService instance."""
        service = get_log_service()
        assert isinstance(service, LogService)
