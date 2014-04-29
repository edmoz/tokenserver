
import time
import uuid
import random
import os
import urlparse

import browserid
import browserid.jwt
from browserid.tests.support import make_assertion

import unittest
import requests

ONE_YEAR = 60 * 60 * 24 * 365

MOCKMYID_PRIVATE_KEY = browserid.jwt.DS128Key({
    "algorithm": "DS",
    "x": "385cb3509f086e110c5e24bdd395a84b335a09ae",
    "y": "738ec929b559b604a232a9b55a5295afc368063bb9c20fac4e53a74970a4db795"
         "6d48e4c7ed523405f629b4cc83062f13029c4d615bbacb8b97f5e56f0c7ac9bc1"
         "d4e23809889fa061425c984061fca1826040c399715ce7ed385c4dd0d40225691"
         "2451e03452d3c961614eb458f188e3e8d2782916c43dbe2e571251ce38262",
    "p": "ff600483db6abfc5b45eab78594b3533d550d9f1bf2a992a7a8daa6dc34f8045a"
         "d4e6e0c429d334eeeaaefd7e23d4810be00e4cc1492cba325ba81ff2d5a5b305a"
         "8d17eb3bf4a06a349d392e00d329744a5179380344e82a18c47933438f891e22a"
         "eef812d69c8f75e326cb70ea000c3f776dfdbd604638c2ef717fc26d02e17",
    "q": "e21e04f911d1ed7991008ecaab3bf775984309c3",
    "g": "c52a4a0ff3b7e61fdf1867ce84138369a6154f4afa92966e3c827e25cfa6cf508b"
         "90e5de419e1337e07a2e9e2a3cd5dea704d175f8ebf6af397d69e110b96afb17c7"
         "a03259329e4829b0d03bbc7896b15b4ade53e130858cc34d96269aa89041f40913"
         "6c7242a38895c9d5bccad4f389af1d7a4bd1398bd072dffa896233397a",
})


class NodeAssignmentTest(unittest.TestCase):
    """This tests the assertion verification + node retrieval.

    Depending on the setup of the system under load, it could also test the
    node allocation mechanism.

    You can populate the database of the system under load with the
    "populate-db" script.
    """

    if os.environ.get('PUBLIC_URL'):
        server_url = os.environ.get('PUBLIC_URL').strip('/')
    else:
        server_url = 'https://token.stage.mozaws.net'

    def setUp(self):
        self.token_exchange = '/1.0/sync/1.5'
        # Options to tweak how many of each kind of user.
        self.vusers = 2

        self.invalid_domain = 'mozilla.com'
        self.valid_domain = 'mockmyid.s3-us-west-2.amazonaws.com'
        self.audience = self.server_url

    def _make_assertion(self, email, **kwds):
        if "exp" not in kwds:
            kwds["exp"] = int((time.time() + ONE_YEAR) * 1000)
        return make_assertion(email, **kwds)

    def _do_token_exchange(self, assertion, status=200):
        url = urlparse.urljoin(self.server_url, self.token_exchange)
        headers = {'Authorization': 'BrowserID %s' % assertion}
        # print 'Assertion: ', assertion
        res = requests.get(url, headers=headers)
        print "Reponse: ", res.status_code, res.json()
        self.assertEquals(res.status_code, status)
        return res

    def test_single_token_exchange(self):
        uid = random.randint(1, 1000000)
        email = "user{uid}@{host}".format(uid=uid, host=self.valid_domain)
        self._do_token_exchange(self._make_assertion(
            email=email,
            issuer=self.valid_domain,
            audience=self.audience,
            issuer_keypair=(None, MOCKMYID_PRIVATE_KEY)))

    def test_single_token_exchange_new_user(self):
        uid = str(uuid.uuid1())
        email = "loadtest-{uid}@{host}".format(uid=uid, host=self.valid_domain)
        self._do_token_exchange(self._make_assertion(
            email=email,
            issuer=self.valid_domain,
            audience=self.audience,
            issuer_keypair=(None, MOCKMYID_PRIVATE_KEY)))

    def test_token_exchange(self):
        # a valid browserid assertion should be taken by the server and turned
        # back into an authentication token which is valid for 30 minutes.
        # we want to test this for a number of users, with different
        # assertions.
        for idx in range(self.vusers):
            email = "{uid}@{host}".format(uid=idx, host=self.valid_domain)
            self._do_token_exchange(self._make_assertion(
                email=email,
                issuer=self.valid_domain,
                audience=self.audience,
                issuer_keypair=(None, MOCKMYID_PRIVATE_KEY)))

    def test_bad_assertion(self, idx=None):
        if idx is None:
            idx = random.choice(range(self.vusers))

        email = "{uid}@{host}".format(uid=idx, host="mockmyid.s3-us-west-2.amazonaws.com")
        # expired assertion
        expired = self._make_assertion(
                email=email,
                issuer=self.valid_domain,
                exp=int(time.time() - ONE_YEAR) * 1000,
                audience=self.audience,
                issuer_keypair=(None, MOCKMYID_PRIVATE_KEY))
        self._do_token_exchange(expired, 401)

        # wrong issuer
        wrong_issuer = self._make_assertion(email, audience=self.audience)
        self._do_token_exchange(wrong_issuer, 401)

        # wrong email host
        email = "{uid}@{host}".format(uid=idx, host=self.invalid_domain)
        wrong_email_host = self._make_assertion(
                email, issuer=self.valid_domain,
                audience=self.audience,
                issuer_keypair=(None, MOCKMYID_PRIVATE_KEY))
        self._do_token_exchange(wrong_email_host, 401)

if __name__ == '__main__':
    unittest.main()
