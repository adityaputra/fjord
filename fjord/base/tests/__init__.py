from functools import wraps

from django.conf import settings
from django.test.client import Client
from django.test import LiveServerTestCase
from django.test.utils import override_settings

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.firefox import firefox_binary
from nose import SkipTest

from funfactory.urlresolvers import split_path, reverse
from test_utils import TestCase as OriginalTestCase


class LocalizingClient(Client):
    """Client which rewrites urls to include locales and adds a user agent.

    This prevents the locale middleware from returning a 301 to add the
    prefixes, which makes tests more complicated.

    It also ensures there is a user agent set in the header. The default is a
    Firefox 14 on Linux user agent. It can be overridden by passing a
    user_agent parameter to ``__init__``, setting ``self.user_agent`` to the
    desired value, or by including ``HTTP_USER_AGENT`` in an individual
    request. This behavior can be prevented by setting ``self.user_agent`` to
    ``None``.

    """
    def __init__(self, user_agent=None, *args, **kwargs):
        self.user_agent = user_agent or ('Mozilla/5.0 (X11; Linux x86_64; '
            'rv:14.0) Gecko/20100101 Firefox/14.0.1')
        super(LocalizingClient, self).__init__(*args, **kwargs)

    def request(self, **request):
        """Make a request, ensuring it has a locale and a user agent."""
        # Fall back to defaults as in the superclass's implementation:
        path = request.get('PATH_INFO', self.defaults.get('PATH_INFO', '/'))
        locale, shortened = split_path(path)
        if not locale:
            request['PATH_INFO'] = '/%s/%s' % (settings.LANGUAGE_CODE,
                                               shortened)
        if 'HTTP_USER_AGENT' not in request and self.user_agent:
            request['HTTP_USER_AGENT'] = self.user_agent

        return super(LocalizingClient, self).request(**request)


@override_settings(ES_LIVE_INDEX=False)
class TestCase(OriginalTestCase):
    """A modification of ``test_utils.TestCase`` that skips live indexing."""
    pass


class MobileTestCase(TestCase):
    """Base class for mobile tests"""
    def setUp(self):
        super(MobileTestCase, self).setUp()
        self.client.cookies[settings.MOBILE_COOKIE] = 'on'


class SeleniumTestCase(LiveServerTestCase):

    skipme = False

    @classmethod
    def setUpClass(cls):
        try:
            firefox_path = getattr(settings, 'SELENIUM_FIREFOX_PATH', None)
            if firefox_path:
                firefox_bin = firefox_binary.FirefoxBinary(
                    firefox_path=firefox_path)
                kwargs = {'firefox_binary': firefox_bin}
            else:
                kwargs = {}
            cls.webdriver = webdriver.Firefox(**kwargs)
        except (RuntimeError, WebDriverException):
            cls.skipme = True

        super(SeleniumTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        if not cls.skipme:
            cls.webdriver.quit()
        super(SeleniumTestCase, cls).tearDownClass()

    def setUp(self):
        # Don't run if Selenium isn't available.
        if self.skipme:
            raise SkipTest('Selenium unavailable.')
        # Go to an empty page before every test.
        self.webdriver.get('')


def with_save(func):
    """Decorate a model maker to add a `save` kwarg.

    If save=True, the model maker will save the object before returning it.

    """
    @wraps(func)
    def saving_func(*args, **kwargs):
        save = kwargs.pop('save', False)
        ret = func(*args, **kwargs)
        if save:
            ret.save()
        return ret

    return saving_func
