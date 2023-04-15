from slackdump2html.SlackDumpReader import SlackDumpReader
from slackdump2html.SlackDataCleaner import SlackDataCleaner
from slackdump2html.HtmlPrinter import HtmlPrinter


def test_SlackDumpReader():
    # Arrange
    reader = SlackDumpReader(SlackDataCleaner())
    # Act
    data = reader.read("tests/test_data/C2R198BRC.json")
    # Assert
    assert True


def test_HtmlPrinter():
    # Arrange
    reader = SlackDumpReader(SlackDataCleaner())
    data = reader.read("tests/test_data/C2R198BRC.json")
    printer = HtmlPrinter(data, "C2R198BRC")
    # Act
    printer.print()
    # Assert
    assert True
