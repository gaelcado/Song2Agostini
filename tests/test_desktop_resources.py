import pytest
from drum_lab.desktop import allowed_resource


@pytest.mark.parametrize('url', [
    'chrome://resources/css/text_defaults_md.css',
    'chrome://resources/cr_elements/cr_icon_button/cr_icon_button.js',
    'chrome-extension://mhjfbmdgcfjbbpaeojofohoefgiehjai/index.html',
    'http://127.0.0.1:54321/api/jobs/example/pdf',
])
def test_pdf_viewer_and_app_resources_allowed(url):
    assert allowed_resource(url, 54321)


@pytest.mark.parametrize('url', [
    'https://example.com/score.pdf', 'http://127.0.0.1:54322/',
    'http://127.0.0.1.example.com:54321/', 'file:///tmp/score.pdf',
    'chrome://settings/', 'chrome://resources.example.com/module.js',
])
def test_viewer_exception_does_not_allow_other_hosts(url):
    assert not allowed_resource(url, 54321)
