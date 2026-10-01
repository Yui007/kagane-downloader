import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from typer.testing import CliRunner
import main
from config import Config
from src.scraper import Series, Book
from src.scraper.api_client import KaganeAPIClient


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.book = Book(book_id='one', chapter_no='1', page_count=2)
        self.series = Series(series_id='series', title='Test series', series_books=[self.book])

    def test_documented_download_command_is_noninteractive(self):
        with patch.object(main, 'KaganeScraper') as scraper, patch.object(main, 'download_chapters_api') as download:
            scraper.return_value.get_series.return_value = self.series
            download.return_value = [(self.book, True, Path('test'), 2)]
            result = CliRunner().invoke(main.app, ['download', '--url', 'test-series', '--chapters', '1'])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(download.call_args.args[2].headless_mode)
            self.assertEqual(download.call_args.args[2].download_format, 'cbz')
            scraper.return_value.close.assert_called_once()

    def test_failed_acquisition_exits_nonzero(self):
        with patch.object(main, 'KaganeScraper') as scraper, patch.object(main, 'download_chapters_api') as download:
            scraper.return_value.get_series.return_value = self.series
            download.return_value = [(self.book, False, Path('test'), 1)]
            result = CliRunner().invoke(main.app, ['download', '--url', 'test-series'])
            self.assertEqual(result.exit_code, 1)

    def test_unknown_source_chapter_does_not_start_download(self):
        with patch.object(main, 'KaganeScraper') as scraper, patch.object(main, 'download_chapters_api') as download:
            scraper.return_value.get_series.return_value = self.series
            result = CliRunner().invoke(main.app, ['download', '--url', 'test-series', '--chapters', '2'])
            self.assertNotEqual(result.exit_code, 0)
            download.assert_not_called()

    def acquire(self, downloaded, conversion_error=False):
        with tempfile.TemporaryDirectory() as temporary, \
             patch('src.scraper.BrowserManager') as browser, \
             patch('src.scraper.APIChapterDownloader') as downloader, \
             patch('src.converter.create_cbz') as converter:
            downloader.return_value.sanitize_filename.side_effect = lambda name, **kw: name
            downloader.return_value.download_from_urls.return_value = downloaded
            driver = browser.return_value.get_driver.return_value
            driver.execute_script.return_value = json.dumps({'series:one': {
                'token': 'test-token', 'pages': [
                    {'page_no': 1, 'page_id': 'one', 'ext': 'jpg'},
                    {'page_no': 2, 'page_id': 'two', 'ext': 'jpg'}]}})
            if conversion_error:
                converter.side_effect = OSError('conversion failed')
            result = main.download_chapters_api(self.series, [self.book], Config(
                download_directory=temporary, download_format='cbz', headless_mode=True))
            return result[0][1], converter.called

    def test_partial_chapter_is_failed_and_not_converted(self):
        self.assertEqual(self.acquire(1), (False, False))

    def test_conversion_failure_is_failed(self):
        self.assertEqual(self.acquire(2, conversion_error=True), (False, True))

    def test_complete_chapter_is_converted(self):
        self.assertEqual(self.acquire(2), (True, True))

    def test_security_challenge_is_not_retried(self):
        client = KaganeAPIClient()
        error = RuntimeError('HTTP 403')
        error.response = SimpleNamespace(status_code=403)
        try:
            with patch.object(client.session, 'get', side_effect=error) as request:
                with self.assertRaises(RuntimeError):
                    client.get_series('test')
                request.assert_called_once()
        finally:
            client.close()


if __name__ == '__main__':
    unittest.main()
